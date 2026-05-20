import logging
from typing import List, Optional

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
    ``test_connection`` returns a "not yet implemented" failure, and
    ``validate_configuration`` does the minimum schema check (BASE_URL
    must be present). Filled out incrementally during feature work.
    """

    FRIGATE_ENTITY_NAME = 'Frigate'
    FRIGATE_SYSTEM_INTEGRATION_NAME = 'system'
    FRIGATE_CAMERA_INTEGRATION_NAME_PREFIX = 'camera'
    MOVEMENT_SENSOR_PREFIX = 'camera.motion'
    OBJECT_PRESENCE_SENSOR_PREFIX = 'camera.object'

    def __init_singleton__(self):
        super().__init_singleton__()
        self._change_listeners = set()
        self._frigate_client : Optional[ FrigateClient ] = None
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
        try:
            integration = Integration.objects.get(
                integration_id = FrigateMetaData.integration_id,
            )
        except Integration.DoesNotExist:
            return
        if not integration.is_enabled:
            return
        integration_attributes = list( integration.attributes.all() )
        try:
            self._frigate_client = FrigateClientFactory.create_client(
                integration_attributes = integration_attributes,
            )
        except Exception:
            logger.exception( 'Failed to build Frigate client.' )
        return

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

    def test_connection(
            self,
            integration_attributes : List[ IntegrationAttribute ],
            timeout_secs           : Optional[ float ],
    ) -> ConnectionTestResult:
        """Live probe against the configured base URL.

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
            logger.exception( f'Error building Frigate client for test_connection: {e}' )
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
