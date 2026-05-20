import logging
from typing import List, Optional

from hi.apps.monitor.periodic_monitor import PeriodicMonitor
from hi.apps.system.enums import HealthStatusType
from hi.apps.system.health_status_provider import HealthStatusProvider

from hi.integrations.integration_controller import IntegrationController
from hi.integrations.integration_gateway import IntegrationGateway
from hi.integrations.integration_manage_view_pane import IntegrationManageViewPane
from hi.integrations.integration_synchronizer import IntegrationSynchronizer
from hi.integrations.models import IntegrationAttribute
from hi.integrations.transient_models import (
    ConnectionTestResult,
    IntegrationMetaData,
    IntegrationValidationResult,
)

from .frigate_controller import FrigateController
from .frigate_manage_view_pane import FrigateManageViewPane
from .frigate_manager import FrigateManager
from .frigate_metadata import FrigateMetaData
from .frigate_mixins import FrigateMixin
from .frigate_sync import FrigateSynchronizer
from .monitors import FrigateMonitor

logger = logging.getLogger(__name__)


class FrigateGateway( IntegrationGateway, FrigateMixin ):
    """Framework entry point for the Frigate integration.

    Auto-discovered by ``IntegrationManager.discover_defined_integrations``
    because this module exposes an ``IntegrationGateway`` subclass and
    lives under ``hi.services.*``. Delegates almost everything to the
    other pieces of the integration; see
    ``docs/dev/integrations/integration-guidelines.md`` for the
    contract this class satisfies.
    """

    def get_metadata(self) -> IntegrationMetaData:
        return FrigateMetaData

    def get_manage_view_pane(self) -> IntegrationManageViewPane:
        return FrigateManageViewPane()

    def get_monitor(self) -> PeriodicMonitor:
        return FrigateMonitor()

    def get_controller(self) -> IntegrationController:
        return FrigateController()

    def notify_settings_changed(self):
        try:
            FrigateManager().notify_settings_changed()
            logger.debug( 'Frigate integration notified of settings change.' )
        except Exception as e:
            logger.exception(
                f'Error notifying Frigate integration of settings change: {e}'
            )

    def get_health_status_provider(self) -> HealthStatusProvider:
        return FrigateManager()

    def get_synchronizer(self) -> IntegrationSynchronizer:
        return FrigateSynchronizer()

    def validate_configuration(
            self,
            integration_attributes : List[ IntegrationAttribute ],
    ) -> IntegrationValidationResult:
        try:
            return FrigateManager().validate_configuration(
                integration_attributes = integration_attributes,
            )
        except Exception as e:
            logger.exception( f'Error validating Frigate configuration: {e}' )
            return IntegrationValidationResult.error(
                status = HealthStatusType.WARNING,
                error_message = f'Configuration validation failed: {e}',
            )

    def test_connection(
            self,
            integration_attributes : List[ IntegrationAttribute ],
            timeout_secs           : Optional[ float ],
    ) -> ConnectionTestResult:
        try:
            return FrigateManager().test_connection(
                integration_attributes = integration_attributes,
                timeout_secs = timeout_secs,
            )
        except Exception as e:
            logger.exception( f'Error in Frigate connection test: {e}' )
            return ConnectionTestResult.failure( f'Connection test error: {e}' )
