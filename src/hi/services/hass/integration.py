import logging
from typing import Dict, List

from hi.integrations.integration_controller import IntegrationController
from hi.integrations.integration_gateway import IntegrationGateway
from hi.integrations.integration_manage_view_pane import IntegrationManageViewPane
from hi.integrations.models import IntegrationAttribute
from hi.integrations.transient_models import IntegrationMetaData, IntegrationHealthStatus
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
    
    def get_health_status(self) -> IntegrationHealthStatus:
        """Get the current health status of the HASS integration.
        
        Delegates to HassManager for health status information.
        """
        try:
            hass_manager = HassManager()
            return hass_manager.get_health_status()
        except Exception as e:
            logger.exception(f'Error getting HASS integration health status: {e}')
            # Return a default error status if we can't get the real status
            from hi.integrations.transient_models import IntegrationHealthStatusType
            import hi.apps.common.datetimeproxy as datetimeproxy
            return IntegrationHealthStatus(
                status=IntegrationHealthStatusType.TEMPORARY_ERROR,
                last_check=datetimeproxy.now(),
                error_message=f'Failed to get health status: {e}'
            )
    
    def validate_configuration(self, integration_attributes: List[IntegrationAttribute]) -> Dict[str, any]:
        """Validate HASS integration configuration by testing API connectivity.
        
        Delegates to HassManager for configuration validation.
        """
        try:
            hass_manager = HassManager()
            return hass_manager.validate_configuration(integration_attributes)
        except Exception as e:
            logger.exception(f'Error validating HASS integration configuration: {e}')
            return {
                'success': False,
                'error_message': f'Configuration validation failed: {e}',
                'error_type': 'unknown'
            }
