import logging
from typing import List

from hi.apps.system.enums import HealthStatusType
from hi.apps.system.health_status_provider import HealthStatusProvider

from hi.integrations.integration_controller import IntegrationController
from hi.integrations.integration_gateway import IntegrationGateway
from hi.integrations.integration_manage_view_pane import IntegrationManageViewPane
from hi.integrations.models import IntegrationAttribute
from hi.integrations.transient_models import IntegrationMetaData, IntegrationValidationResult
from hi.apps.monitor.periodic_monitor import PeriodicMonitor

from .hb_manage_view_pane import HbManageViewPane
from .hb_metadata import HbMetaData

logger = logging.getLogger(__name__)


class HomeBoxGateway(IntegrationGateway):
    def get_metadata(self) -> IntegrationMetaData:
        return HbMetaData

    def get_manage_view_pane(self) -> IntegrationManageViewPane:
        return HbManageViewPane()

    def get_monitor(self) -> PeriodicMonitor:
        
        return HomeBoxMonitor()

    def get_controller(self) -> IntegrationController:
        # Implemente se necessário
        return HomeBoxController()

    def notify_settings_changed(self):
        """Notify HomeBox integration that settings have changed.
        
        Delegates to HomeBoxManager to reload configuration and notify monitors.
        """
        try:
            hb_manager = HomeBoxManager()
            hb_manager.notify_settings_changed()
            logger.debug('HomeBox integration notified of settings change')
        except Exception as e:
            logger.exception(f'Error notifying HomeBox integration of settings change: {e}')

    def get_health_status_provider(self):
        return HomeBoxManager()

    def validate_configuration(
            self,
            integration_attributes: List[IntegrationAttribute]
    ) -> IntegrationValidationResult:
        """Validate HomeBox integration configuration by testing API connectivity.

        Delegates to HomeBoxManager for configuration validation.
        """
        try:
            hb_manager = HomeBoxManager()
            return hb_manager.validate_configuration(integration_attributes)
        except Exception as e:
            logger.exception(f'Error validating HomeBox integration configuration: {e}')
            return IntegrationValidationResult.error(
                status=HealthStatusType.WARNING,
                error_message=f'Configuration validation failed: {e}'
            )
