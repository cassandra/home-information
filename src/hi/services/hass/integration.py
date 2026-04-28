import logging
from typing import List, Optional

from hi.apps.system.enums import HealthStatusType
from hi.apps.system.health_status_provider import HealthStatusProvider

from hi.integrations.integration_controller import IntegrationController
from hi.integrations.integration_gateway import IntegrationGateway
from hi.integrations.integration_manage_view_pane import IntegrationManageViewPane
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

    def test_connection(
            self,
            integration_attributes: List[IntegrationAttribute],
            timeout_secs: Optional[float],
    ) -> ConnectionTestResult:
        """Live connection probe; delegates to HassManager."""
        try:
            hass_manager = HassManager()
            return hass_manager.test_connection(
                integration_attributes=integration_attributes,
                timeout_secs=timeout_secs,
            )
        except Exception as e:
            logger.exception(f'Error in HASS connection test: {e}')
            return ConnectionTestResult.failure(f'Connection test error: {e}')
