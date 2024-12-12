from asgiref.sync import sync_to_async
import asyncio
import json
import logging
from typing import Dict, List

from django.apps import apps
from django.db import transaction

from hi.apps.attribute.enums import AttributeType
from hi.apps.common.singleton import Singleton
from hi.apps.common.module_utils import import_module_safe

from .enums import IntegrationAttributeType
from .forms import IntegrationAttributeFormSet
from .integration_data import IntegrationData
from .integration_gateway import IntegrationGateway
from .integration_key import IntegrationKey
from .models import Integration, IntegrationAttribute
from .transient_models import IntegrationMetaData

logger = logging.getLogger(__name__)


class IntegrationManager( Singleton ):

    def __init_singleton__( self ):
        self._integration_data_map : Dict[ str, IntegrationData ] = dict()
        self._monitor_map = {}  # Known monitors
        self._event_loop = None  # Added dynamically and indicates if thread/event loop initialized
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

    def get_integration_gateway( self, integration_id : str ) -> IntegrationGateway:
        if integration_id in self._integration_data_map:
            return self._integration_data_map[integration_id].integration_gateway
        raise KeyError( f'Unknown integration id "{integration_id}".' )

    async def initialize(self) -> None:
        await self._load_integration_data()
        await self._start_all_integration_monitors()
        return
        
    async def _load_integration_data(self) -> None:
        
        logger.debug("Discovering defined integrations ...")
        defined_integration_gateway_map = self._discover_defined_integrations()

        logger.debug("Loading existing integrations ...")
        existing_integration_map = await sync_to_async( self._load_existing_integrations )()
        
        for integration_id, integration_gateway in defined_integration_gateway_map.items():
            integration_metadata = integration_gateway.get_metadata()
            integration_id = integration_metadata.integration_id
            if integration_id in existing_integration_map:
                integration = existing_integration_map[integration_id]
            else:
                integration = Integration.objects.create(
                    integration_id = integration_id,
                    is_enabled = False,
                )
            integration_data = IntegrationData(
                integration_gateway = integration_gateway,
                integration = integration,
            )
            self._integration_data_map[integration_id] = integration_data
            continue
        return

    async def _start_all_integration_monitors(self) -> None:
        if self._event_loop:
            self.shutdown()
        
        self._event_loop = asyncio.get_event_loop()
        
        for integration_data in self._integration_data_map.values():
            if not integration_data.is_enabled:
                logger.debug( f'Skipping monitor start for {integration_data}. Integration is disabled.' )
                continue
            self._start_integration_monitor( integration_data = integration_data )
            continue
        return

    def _start_integration_monitor( self, integration_data : IntegrationData ):
        integration_id = integration_data.integration_id
        logger.debug( f'Starting integration monitor for {integration_id}' )

        assert self._event_loop is not None
        
        if not integration_data.is_enabled:
            logger.warning( f'Tried to start monitor for disabled integration: {integration_id}' )
            return

        monitor = integration_data.integration_gateway.get_monitor()
        if not monitor:
            logger.debug( f'No monitor defined {integration_id}' )
            return
        
        if integration_id in self._monitor_map:
            existing_monitor = self._monitor_map[integration_id]
            if existing_monitor.is_running:
                logger.warning( f'Found existing running monitor for integration: {integration_id}' )
                return
                
        self._monitor_map[integration_id] = monitor
        if not monitor.is_running:
            logger.debug(f"Starting monitor: {integration_id}")
            asyncio.run_coroutine_threadsafe( monitor.start(), self._event_loop )
        return

    def _stop_integration_monitor( self, integration_data : IntegrationData ):
        integration_id = integration_data.integration_id
        logger.debug( f'Stopping integration monitor for {integration_id}' )

        if integration_id not in self._monitor_map:
            logger.debug( f'No monitor running for {integration_id}' )
            return

        existing_monitor = self._monitor_map[integration_id]
        if existing_monitor.is_running:
            existing_monitor.stop()
        else:
            logger.debug( f'Existing monitor is not running for {integration_id}' )

        del self._monitor_map[integration_id]
        return
        
    def shutdown(self) -> None:
        if not self._event_loop:
            logger.info("Cannot stop all monitors. No event loop.")
            return
        
        logger.info("Stopping all integration monitors...")

        for integration_id, monitor in self._monitor_map.items():
            logger.debug( f'Stopping integration monitor for {integration_id}' )
            monitor.stop()
            continue

        if self._event_loop.is_running():
            self._event_loop.stop()
        
        return

    def _discover_defined_integrations(self) -> Dict[ str, IntegrationGateway ]:

        integration_id_to_gateway = dict()
        for app_config in apps.get_app_configs():
            if not app_config.name.startswith( 'hi.integrations' ):
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
    
    def _ensure_all_attributes_exist( self,
                                      integration_metadata  : IntegrationMetaData,
                                      integration           : Integration ):
        """
        After an integration is created, we need to be able to detect if any
        new attributes might have been defined.  This allows new code
        features to be added for existing installations.
        """

        new_attribute_types = set()
        existing_attribute_integration_keys = set([ x.integration_key
                                                    for x in integration.attributes.all() ])
        
        AttributeType = integration_metadata.attribute_type
        for attribute_type in AttributeType:
            integration_key = IntegrationKey(
                integration_id = integration.integration_id,
                integration_name = str(attribute_type),
            )
            if integration_key not in existing_attribute_integration_keys:
                new_attribute_types.add( attribute_type )
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
        IntegrationAttribute.objects.create(
            integration = integration,
            name = attribute_type.label,
            value = attribute_type.initial_value,
            value_type_str = str(attribute_type.value_type),
            value_range_str = json.dumps( attribute_type.value_range_dict ),
            integration_key_str = str(integration_key),
            attribute_type_str = AttributeType.PREDEFINED,
            is_editable = attribute_type.is_editable,
            is_required = attribute_type.is_required,
        )
        return
                
    def enable_integration( self,
                            integration_data               : IntegrationData,
                            integration_attribute_formset  : IntegrationAttributeFormSet ):
        with transaction.atomic():
            integration_data.integration.is_enabled = True
            integration_data.integration.save()
            integration_attribute_formset.save()
        self._start_integration_monitor( integration_data = integration_data )
        return
                
    def disable_integration( self, integration_data : IntegrationData ):

        with transaction.atomic():
            integration_data.integration.is_enabled = False
            integration_data.integration.save()
        self._stop_integration_monitor( integration_data = integration_data )
        return
    
