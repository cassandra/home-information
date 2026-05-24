import logging
from typing import List, Optional

from hi.apps.entity.models import Entity
from hi.apps.entity.transient_models import VideoSnapshot
from hi.apps.system.enums import HealthStatusType
from hi.apps.system.health_status_provider import HealthStatusProvider

from hi.integrations.connect.integration_controller import IntegrationController
from hi.integrations.connect.integration_gateway import IntegrationGateway
from hi.integrations.connect.integration_manage_view_pane import IntegrationManageViewPane
from hi.integrations.connect.integration_synchronizer import IntegrationSynchronizer
from hi.integrations.models import IntegrationAttribute
from hi.integrations.transient_models import (
    ConnectionTestResult,
    IntegrationMetaData,
    IntegrationValidationResult,
)
from hi.apps.monitor.periodic_monitor import PeriodicMonitor

from .hass_controller import HassController
from .hass_manage_view_pane import HassManageViewPane
from .hass_manager import HassManager
from .hass_metadata import HassMetaData
from .hass_sync import HassSynchronizer
from .monitors import HassMonitor

logger = logging.getLogger(__name__)


class HassGateway( IntegrationGateway ):

    def get_metadata(self) -> IntegrationMetaData:
        return HassMetaData

    def get_manage_view_pane(self) -> IntegrationManageViewPane:
        return HassManageViewPane()

    def get_monitor(self) -> PeriodicMonitor:
        return HassMonitor()
    
    def get_controller(self) -> IntegrationController:
        return HassController()
    
    def notify_settings_changed(self):
        """Notify HASS integration that settings have changed.
        
        Delegates to HassManager to reload configuration and notify monitors.
        """
        try:
            hass_manager = HassManager()
            hass_manager.notify_settings_changed()
            logger.debug('HASS integration notified of settings change')
        except Exception as e:
            logger.exception(f'Error notifying HASS integration of settings change: {e}')
    
    def get_health_status_provider(self) -> HealthStatusProvider:
        return HassManager()

    def get_synchronizer(self) -> IntegrationSynchronizer:
        return HassSynchronizer()

    def validate_configuration(
            self, integration_attributes: List[IntegrationAttribute]
    ) -> IntegrationValidationResult:
        """Schema-only validation; delegates to HassManager."""
        try:
            hass_manager = HassManager()
            return hass_manager.validate_configuration(integration_attributes)
        except Exception as e:
            logger.exception(f'Error validating HASS integration configuration: {e}')
            return IntegrationValidationResult.error(
                status=HealthStatusType.WARNING,
                error_message=f'Configuration validation failed: {e}'
            )

    def validate_access(
            self,
            integration_attributes: List[IntegrationAttribute],
            timeout_secs: Optional[float],
    ) -> ConnectionTestResult:
        """Live access validation probe; delegates to HassManager."""
        try:
            hass_manager = HassManager()
            return hass_manager.validate_access(
                integration_attributes=integration_attributes,
                timeout_secs=timeout_secs,
            )
        except Exception as e:
            logger.exception(f'Error in HASS access validation: {e}')
            return ConnectionTestResult.failure(f'Access validation error: {e}')

    def get_entity_video_snapshot(self, entity: Entity) -> Optional[VideoSnapshot]:
        if not entity.has_video_snapshot:
            return None
        if entity.integration_id != HassMetaData.integration_id:
            return None

        hass_manager = HassManager()
        # ``Entity.integration_name`` is the HassDevice device_id (an HI
        # grouping construct), not the HA state id the attrs cache is
        # keyed by. The manager bridges the two via a sync-time-built
        # map of HI Entity.id -> camera-domain HA state id.
        ha_state_id = hass_manager.get_ha_state_id_for_entity( entity )
        if not ha_state_id:
            return None

        attrs = hass_manager.get_latest_attrs( ha_state_id )
        if not attrs:
            return None

        entity_picture = attrs.get( 'entity_picture' )
        if not entity_picture:
            return None

        # Some HA integrations emit an absolute URL; pass those
        # through unchanged. Relative paths get the HA base prefix.
        if entity_picture.startswith( ('http://', 'https://') ):
            source_url = entity_picture
        else:
            client = hass_manager.hass_client
            if not client:
                return None
            source_url = f'{client.api_base_url}{entity_picture}'

        return VideoSnapshot( source_url = source_url )
