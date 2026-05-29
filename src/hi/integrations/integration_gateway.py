from typing import List, Optional

from hi.apps.entity.entity_placement import (
    EntityPlacementInput,
    PlacementInputBuilder,
)
from hi.apps.entity.models import Entity

from hi.integrations.referencer.integration_referencer import (
    IntegrationAttributeReferencer,
)
from hi.integrations.connector.integration_connector import IntegrationConnector
from hi.integrations.importer.integration_importer import IntegrationImporter
from hi.integrations.models import IntegrationAttribute
from hi.integrations.transient_models import (
    ConnectionTestResult,
    IntegrationMetaData,
    IntegrationValidationResult,
)


class IntegrationGateway:
    """Subclassed by each integration to expose its lifecycle and capability hooks."""

    def get_metadata(self) -> IntegrationMetaData:
        raise NotImplementedError('Subclasses must override this method')

    def notify_settings_changed(self):
        """Called when Integration or IntegrationAttribute models are
        modified. Default is no-op; integrations with cached upstream
        clients or manager state override to reload them. Reference-
        only integrations (no connector, no monitor) have nothing to
        reload on a settings change and inherit the default."""
        return

    def get_connector(self) -> Optional[IntegrationConnector]:
        """Return the integration's connector when it supports the CONNECT
        capability; None otherwise. The framework owns the sync workflow;
        the connector supplies the integration-specific work and metadata.

        Integrations without a connector opt out of both full sync and the
        periodic drift check (the sync-check probe rides on the connector)."""
        return None

    def get_importer(self) -> Optional[IntegrationImporter]:
        """Return the integration's importer when it supports the IMPORT
        capability; None otherwise. The framework owns the import workflow;
        the importer supplies integration-specific candidate listing, item
        ingest, and discard operations."""
        return None

    def get_attribute_referencer(self) -> Optional[IntegrationAttributeReferencer]:
        """Return the integration's attribute-referencer when it supports the
        ATTRIBUTE_REFERENCE capability; None otherwise. The framework owns
        the picker and the TEXT-attribute attach lifecycle; the referencer
        supplies the integration-specific search-against-upstream operation."""
        return None

    def validate_configuration(
            self,
            integration_attributes: List[IntegrationAttribute]
    ) -> IntegrationValidationResult:
        """Schema-only validation of the proposed configuration. Must NOT
        perform network operations. For live access validation, see
        ``validate_access``."""
        raise NotImplementedError('Subclasses must override this method')

    def validate_access(
            self,
            integration_attributes: List[IntegrationAttribute],
            timeout_secs: Optional[float],
    ) -> ConnectionTestResult:
        """Live probe to validate access to the upstream system using the
        proposed configuration. Must respect the bounded timeout."""
        raise NotImplementedError('Subclasses must override this method')

    def group_entities_for_placement(
            self, entities: List[Entity],
    ) -> EntityPlacementInput:
        """Partition the given entities into the EntityPlacementInput shape
        consumed by placement. Capability-neutral -- both sync and import
        flows feed entities through this method, so a given integration
        groups its entities the same way regardless of how they arrived.

        Default: group by ``EntityGroupType`` rollup using the rollup's
        humanized label as the group name. Subclasses override when a
        different domain grouping makes sense."""
        return PlacementInputBuilder.by_entity_type_group(
            entities    = entities,
            item_key_fn = self._placement_item_key,
        )

    def _placement_item_key(self, entity: Entity) -> str:
        """Stable per-entity placement key. Prefers the live
        integration_key, falls back to previous_integration_key for
        imported/detached entities, then to the row id as a final
        fallback for entities with no integration provenance at all."""
        if entity.integration_key:
            ikey = entity.integration_key
            return f'{ikey.integration_id}:{ikey.integration_name}'
        if entity.previous_integration_key:
            pkey = entity.previous_integration_key
            return f'{pkey.integration_id}:{pkey.integration_name}'
        return f'entity:{entity.id}'
