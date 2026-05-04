from asgiref.sync import sync_to_async
import asyncio
import json
import logging
import threading
from typing import Dict, List

from django.apps import apps
from django.conf import settings
from django.db import transaction
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from hi.apps.attribute.enums import AttributeType
from hi.apps.common.delayed_signal_processor import DelayedSignalProcessor
from hi.apps.common.singleton import Singleton
from hi.apps.common.module_utils import import_module_safe
from hi.apps.entity.models import Entity
from hi.apps.system.health_status_provider import HealthStatusProvider

from .entity_operations import EntityIntegrationOperations
from .enums import IntegrationAttributeType, IntegrationDisableMode
from .exceptions import IntegrationConnectionError
from .integration_data import IntegrationData
from .integration_gateway import IntegrationGateway
from .transient_models import IntegrationKey
from .models import Integration, IntegrationAttribute
from .transient_models import IntegrationMetaData

logger = logging.getLogger(__name__)


class IntegrationManager( Singleton ):

    START_DELAY_INTERVAL_SECS = 2

    # Bounded timeout (in seconds) used when an integration's gateway
    # test_connection() probe is invoked synchronously during attribute-save
    # validation or before relaunching monitors. Kept short for interactive
    # save-time UX; can be promoted to a user-tunable setting later if
    # demand emerges.
    HEALTH_CHECK_TIMEOUT_SECS = 5

    def __new__(cls):
        return super().__new__(cls)
    
    def __init_singleton__( self ):
        self._integration_data_map : Dict[ str, IntegrationData ] = dict()
        self._monitor_map = dict()
        self._initialized = False
        self._data_lock = threading.Lock()
        self._monitor_event_loop = None
        return

    def reset_for_testing(self):
        """
        Reset the manager's in-memory state. Intended for use in tests only,
        to provide isolation from singleton state that persists across test
        methods (integration data map, monitor map).
        """
        self._integration_data_map.clear()
        self._monitor_map.clear()
        return

    def get_integration_data_list( self, enabled_only = False ) -> List[ IntegrationData ]:
        if enabled_only:
            integration_data_list = [ x for x in self._integration_data_map.values() if x.is_enabled ]
        else:
            integration_data_list = list( self._integration_data_map.values() )

        integration_data_list.sort( key = lambda data : data.integration_metadata.label )
        return integration_data_list
    
    def get_default_integration_data( self ) -> IntegrationData:
        enabled_integration_data_list = [ x for x in self._integration_data_map.values()
                                          if x.is_enabled ]
        if not enabled_integration_data_list:
            return None
        enabled_integration_data_list.sort( key = lambda data : data.integration_metadata.label )
        return enabled_integration_data_list[0]

    def get_integration_data( self, integration_id : str ) -> IntegrationData :
        if integration_id in self._integration_data_map:
            return self._integration_data_map[integration_id]
        raise KeyError( f'Unknown integration id "{integration_id}".' )

    def refresh_integrations_from_db( self ) :
        for integration_data in self._integration_data_map.values():
            integration_data.integration.refresh_from_db()
            continue
        return

    def get_integration_gateway( self, integration_id : str ) -> IntegrationGateway:
        if integration_id in self._integration_data_map:
            return self._integration_data_map[integration_id].integration_gateway
        raise KeyError( f'Unknown integration id "{integration_id}".' )

    def get_health_status_by_provider_id( self,
                                          provider_id : str ) -> HealthStatusProvider:
        with self._data_lock:
            for integration in self._integration_data_map.values():
                provider = integration.integration_gateway.get_health_status_provider()
                if provider.get_provider_info().provider_id == provider_id:
                    return provider
                continue
        raise KeyError( f'Unknown provider id: "{provider_id}".' )

    def get_health_status_by_monitor_id( self,
                                         monitor_id : str ) -> HealthStatusProvider:
        with self._data_lock:
            for monitor in self._monitor_map.values():
                if monitor.id == monitor_id:
                    return monitor
                continue
        raise KeyError( f'Unknown monitor id: "{monitor_id}".' )

    def get_health_status_providers(self) -> List[HealthStatusProvider]:
        with self._data_lock:
            return list( self._monitor_map.values() )

    def get_health_status_provider_map(self) -> Dict[str, HealthStatusProvider]:
        """Snapshot of running monitors keyed by integration_id.

        Callers that want to pair every configured integration with
        its monitor (when present) — e.g., the system-info page —
        use this alongside ``get_integration_data_list``. A missing
        key for a configured integration means no live monitor
        (the integration is paused or its monitor failed to start).
        """
        with self._data_lock:
            return dict( self._monitor_map )
        
    async def initialize( self, event_loop ) -> None:
        """
        This should be initialized from the background thread where the
        integration monitor task will run.
        """
        with self._data_lock:
            if self._initialized:
                logger.info("IntegrationManager already initialize. Skipping.")
                return
            self._initialized = True

            self._monitor_event_loop = event_loop
           
            logger.info("Discovering and starting integration monitors...")
            await self._load_integration_data()
            await self._start_all_integration_monitors()
        return
        
    async def shutdown(self) -> None:
        logger.info("Stopping all integration monitors...")
        for integration_id, monitor in self._monitor_map.items():
            logger.debug( f'Stopping integration monitor: {integration_id}' )
            monitor.stop()
            continue
        return
        
    async def _load_integration_data(self) -> None:
        
        logger.debug("Discovering defined integrations ...")
        defined_integration_gateway_map = self.discover_defined_integrations()

        logger.debug("Loading existing integrations ...")
        existing_integration_map = await sync_to_async( self._load_existing_integrations,
                                                        thread_sensitive = True )()
        
        for integration_id, integration_gateway in defined_integration_gateway_map.items():
            integration_metadata = integration_gateway.get_metadata()
            integration_id = integration_metadata.integration_id
            if integration_id in existing_integration_map:
                integration = existing_integration_map[integration_id]
            else:
                logger.warning(
                    f'Missing integration DB record for "{integration_id}". '
                    'Skipping integration startup until sync_integrations is run.'
                )
                continue
            integration_data = IntegrationData(
                integration_gateway = integration_gateway,
                integration = integration,
            )
            self._integration_data_map[integration_id] = integration_data
            continue
        return

    async def _start_all_integration_monitors(self) -> None:
        logger.debug("Starting integration monitors...")

        for integration_data in self._integration_data_map.values():
            if not integration_data.is_enabled:
                logger.debug( f'Skipping disabled integration monitor: {integration_data}' )
                continue

            # Avoid the "thundering herd" during startups
            await asyncio.sleep( self.START_DELAY_INTERVAL_SECS )
            await self._start_integration_monitor( integration_data = integration_data )
            continue
        return

    def _launch_integration_monitor_task( self, integration_data : IntegrationData ):
        integration_id = integration_data.integration_id

        async def run_in_loop():
            try:
                await self._start_integration_monitor( integration_data = integration_data )
            except Exception as e:
                logger.exception( f'Error in integration monitor task "{integration_id}": {e}')
            return

        if self._monitor_event_loop is None:
            logger.error( f'Error in integration monitor task "{integration_id}": No event loop.')
            return

        try:
            _ = asyncio.get_running_loop()
            asyncio.create_task( run_in_loop() )
        except RuntimeError:
            asyncio.run_coroutine_threadsafe( run_in_loop(), self._monitor_event_loop )
        return
        
    async def _start_integration_monitor( self, integration_data : IntegrationData ):
        integration_id = integration_data.integration_id
        logger.debug( f'Starting integration monitor: {integration_id}' )

        if not integration_data.is_enabled:
            logger.warning( f'Tried to start disabled integration monitor: {integration_id}' )
            return

        monitor = integration_data.integration_gateway.get_monitor()
        if not monitor:
            logger.debug( f'No integration monitor defined: {integration_id}' )
            return
        
        if integration_id in self._monitor_map:
            existing_monitor = self._monitor_map[integration_id]
            if existing_monitor.is_running:
                logger.warning( f'Found running integration monitor: {integration_id}' )
                return
                
        self._monitor_map[integration_id] = monitor
        if not monitor.is_running:

            if settings.DEBUG and settings.SUPPRESS_MONITORS:
                logger.debug(f"Skipping integration monitor: {integration_id}. See SUPPRESS_MONITORS = True")
                return
            
            logger.debug(f"Starting integration monitor: {integration_id}")
            asyncio.create_task( monitor.start(),
                                 name=f'Integration-{integration_id}' )
        return

    def _stop_integration_monitor( self, integration_data : IntegrationData ):
        integration_id = integration_data.integration_id
        logger.debug( f'Stopping integration monitor: {integration_id}' )

        if integration_id not in self._monitor_map:
            logger.debug( f'No integration monitor running: {integration_id}' )
            return

        existing_monitor = self._monitor_map[integration_id]
        if existing_monitor.is_running:
            existing_monitor.stop()
        else:
            logger.debug( f'Existing integration monitor is not running: {integration_id}' )

        del self._monitor_map[integration_id]
        return

    def discover_defined_integrations(self) -> Dict[ str, IntegrationGateway ]:

        integration_id_to_gateway = dict()
        for app_config in apps.get_app_configs():
            if not app_config.name.startswith( 'hi.services' ):
                continue
            module_name = f'{app_config.name}.integration'
            try:
                app_module = import_module_safe( module_name = module_name )
                if not app_module:
                    logger.debug( f'No integration module for {app_config.name}' )
                    continue

                logger.debug( f'Found integration module for {app_config.name}' )
                
                for attr_name in dir(app_module):
                    attr = getattr( app_module, attr_name )
                    if ( isinstance( attr, type )
                         and issubclass( attr, IntegrationGateway )
                         and attr is not IntegrationGateway ):
                        logger.debug(f'Found integration gateway: {attr_name}')
                        integration_gateway = attr()
                        integration_metadata = integration_gateway.get_metadata()
                        integration_id = integration_metadata.integration_id
                        integration_id_to_gateway[integration_id] = integration_gateway
                    continue                
                
            except Exception as e:
                logger.exception( f'Problem getting integration gateway for {module_name}.', e )
            continue

        return integration_id_to_gateway

    def _load_existing_integrations(self):
        integration_queryset = Integration.objects.all()
        return { x.integration_id: x for x in integration_queryset }
    
    def ensure_all_attributes_exist( self,
                                     integration_metadata  : IntegrationMetaData,
                                     integration           : Integration ):
        """
        After an integration is created, we need to be able to detect if any
        new attributes might have been defined.  This allows new code
        features to be added for existing installations.
        """
        with self._data_lock:
            new_attribute_types = list()
            existing_attributes = { x.integration_key: x
                                    for x in integration.attributes.all() }

            AttributeType = integration_metadata.attribute_type
            for attribute_type in AttributeType:
                integration_key = IntegrationKey(
                    integration_id = integration.integration_id,
                    integration_name = str(attribute_type),
                )
                if integration_key not in existing_attributes:
                    new_attribute_types.append( attribute_type )
                else:
                    existing_attr = existing_attributes[integration_key]
                    if existing_attr.name != attribute_type.label:
                        existing_attr.name = attribute_type.label
                        existing_attr.save(
                            update_fields = ['name'],
                            track_history = False,
                        )
                    description = attribute_type.description or ''
                    if existing_attr.description != description:
                        existing_attr.description = description
                        existing_attr.save(
                            update_fields = ['description'],
                            track_history = False,
                        )
                continue

            if new_attribute_types:
                with transaction.atomic():
                    for attribute_type in new_attribute_types:
                        self._create_integration_attribute(
                            integration = integration,
                            attribute_type = attribute_type,
                        )
                        continue
        return
        
    def _create_integration_attribute( self,
                                       integration     : Integration,
                                       attribute_type  : IntegrationAttributeType ):
        integration_key = IntegrationKey(
            integration_id = integration.integration_id,
            integration_name = str(attribute_type),
        )
        attribute = IntegrationAttribute(
            integration = integration,
            name = attribute_type.label,
            value = attribute_type.initial_value,
            description = attribute_type.description or '',
            value_type_str = str(attribute_type.value_type),
            value_range_str = json.dumps( attribute_type.value_range_dict ),
            integration_key_str = str(integration_key),
            attribute_type_str = AttributeType.PREDEFINED,
            is_editable = attribute_type.is_editable,
            is_required = attribute_type.is_required,
        )
        attribute.save( track_history = False )  # Do not want this initial value in history
        return
                
    def enable_integration( self, integration_data : IntegrationData ):
        """
        Idempotent: enabling an already-enabled integration is a no-op.

        The is_enabled re-read happens inside the data lock and atomic
        transaction so the disabled→enabled transition (which also
        un-pauses) cannot race with another caller. Callers can invoke
        this unconditionally without first checking is_enabled, which
        avoids a TOCTOU window between caller check and manager write.
        """
        with self._data_lock:
            with transaction.atomic():
                # Re-read fresh state inside the lock; another caller
                # may have enabled the integration between the caller's
                # check (if any) and our acquiring this lock.
                integration_data.integration.refresh_from_db()
                if integration_data.integration.is_enabled:
                    return
                integration_data.integration.is_enabled = True
                integration_data.integration.is_paused = False
                integration_data.integration.save()
            self.refresh_integrations_from_db()
            self._launch_integration_monitor_task(
                integration_data = integration_data,
            )
        return

    def disable_integration( self,
                             integration_data : IntegrationData,
                             mode             : IntegrationDisableMode = None ):
        """
        Remove an integration: stop monitors, handle attached entities per
        mode, flip state flags. Configuration attributes (IntegrationAttribute
        rows) are retained so a subsequent Configure can reuse them.

        Mode semantics:
          SAFE (default): delete entities without user-created data; preserve
          entities with user-created data by detaching them from the
          integration (via EntityIntegrationOperations.preserve_with_user_data).
          Preserved entities get the '[Disconnected]' name prefix.

          ALL: hard-delete all entities attached to this integration
          regardless of user data.

        Monitors are stopped first to avoid races with in-flight sync work.
        """
        if mode is None:
            mode = IntegrationDisableMode.default()

        with self._data_lock:
            # Stop monitors before any entity changes to avoid races with
            # in-flight sync work.
            self._stop_integration_monitor( integration_data = integration_data )

        integration_id = integration_data.integration_id

        # DB-level entity removal does not need the manager's data
        # lock — it operates on rows, not on the in-memory monitor
        # map, and transaction.atomic() handles row-level
        # concurrency. Holding _data_lock across the closure walk
        # and cascading deletes would block all other lifecycle
        # calls on every integration for the duration of a wide
        # removal.
        with transaction.atomic():
            # Seed: every entity attached to this integration. The
            # closure walk inside the helper picks up delegate
            # entities (e.g., Area entities auto-created when a
            # motion sensor was placed in a view) that would be
            # orphaned by the removal.
            seed_entity_ids = list(
                Entity.objects
                .filter( integration_id = integration_id )
                .values_list( 'id', flat = True )
            )
            EntityIntegrationOperations.remove_entities_with_closure(
                seed_entity_ids = seed_entity_ids,
                integration_name = integration_id,
                preserve_user_data = ( mode != IntegrationDisableMode.ALL ),
            )

        with self._data_lock:
            # Re-read inside the lock: a concurrent lifecycle call
            # may have touched the row while we were doing the
            # lock-free DB removal. The disable intent still wins
            # (entities are gone), so we unconditionally flip both
            # flags to the disabled state — but refresh first so
            # we don't clobber unrelated fields a concurrent caller
            # may have written.
            integration_data.integration.refresh_from_db()
            integration_data.integration.is_enabled = False
            integration_data.integration.is_paused = False
            integration_data.integration.save()
        return

    def pause_integration( self, integration_data : IntegrationData ):
        """
        Stop the integration's monitors while leaving is_enabled, entities,
        and configuration intact. No-op if the integration is not enabled or
        is already paused. The DB flag represents user intent: once set, a
        failed monitor stop does not re-trigger on a subsequent pause call.
        """
        if not integration_data.integration.is_enabled:
            return
        if integration_data.integration.is_paused:
            return
        with self._data_lock:
            with transaction.atomic():
                integration_data.integration.is_paused = True
                integration_data.integration.save()
            self.refresh_integrations_from_db()
            self._stop_integration_monitor( integration_data = integration_data )
        return

    def resume_integration( self, integration_data : IntegrationData ):
        """
        Relaunch the integration's monitors after a pause. No-op if the
        integration is not enabled. Unlike pause, resume always attempts the
        monitor launch regardless of the is_paused flag, so that a prior
        failed launch can be retried by invoking resume again.
        _launch_integration_monitor_task is idempotent when the monitor is
        already running.

        Probes upstream connectivity via the gateway's test_connection
        before relaunching, so we fail fast (with a meaningful error to
        the caller) rather than spinning up monitors that will immediately
        error against an unreachable service. Raises
        IntegrationConnectionError on probe failure.

        The probe runs OUTSIDE the data lock — we don't want to hold the
        lock for ~5 seconds while a network probe is in flight, since
        that would block all other lifecycle operations on every
        integration. The trade-off is a TOCTOU window between the
        outside-lock is_enabled check and the inside-lock state write:
        another caller could disable_integration() during the probe.
        We close that window by re-checking is_enabled inside the lock
        and aborting if the integration was disabled while we probed.
        """
        if not integration_data.integration.is_enabled:
            return

        integration_attributes = list(
            integration_data.integration.attributes.all()
        )
        test_result = integration_data.integration_gateway.test_connection(
            integration_attributes = integration_attributes,
            timeout_secs = self.HEALTH_CHECK_TIMEOUT_SECS,
        )
        if not test_result.is_success:
            raise IntegrationConnectionError(
                test_result.message or 'Connection test failed during resume.'
            )

        with self._data_lock:
            # Re-check is_enabled inside the lock to close the TOCTOU
            # window opened by running the probe lock-free above. If
            # another caller disabled the integration while we were
            # probing, abandon the resume — surfacing the cause to the
            # caller so the UI can communicate why nothing happened.
            integration_data.integration.refresh_from_db()
            if not integration_data.integration.is_enabled:
                raise IntegrationConnectionError(
                    'Integration was disabled while resume was probing upstream.'
                )
            with transaction.atomic():
                integration_data.integration.is_paused = False
                integration_data.integration.save()
            self.refresh_integrations_from_db()
            self._launch_integration_monitor_task(
                integration_data = integration_data,
            )
        return
    
    def notify_integration_settings_changed(self):
        """
        Notify all integrations that their settings have changed.
        
        This method is called when Integration or IntegrationAttribute models
        are modified. It loops through all discovered integrations and calls
        their gateway's notify_settings_changed() method to reload configuration.
        """
        logger.debug('Integration settings changed - notifying all integrations')
        
        for integration_data in self._integration_data_map.values():
            integration_id = integration_data.integration_id
            try:
                # Notify the integration gateway that settings have changed
                integration_gateway = integration_data.integration_gateway
                integration_gateway.notify_settings_changed()
                logger.debug(f'Notified {integration_id} integration of settings change')
                    
            except Exception as e:
                logger.exception(f'Could not notify {integration_id} integration: {e}')


def _integration_manager_reload_callback():
    """Callback function for delayed integration manager reload."""
    integration_manager = IntegrationManager()
    integration_manager.notify_integration_settings_changed()


# Create delayed signal processor for integration changes
_integration_processor = DelayedSignalProcessor(
    name="integration_manager",
    callback_func=_integration_manager_reload_callback,
    delay_seconds=0.1
)


@receiver(post_save, sender=Integration)
@receiver(post_delete, sender=Integration)
@receiver(post_save, sender=IntegrationAttribute)
@receiver(post_delete, sender=IntegrationAttribute)
def integration_model_changed(sender, instance, **kwargs):
    """
    Handle changes to Integration and IntegrationAttribute models.
    
    This signal handler schedules the IntegrationManager to notify all
    integration monitors after the transaction commits.
    """
    logger.debug(f'Integration model change detected: {sender.__name__}')
    _integration_processor.schedule_processing()
