from typing import List, Optional

from hi.apps.entity.entity_placement import (
    EntityPlacementInput,
    PlacementInputBuilder,
)
from hi.apps.entity.models import Entity

from hi.integrations.connector.integration_connector import IntegrationConnector
from hi.integrations.importer.integration_importer import IntegrationImporter
from hi.integrations.models import IntegrationAttribute
from hi.integrations.transient_models import (
    ConnectionTestResult,
    IntegrationMetaData,
    IntegrationValidationResult,
)


class IntegrationGateway:
    """
    Each integration needs to provide an Integration Manager that implements these methods.
    """

    def get_metadata(self) -> IntegrationMetaData:
        raise NotImplementedError('Subclasses must override this method')

    def notify_settings_changed(self):
        """
        This method is called when Integration or IntegrationAttribute models
        are modified. Each integration should implement this to reload its
        configuration and notify any dependent components.
        """
        raise NotImplementedError('Subclasses must override this method')

    def get_connector(self) -> Optional[IntegrationConnector]:
        """
        Return the integration's connector when it supports sync;
        None otherwise. Sync is an opt-in capability — not every
        integration requires one. The framework owns the sync workflow
        (pre-sync confirmation, sync execution, post-sync placement);
        the connector participates by providing the integration-
        specific work plus a small amount of peripheral metadata.

        The Issue #283 sync-check probe also rides on the connector
        (see ``IntegrationConnector.check_needs_sync``): integrations
        without a connector naturally opt out of both full sync and
        the periodic drift check.
        """
        return None

    def get_importer(self) -> Optional[IntegrationImporter]:
        """
        Return the integration's importer when it supports the IMPORT
        capability; None otherwise. Parallel to get_connector() for
        the CONNECT capability. The framework owns the import workflow
        (Data Import page, preview, confirm, result modal, placement);
        the importer supplies the integration-specific candidate
        listing, item ingest, and discard operations.
        """
        return None

    def validate_configuration(
            self,
            integration_attributes: List[IntegrationAttribute]
    ) -> IntegrationValidationResult:
        """
        Schema-only validation of the proposed configuration. Must NOT
        perform network operations. Returns success if the attribute set
        is structurally usable; returns an error otherwise. For live
        access validation, see validate_access().
        """
        raise NotImplementedError('Subclasses must override this method')

    def validate_access(
            self,
            integration_attributes: List[IntegrationAttribute],
            timeout_secs: Optional[float],
    ) -> ConnectionTestResult:
        """
        Live probe to validate access to the upstream system using the
        proposed configuration. Must respect the bounded timeout. Used
        at attribute-save time (Configure / Reconfigure) and before
        relaunching monitors (Resume).
        """
        raise NotImplementedError('Subclasses must override this method')

    def group_entities_for_placement(
            self, entities: List[Entity],
    ) -> EntityPlacementInput:
        """Partition the given entities into the EntityPlacementInput
        shape consumed by the placement modal. Capability-neutral —
        both Connect-sync and Import-run flows feed entities through
        this same method, so a given integration groups its entities
        the same way regardless of how they arrived.

        Default: group by ``EntityGroupType`` rollup using the
        rollup's humanized label as the group name. Subclasses
        override when a different domain grouping makes sense
        (e.g., HomeBox's Location/Tag/Type fallback)."""
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
