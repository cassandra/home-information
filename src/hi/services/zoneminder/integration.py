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

from .zm_manager import ZoneMinderManager
from .zm_metadata import ZmMetaData
from .zm_connector import ZmConnector
from .zm_mixins import ZoneMinderMixin

logger = logging.getLogger(__name__)


class ZoneMinderGateway( IntegrationGateway, ZoneMinderMixin ):

    def get_metadata(self) -> IntegrationMetaData:
        return ZmMetaData

    def notify_settings_changed(self):
        """Notify ZoneMinder integration that settings have changed.

        Delegates to ZoneMinderManager to reload configuration and notify monitors.
        """
        try:
            zm_manager = ZoneMinderManager()
            zm_manager.notify_settings_changed()
            logger.debug('ZoneMinder integration notified of settings change')
        except Exception as e:
            logger.exception(f'Error notifying ZoneMinder integration of settings change: {e}')

    def get_connector(self) -> IntegrationConnector:
        return ZmConnector()

    def validate_configuration(
            self,
            integration_attributes: List[IntegrationAttribute]
    ) -> IntegrationValidationResult:
        """Schema-only validation; delegates to ZoneMinderManager."""
        try:
            zm_manager = ZoneMinderManager()
            return zm_manager.validate_configuration(integration_attributes)
        except Exception as e:
            logger.exception(f'Error validating ZoneMinder integration configuration: {e}')
            return IntegrationValidationResult.error(
                status=HealthStatusType.WARNING,
                error_message=f'Configuration validation failed: {e}'
            )

    def validate_access(
            self,
            integration_attributes: List[IntegrationAttribute],
            timeout_secs: Optional[float],
    ) -> ConnectionTestResult:
        """Live access validation probe; delegates to ZoneMinderManager."""
        try:
            zm_manager = ZoneMinderManager()
            return zm_manager.validate_access(
                integration_attributes=integration_attributes,
                timeout_secs=timeout_secs,
            )
        except Exception as e:
            logger.exception(f'Error in ZoneMinder access validation: {e}')
            return ConnectionTestResult.failure(f'Access validation error: {e}')
