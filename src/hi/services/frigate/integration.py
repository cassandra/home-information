import logging
from typing import List, Optional

from hi.apps.entity.entity_placement import (
    EntityPlacementGroup,
    EntityPlacementInput,
    EntityPlacementItem,
)
from hi.apps.entity.models import Entity
from hi.apps.system.enums import HealthStatusType

from hi.integrations.integration_gateway import IntegrationGateway
from hi.integrations.connector.integration_connector import IntegrationConnector
from hi.integrations.models import IntegrationAttribute
from hi.integrations.transient_models import (
    ConnectionTestResult,
    IntegrationMetaData,
    IntegrationValidationResult,
)

from .frigate_manager import FrigateManager
from .frigate_metadata import FrigateMetaData
from .frigate_mixins import FrigateMixin
from .frigate_connector import FrigateConnector

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

    def notify_settings_changed(self):
        try:
            FrigateManager().notify_settings_changed()
            logger.debug( 'Frigate integration notified of settings change.' )
        except Exception as e:
            logger.exception(
                f'Error notifying Frigate integration of settings change: {e}'
            )

    def get_connector(self) -> IntegrationConnector:
        return FrigateConnector()

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

    def validate_access(
            self,
            integration_attributes : List[ IntegrationAttribute ],
            timeout_secs           : Optional[ float ],
    ) -> ConnectionTestResult:
        try:
            return FrigateManager().validate_access(
                integration_attributes = integration_attributes,
                timeout_secs = timeout_secs,
            )
        except Exception as e:
            logger.exception( f'Error in Frigate access validation: {e}' )
            return ConnectionTestResult.failure( f'Access validation error: {e}' )

    def group_entities_for_placement(
            self, entities: List[Entity],
    ) -> EntityPlacementInput:
        """Single 'Cameras' placement group: Frigate cameras usually
        share a wall-of-views layout, so 'all cameras → same place'
        is the right default. Operators can still drill into
        per-camera placement from the dispatcher."""
        if not entities:
            return EntityPlacementInput()
        items = [
            EntityPlacementItem(
                key = self._placement_item_key( entity = entity ),
                label = entity.name,
                entity = entity,
            )
            for entity in entities
        ]
        return EntityPlacementInput(
            groups = [ EntityPlacementGroup( label = 'Cameras', items = items ) ],
        )
