import logging
from typing import List, Optional

from hi.apps.entity.models import Entity
from hi.apps.system.enums import HealthStatusType
from hi.apps.system.health_status_provider import HealthStatusProvider

from hi.integrations.connect.external_view_data import ExternalViewData
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

from .hb_controller import HomeBoxController
from .hb_manage_view_pane import HbManageViewPane
from .shared.hb_manager import HomeBoxManager
from .hb_metadata import HbMetaData
from .connector.hb_sync import HomeBoxSynchronizer
from .monitors import HomeBoxMonitor

logger = logging.getLogger(__name__)


class HomeBoxGateway(IntegrationGateway):
    def get_metadata(self) -> IntegrationMetaData:
        return HbMetaData

    def get_manage_view_pane(self) -> IntegrationManageViewPane:
        return HbManageViewPane()

    def get_monitor(self) -> PeriodicMonitor:
        return HomeBoxMonitor()

    def get_controller(self) -> IntegrationController:
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

    def get_health_status_provider(self) -> HealthStatusProvider:
        return HomeBoxManager()

    def get_synchronizer(self) -> IntegrationSynchronizer:
        return HomeBoxSynchronizer()

    def validate_configuration(
            self,
            integration_attributes: List[IntegrationAttribute]
    ) -> IntegrationValidationResult:
        """Schema-only validation; delegates to HomeBoxManager."""
        try:
            hb_manager = HomeBoxManager()
            return hb_manager.validate_configuration(integration_attributes)
        except Exception as e:
            logger.exception(f'Error validating HomeBox integration configuration: {e}')
            return IntegrationValidationResult.error(
                status=HealthStatusType.WARNING,
                error_message=f'Configuration validation failed: {e}'
            )

    def validate_access(
            self,
            integration_attributes: List[IntegrationAttribute],
            timeout_secs: Optional[float],
    ) -> ConnectionTestResult:
        """Live access validation probe; delegates to HomeBoxManager."""
        try:
            hb_manager = HomeBoxManager()
            return hb_manager.validate_access(
                integration_attributes = integration_attributes,
                timeout_secs = timeout_secs,
            )
        except Exception as e:
            logger.exception(f'Error in HomeBox access validation: {e}')
            return ConnectionTestResult.failure(f'Access validation error: {e}')

    def get_external_view_data(self, entity: Entity) -> Optional[ExternalViewData]:
        from .connector.hb_connector import HomeBoxConnector
        return HomeBoxConnector().get_external_view_data(entity)
