import logging
from typing import List, Optional

from hi.apps.system.enums import HealthStatusType

from hi.integrations.integration_gateway import IntegrationGateway
from hi.integrations.connector.integration_connector import IntegrationConnector
from hi.integrations.models import IntegrationAttribute
from hi.integrations.transient_models import (
    ConnectionTestResult,
    IntegrationMetaData,
    IntegrationValidationResult,
)

from .hass_manager import HassManager
from .hass_metadata import HassMetaData
from .hass_connector import HassConnector

logger = logging.getLogger(__name__)


class HassGateway( IntegrationGateway ):

    def get_metadata(self) -> IntegrationMetaData:
        return HassMetaData

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

    def get_connector(self) -> IntegrationConnector:
        return HassConnector()

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
