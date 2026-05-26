import logging
from typing import List, Optional

from hi.apps.entity.entity_placement import EntityPlacementInput
from hi.apps.entity.models import Entity
from hi.apps.system.enums import HealthStatusType

from hi.integrations.integration_gateway import IntegrationGateway
from hi.integrations.connector.integration_connector import IntegrationConnector
from hi.integrations.importer.integration_importer import IntegrationImporter
from hi.integrations.models import IntegrationAttribute
from hi.integrations.transient_models import (
    ConnectionTestResult,
    IntegrationMetaData,
    IntegrationValidationResult,
)

from hi.services.homebox.hb_manager import HomeBoxManager
from hi.services.homebox.hb_metadata import HbMetaData
from hi.services.homebox.hb_placement_grouper import HbPlacementGrouper
from hi.services.homebox.connector.homebox_connector import HomeBoxConnector
from hi.services.homebox.importer.homebox_importer import HomeBoxImporter

logger = logging.getLogger(__name__)


class HomeBoxGateway(IntegrationGateway):
    def get_metadata(self) -> IntegrationMetaData:
        return HbMetaData

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

    def get_connector(self) -> IntegrationConnector:
        return HomeBoxConnector()

    def get_importer(self) -> IntegrationImporter:
        return HomeBoxImporter()

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

    def group_entities_for_placement(
            self, entities: List[Entity],
    ) -> EntityPlacementInput:
        """HomeBox grouping: ordered Location → Tag → EntityType
        fallback. See ``HbPlacementGrouper`` for the policy."""
        grouper = HbPlacementGrouper(
            placement_item_key_fn = self._placement_item_key,
        )
        return grouper.group_entities( entities = entities )
