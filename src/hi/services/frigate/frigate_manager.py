import logging
import time
from typing import Dict, List, Optional

from asgiref.sync import sync_to_async

from hi.apps.common.utils import str_to_bool

from hi.apps.common.singleton_manager import SingletonManager
from hi.apps.system.aggregate_health_provider import AggregateHealthProvider
from hi.apps.system.api_health_status_provider import ApiHealthStatusProvider
from hi.apps.system.enums import HealthStatusType
from hi.apps.system.provider_info import ProviderInfo

from hi.integrations.models import IntegrationAttribute
from hi.integrations.transient_models import (
    ConnectionTestResult,
    IntegrationKey,
    IntegrationValidationResult,
)

from hi.integrations.models import Integration

from .constants import FrigateApi
from .enums import FrigateAttributeType
from .frigate_client import FrigateClient
from .frigate_client_factory import FrigateClientFactory
from .frigate_metadata import FrigateMetaData

logger = logging.getLogger(__name__)


class FrigateManager( SingletonManager, AggregateHealthProvider, ApiHealthStatusProvider ):
    """Singleton coordinator for the Frigate integration.

    Owns the lazily-constructed ``FrigateClient`` (built from persisted
    IntegrationAttribute records), brokers configuration validation and
    connection probes, and dispatches settings-changed notifications to
    registered listeners. Mirrors ``ZoneMinderManager`` in role.

    Scaffolding stub: ``_reload_implementation`` is a no-op,
    ``validate_access`` returns a "not yet implemented" failure, and
    ``validate_configuration`` does the minimum schema check (BASE_URL
    must be present). Filled out incrementally during feature work.
    """

    FRIGATE_ENTITY_NAME = 'Frigate'
    FRIGATE_SYSTEM_INTEGRATION_NAME = 'system'
    FRIGATE_CAMERA_INTEGRATION_NAME_PREFIX = 'camera'
    OBJECT_PRESENCE_SENSOR_PREFIX = 'camera.object'
    OBJECT_PRESENCE_EVENT_PREFIX = 'camera.object.event'

    def __init_singleton__(self):
        super().__init_singleton__()
        self._change_listeners = set()
        self._frigate_client : Optional[ FrigateClient ] = None
        self._attribute_map : Dict[ FrigateAttributeType, IntegrationAttribute ] = {}
        self.add_api_health_status_provider( self )
        return

    @classmethod
    def get_provider_info(cls) -> ProviderInfo:
        return ProviderInfo(
            provider_id = 'hi.services.frigate.manager',
            provider_name = 'Frigate Integration',
            description = '',
        )

    @classmethod
    def get_api_provider_info(cls) -> ProviderInfo:
        return ProviderInfo(
            provider_id = 'hi.services.frigate.api',
            provider_name = 'Frigate API',
            description = 'Frigate NVR HTTP API',
        )

    def _reload_implementation(self):
        """Pull current attribute values and (re)build the API client.

        Called under ``SingletonManager``'s data lock. The client is
        nulled on every reload and only re-created when the integration
        DB row is present and enabled. Sync / monitor consumers should
        gate on ``frigate_client is not None`` before calling out."""
        self._frigate_client = None
        self._attribute_map = {}
        try:
            integration = Integration.objects.get(
                integration_id = FrigateMetaData.integration_id,
            )
        except Integration.DoesNotExist:
            self.record_disabled( 'Frigate integration disabled' )
            return
        if not integration.is_enabled:
            self.record_disabled( 'Frigate integration disabled' )
            return
        integration_attributes = list( integration.attributes.all() )
        self._attribute_map = self._build_attribute_map(
            integration_attributes = integration_attributes,
        )
        try:
            self._frigate_client = FrigateClientFactory.create_client(
                integration_attributes = integration_attributes,
            )
        except Exception:
            logger.exception( 'Failed to build Frigate client.' )
            self.record_error( 'Failed to build Frigate client' )
            return
        self.record_healthy( 'Reloaded' )
        return

    @staticmethod
    def _build_attribute_map(
            integration_attributes : List[ IntegrationAttribute ],
    ) -> Dict[ FrigateAttributeType, IntegrationAttribute ]:
        attribute_map : Dict[ FrigateAttributeType, IntegrationAttribute ] = {}
        for attr_type in FrigateAttributeType:
            target_key = IntegrationKey(
                integration_id = FrigateMetaData.integration_id,
                integration_name = str( attr_type ),
            )
            for attr in integration_attributes:
                if attr.integration_key == target_key:
                    attribute_map[ attr_type ] = attr
                    break
                continue
            continue
        return attribute_map

    @property
    def should_add_alarm_events( self ) -> bool:
        self.ensure_initialized()
        attribute = self._attribute_map.get( FrigateAttributeType.ADD_ALARM_EVENTS )
        if attribute:
            return str_to_bool( attribute.value )
        return False

    @property
    def frigate_client(self) -> Optional[ FrigateClient ]:
        """Lazily-constructed ``FrigateClient`` built against current
        integration attributes. Returns ``None`` when the integration
        is disabled or the configuration is unusable."""
        self.ensure_initialized()
        return self._frigate_client

    # ---- Integration-key helpers ------------------------------------

    @classmethod
    def _to_integration_key( cls, prefix : str, camera_name : str ) -> IntegrationKey:
        """Build a per-camera ``IntegrationKey`` with a stable scheme:
        ``<prefix>.<camera_name>`` for the integration_name slot. The
        prefixes (``camera`` / ``camera.motion`` / ``camera.object``)
        live as constants on this manager."""
        return IntegrationKey(
            integration_id = FrigateMetaData.integration_id,
            integration_name = f'{prefix}.{camera_name}',
        )

    # ---- Client-facing helpers (used by FrigateMonitor) -------------

    def get_cameras( self ) -> List[ Dict ]:
        """Camera list from ``/api/config``. Raises when the client
        isn't built yet (integration disabled / unconfigured) — the
        monitor's outer try/except records this as a health warning."""
        client = self.frigate_client
        if client is None:
            raise RuntimeError( 'Frigate client not available.' )
        with self.api_call_context( 'frigate_cameras' ):
            return client.get_cameras()

    async def get_cameras_async( self ) -> List[ Dict ]:
        return await sync_to_async(
            self.get_cameras,
            thread_sensitive = True,
        )()

    def get_events( self,
                    after  : Optional[ float ] = None,
                    limit  : Optional[ int ]   = None ) -> List[ Dict ]:
        """Events from ``/api/events``. ``after`` is the polling
        cursor in epoch seconds; ``limit`` caps the returned count
        when set."""
        client = self.frigate_client
        if client is None:
            raise RuntimeError( 'Frigate client not available.' )
        with self.api_call_context( 'frigate_events' ):
            return client.get_events( after = after, limit = limit )

    async def get_events_async( self,
                                after  : Optional[ float ] = None,
                                limit  : Optional[ int ]   = None ) -> List[ Dict ]:
        return await sync_to_async(
            self.get_events,
            thread_sensitive = True,
        )( after = after, limit = limit )

    def get_event( self, event_id : str ) -> Dict:
        """Single event detail by id. Raises ``Http404`` when the
        event no longer exists in Frigate (cleared from history)."""
        client = self.frigate_client
        if client is None:
            raise RuntimeError( 'Frigate client not available.' )
        with self.api_call_context( 'frigate_event_detail' ):
            return client.get_event( event_id = event_id )

    async def get_event_async( self, event_id : str ) -> Dict:
        return await sync_to_async(
            self.get_event,
            thread_sensitive = True,
        )( event_id = event_id )

    # ---- Media URL helpers ------------------------------------------

    def get_camera_snapshot_url( self, camera_name : str ) -> Optional[ str ]:
        """Live-frame JPEG URL for a camera. Returns ``None`` when the
        client isn't available."""
        client = self.frigate_client
        if client is None:
            return None
        path = FrigateApi.CAMERA_SNAPSHOT_PATH_TEMPLATE.format(
            camera_name = camera_name,
        )
        return f'{client.base_url}{path}?_t={int(time.time())}'

    def get_event_snapshot_url( self, event_id : str ) -> Optional[ str ]:
        """Event-frame JPEG URL. Returns ``None`` when the client
        isn't available."""
        client = self.frigate_client
        if client is None:
            return None
        path = FrigateApi.EVENT_SNAPSHOT_PATH_TEMPLATE.format(
            event_id = event_id,
        )
        return f'{client.base_url}{path}?_t={int(time.time())}'

    def get_event_clip_url( self, event_id : str ) -> Optional[ str ]:
        """Event-clip MP4 URL. Returns ``None`` when the client
        isn't available."""
        client = self.frigate_client
        if client is None:
            return None
        path = FrigateApi.EVENT_CLIP_PATH_TEMPLATE.format(
            event_id = event_id,
        )
        return f'{client.base_url}{path}?_t={int(time.time())}'

    @classmethod
    def _frigate_integration_key( cls ) -> IntegrationKey:
        """Integration key for the (future) singleton Frigate service
        entity. Held in reserve for v2 when ``/api/stats`` lands;
        unused in v1, which is cameras-only."""
        return IntegrationKey(
            integration_id = FrigateMetaData.integration_id,
            integration_name = cls.FRIGATE_SYSTEM_INTEGRATION_NAME,
        )

    # ---- Settings-change plumbing -----------------------------------

    def register_change_listener( self, callback ):
        if callback not in self._change_listeners:
            logger.debug( f'Adding Frigate setting change listener from {callback.__module__}' )
            self._change_listeners.add( callback )
        return

    def notify_settings_changed(self):
        self.reload()
        for callback in self._change_listeners:
            try:
                callback()
            except Exception:
                logger.exception( 'Problem calling Frigate change-listener callback.' )
            continue
        return

    # ---- Gateway-facing API -----------------------------------------

    def validate_configuration(
            self,
            integration_attributes : List[ IntegrationAttribute ],
    ) -> IntegrationValidationResult:
        """Schema-only validation. No network calls."""
        base_url = self._attr_value(
            integration_attributes = integration_attributes,
            attr_type = FrigateAttributeType.BASE_URL,
        )
        if not base_url:
            return IntegrationValidationResult.error(
                status = HealthStatusType.WARNING,
                error_message = 'Base URL is required.',
            )
        return IntegrationValidationResult.success()

    def validate_access(
            self,
            integration_attributes : List[ IntegrationAttribute ],
            timeout_secs           : Optional[ float ],
    ) -> ConnectionTestResult:
        """Live access validation against the configured base URL.

        Builds a temporary ``FrigateClient`` from the proposed
        attributes and calls ``ping()``. Bounded by ``timeout_secs``
        so the Configure form can fail interactively rather than
        wait on a stalled host."""
        try:
            client = FrigateClientFactory.create_client(
                integration_attributes = integration_attributes,
                timeout_secs = timeout_secs,
            )
        except ValueError as e:
            return ConnectionTestResult.failure( str( e ) )
        except Exception as e:
            logger.exception( f'Error building Frigate client for validate_access: {e}' )
            return ConnectionTestResult.failure( f'Configuration error: {e}' )

        try:
            client.ping()
        except ValueError as e:
            return ConnectionTestResult.failure( str( e ) )
        except Exception as e:
            return ConnectionTestResult.failure( f'Connection error: {e}' )
        return ConnectionTestResult.success()

    @property
    def integration_id(self) -> str:
        return FrigateMetaData.integration_id

    @staticmethod
    def _attr_value(
            integration_attributes : List[ IntegrationAttribute ],
            attr_type              : FrigateAttributeType,
    ) -> Optional[ str ]:
        """Look up an attribute value by type. ``IntegrationAttribute``
        carries an ``integration_key`` whose ``integration_name`` is
        ``str(attr_type)`` (the lowercased slug LabeledEnum yields);
        matching directly on that field is the framework's convention."""
        target_key = IntegrationKey(
            integration_id = FrigateMetaData.integration_id,
            integration_name = str( attr_type ),
        )
        for attr in integration_attributes:
            if attr.integration_key == target_key:
                return attr.value
            continue
        return None
