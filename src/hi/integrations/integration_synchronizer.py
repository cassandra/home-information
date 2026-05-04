"""
Per-integration synchronizer base class.

The general integration framework owns the sync workflow (pre-sync
confirmation modal, sync execution view, post-sync placement modal).
The synchronizer is the per-integration participant that the framework
hands off to for the integration-specific work plus a small amount of
peripheral metadata the framework surfaces alongside.

Each integration that supports sync provides a concrete subclass and
returns an instance of it from `IntegrationGateway.get_synchronizer()`.
Sync is opt-in: a gateway whose integration does not support sync
returns None.
"""
import logging
from typing import List, Optional

from hi.apps.common.database_lock import ExclusionLockContext
from hi.apps.entity.entity_placement import (
    EntityPlacementInput,
    EntityPlacementItem,
)
from hi.apps.entity.models import Entity

from .entity_operations import EntityIntegrationOperations
from .sync_result import IntegrationSyncResult
from .user_data_detector import EntityUserDataDetector

logger = logging.getLogger(__name__)


class IntegrationSynchronizer:
    """
    Base class for per-integration synchronizers.

    The framework calls `sync()`. The base implementation acquires a
    process-wide synchronization lock, delegates to the subclass's
    `_sync_impl()`, and converts unexpected RuntimeError into a result
    object. Subclasses implement the integration-specific work in
    `_sync_impl()` and the small metadata accessors below.

    Synchronization is process-wide rather than per-integration: at
    most one integration sync runs at a time. Concurrent syncs across
    integrations could race over shared infrastructure (entity tables,
    location-view bookkeeping in later phases) and the user is unlikely
    to need parallelism here. Override at a subclass level if a future
    integration genuinely needs concurrent sync.
    """

    # Single shared lock name across all integration syncs. See class
    # docstring above for the rationale.
    SYNCHRONIZATION_LOCK_NAME = 'integrations_sync'

    def get_description(self, is_initial_import: bool) -> Optional[str]:
        """
        Optional copy describing what this integration's sync will do,
        surfaced to the operator in the framework's pre-sync
        confirmation modal alongside a generic lead message.

        `is_initial_import` distinguishes the first-time IMPORT (no
        entities have been imported yet) from subsequent REFRESH
        operations. The two contexts mean different things to the
        operator and integrations are encouraged to provide tailored
        copy for each. Return None to render only the generic lead
        text.
        """
        return None

    def get_result_title(self, is_initial_import: bool) -> str:
        """
        Short, generic header for the sync result modal: 'Import
        Result' for the first-time path, 'Refresh Result' otherwise.
        The integration's identity is surfaced in the modal body
        (logo + label) rather than the title bar — keeps the title
        bar contrast predictable regardless of integration. Override
        only if a specific integration genuinely needs custom copy.
        """
        if is_initial_import:
            return 'Import Result'
        return 'Refresh Result'

    def sync(self, is_initial_import: bool) -> IntegrationSyncResult:
        """
        Public entry point used by the framework. Wraps `_sync_impl`
        with the sync lock and standard error handling. Subclasses
        override `_sync_impl` rather than this method.

        ``is_initial_import`` is the operator-intent flag from the
        sync flow (Import for first-time, Refresh otherwise);
        threaded down so each subclass can title its result
        consistently.
        """
        try:
            with ExclusionLockContext(name=self.SYNCHRONIZATION_LOCK_NAME):
                logger.debug(f'{self.__class__.__name__} sync started.')
                return self._sync_impl(is_initial_import=is_initial_import)
        except RuntimeError as e:
            logger.exception(e)
            return IntegrationSyncResult(
                title=self.get_result_title(is_initial_import=is_initial_import),
                error_list=[str(e)],
            )
        finally:
            logger.debug(f'{self.__class__.__name__} sync ended.')

    def _sync_impl(self, is_initial_import: bool) -> IntegrationSyncResult:
        """
        Integration-specific sync work. Subclasses must override.
        Called with the synchronization lock held.
        """
        raise NotImplementedError('Subclasses must override this method')

    def group_entities_for_placement(
            self, entities : List[Entity],
    ) -> EntityPlacementInput:
        """Partition a set of entities into the
        ``EntityPlacementInput`` shape consumed by the placement
        modal.

        Two callers:

        * The sync flow passes in the entities just *created* during
          this sync run (existing-entity updates do not need
          re-placement).
        * A future "place unplaced items" recovery feature will pass
          in entities that already exist for the integration but have
          no EntityView row.

        Either caller receives the same shape; the per-integration
        grouping logic lives in this method so both callers agree
        on what "groups" means for this integration.

        Default implementation: every entity is ungrouped. Subclasses
        override to provide a meaningful domain grouping (e.g., HASS
        by entity_type, ZM single "Monitors" group).
        """
        return EntityPlacementInput(
            ungrouped_items = [
                EntityPlacementItem(
                    key = self._placement_item_key( entity = entity ),
                    label = entity.name,
                    entity = entity,
                )
                for entity in entities
            ],
        )

    def _placement_item_key( self, entity : Entity ) -> str:
        """Stable per-entity placement key. Subclasses may override
        for custom keying; the default uses the entity's
        integration_key when available, falling back to the row id."""
        integration_key = entity.integration_key
        if integration_key:
            return f'{integration_key.integration_id}:{integration_key.integration_name}'
        return f'entity:{entity.id}'

    def _remove_entity_intelligently(self,
                                     entity: Entity,
                                     result: IntegrationSyncResult,
                                     integration_name: str):
        """
        Remove an entity that no longer exists in the integration.

        If the entity has user-created attributes, preserve the entity but
        disconnect it from the integration and remove only integration-
        related components. Otherwise, perform complete deletion.

        Appends the entity's *current* name (captured before any
        rename in the preserve path) to ``result.removed_list`` —
        both 'preserve with user data' and 'hard delete' are
        operator-visible removals from the integration's perspective.
        """
        result.removed_list.append(entity.name)
        if EntityUserDataDetector.has_user_created_attributes(entity):
            EntityIntegrationOperations.preserve_with_user_data(
                entity = entity,
                integration_name = integration_name,
                result = result,
            )
        else:
            # No user data, safe to delete completely; deletion
            # cascades to all related data.
            entity.delete()
