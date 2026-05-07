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
from typing import Any, Dict, List, Optional

from django.db import transaction

from hi.apps.common.database_lock import ExclusionLockContext
from hi.apps.entity.entity_placement import (
    EntityPlacementInput,
    EntityPlacementItem,
)
from hi.apps.entity.models import Entity

from .entity_operations import EntityIntegrationOperations
from .sync_check import IntegrationSyncCheck, SyncDelta
from .sync_result import IntegrationSyncResult
from .transient_models import IntegrationKey, IntegrationMetaData

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

    def sync(self,
             is_initial_import   : bool,
             preserve_user_data  : bool = True,
             ) -> IntegrationSyncResult:
        """
        Public entry point used by the framework. Wraps `_sync_impl`
        with the sync lock and standard error handling. Subclasses
        override `_sync_impl` rather than this method.

        ``is_initial_import`` is the operator-intent flag from the
        sync flow (Import for first-time, Refresh otherwise);
        threaded down so each subclass can title its result
        consistently.

        ``preserve_user_data`` controls how user-data entities are
        handled when the sync drops them as no-longer-present
        upstream — symmetric to the integration-disable flow's SAFE
        / ALL choice. True (default, "Refresh and Retain") detaches
        them; False ("Refresh and Remove") hard-deletes them. Stored
        on the instance for the duration so
        ``_remove_entity_intelligently`` can read it without
        threading the flag through every subclass's ``_sync_impl``;
        the process-wide ``SYNCHRONIZATION_LOCK_NAME`` precludes
        concurrent syncs.
        """
        self._preserve_user_data = preserve_user_data
        try:
            with ExclusionLockContext(name=self.SYNCHRONIZATION_LOCK_NAME):
                logger.debug(f'{self.__class__.__name__} sync started.')
                result = self._sync_impl(is_initial_import=is_initial_import)
        except RuntimeError as e:
            logger.exception(e)
            result = IntegrationSyncResult(
                title=self.get_result_title(is_initial_import=is_initial_import),
                error_list=[str(e)],
            )
        finally:
            logger.debug(f'{self.__class__.__name__} sync ended.')

        self._record_sync_check_complete_if_successful( result = result )
        return result

    def _record_sync_check_complete_if_successful(
            self, result : IntegrationSyncResult ) -> None:
        """Issue #283: a successful sync brings HI in line with upstream
        as of right now. Write a zero-delta sync-check result with the
        current timestamp so UI surfaces clear immediately and the next
        background probe has a fresh baseline. Cache write failures must
        not propagate — the sync itself succeeded and the caller's
        flow should continue regardless."""
        if result.error_list:
            return
        try:
            metadata = self.get_integration_metadata()
        except NotImplementedError:
            return
        try:
            IntegrationSyncCheck.record_sync_complete(
                integration_id = metadata.integration_id,
                integration_label = metadata.label,
            )
        except Exception as e:
            logger.warning(
                f'Failed to record sync-check completion for '
                f'{metadata.integration_id}: {e}'
            )
        return

    def _sync_impl(self, is_initial_import: bool) -> IntegrationSyncResult:
        """
        Integration-specific sync work. Subclasses must override.
        Called with the synchronization lock held.
        """
        raise NotImplementedError('Subclasses must override this method')

    async def check_needs_sync(self) -> Optional[SyncDelta]:
        """Issue #283 — periodic sync-check probe. Return a
        ``SyncDelta`` describing how upstream has drifted from HI's
        current state, or ``None`` to opt out.

        The framework monitor in ``hi.integrations.monitors`` invokes
        this on each enabled+unpaused integration's synchronizer once
        per cycle (default 4 hours). Implementations should do a
        *cheap* upstream fetch — the probe is purely informational and
        runs even when no user action is in progress — and delegate
        the comparison to ``IntegrationSyncCheck.compute_delta``. The
        framework wraps the returned delta into a
        ``SyncCheckResult`` (with timestamp and summary) and caches
        it; subclasses do not touch the cache directly.

        Failures (client unavailable, upstream unreachable) should
        propagate; the framework monitor's per-call try/except
        classifies the cycle as ERROR for that integration and
        continues with the others.

        Default returns ``None`` — opt-out. Sync-check is opt-in even
        among integrations that support full sync.
        """
        return None

    def get_integration_metadata(self) -> IntegrationMetaData:
        """
        Subclasses return their integration's ``IntegrationMetaData``
        constant (the same object the gateway exposes via
        ``get_metadata()``). The framework reads ``.integration_id``
        and ``.label`` from it for shared operations like the
        auto-reconnect pre-pass and the entity-removal helper, so
        each subclass declares the source of truth in one place
        instead of repeating the values at every call site.
        """
        raise NotImplementedError(
            f'{self.__class__.__name__} must override get_integration_metadata()'
        )

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

    def reconnect_disconnected_items(
            self,
            integration_key_to_upstream : Dict[ IntegrationKey, Any ],
            integration_key_to_entity   : Dict[ IntegrationKey, Entity ],
            result                      : IntegrationSyncResult ):
        """
        Framework-level auto-reconnect (Issue #281). Symmetric to
        the framework-level disconnect path
        (``EntityIntegrationOperations.preserve_with_user_data``):
        both directions of the cycle live in shared code, with each
        integration contributing only the minimal piece that's
        genuinely integration-specific — the converter dispatch via
        ``_rebuild_integration_components()``.

        For each unmatched upstream key with a unique secondary
        match, this method:

          * clears the previous-identity columns (which removes the
            "Detached from <integration>" badge in the UI),
          * dispatches to ``_rebuild_integration_components()`` so the
            integration's converter repopulates the integration-owned
            components on the existing entity,
          * appends the entity name to ``result.reconnected_list``
            (which drives the "Reconnected" tile + per-category list
            in the sync result modal) and to ``result.info_list``
            (the diagnostic Details section),
          * inserts the reconnected entity into
            ``integration_key_to_entity`` so the synchronizer's main
            loop sees it as primary-matched and gives it the standard
            update / attribute-sync treatment without any
            reconnect-specific branching.

        The entity's ``name`` is deliberately not touched: the user
        may have edited it before or after the intervening detach,
        and the detached/connected distinction is signaled
        structurally via the integration_id / previous_integration_id
        columns rather than by a name-string convention.

        Ambiguous secondary matches are handled inside
        ``find_reconnect_candidates``: dropped silently, with a
        WARNING log + ``info_list`` breadcrumb so the operator can
        find them and resolve via merge (#263).
        """
        unmatched_upstream_keys = [
            integration_key for integration_key in integration_key_to_upstream
            if integration_key not in integration_key_to_entity
        ]
        if not unmatched_upstream_keys:
            return

        metadata = self.get_integration_metadata()
        candidates = EntityIntegrationOperations.find_reconnect_candidates(
            integration_id = metadata.integration_id,
            upstream_keys = unmatched_upstream_keys,
            result = result,
        )
        if not candidates:
            return

        for upstream_key, entity in candidates.items():
            # Wrap each reconnect in its own atomic boundary so a
            # mid-batch converter failure rolls back that single
            # entity's changes (including the cleared previous
            # identity) without aborting reconnects already
            # committed for prior entities. The result-list appends
            # are inside the boundary so they stay consistent with
            # the persisted state.
            with transaction.atomic():
                entity.previous_integration_key = None
                self._rebuild_integration_components(
                    entity = entity,
                    upstream = integration_key_to_upstream[ upstream_key ],
                    result = result,
                )
                # The disconnect path set is_disabled=True (the
                # capability gate that hides detached entities from
                # listings like the Cameras sidebar). Reconnect is
                # the symmetric clear: the entity is integration-
                # attached again and should participate in those
                # listings. Capability flags like has_video_stream
                # are converter-owned and should already have been
                # re-established by _rebuild_integration_components.
                entity.is_disabled = False
                # Defensive save: subclasses' converters typically
                # save the entity themselves, but the framework
                # explicitly persists the cleared previous-identity
                # and is_disabled fields so a future converter that
                # only writes related rows cannot leave the entity
                # in a half-reconnected state.
                entity.save(
                    update_fields = [
                        'previous_integration_id',
                        'previous_integration_name',
                        'is_disabled',
                    ],
                )
                # reconnected_list drives the operator-visible
                # "Reconnected" tile + per-category list in the
                # sync result modal; info_list keeps the same name
                # in the diagnostic Details section so the operator
                # sees a consistent record across both surfaces.
                result.reconnected_list.append( entity.name )
                result.info_list.append(
                    f'Auto-reconnected {metadata.label} item "{entity.name}"'
                )
                integration_key_to_entity[ upstream_key ] = entity
        return

    def _rebuild_integration_components( self,
                                         entity   : Entity,
                                         upstream : Any,
                                         result   : IntegrationSyncResult ):
        """
        Subclass hook for the auto-reconnect (Issue #281) path. Given
        an existing Entity (the previously-disconnected one) and the
        upstream payload for it, repopulate the entity's
        integration-owned components by dispatching to the
        integration's converter with the existing-entity parameter set.

        The base class raises NotImplementedError; subclasses must
        override to participate in auto-reconnect. (Reconnect is
        framework-driven; the only piece each integration owns is
        this thin converter-dispatch override.)
        """
        raise NotImplementedError(
            f'{self.__class__.__name__} must override '
            f'_rebuild_integration_components() to participate in '
            f'auto-reconnect.'
        )

    def _remove_entity_intelligently(self,
                                     entity: Entity,
                                     result: IntegrationSyncResult):
        """
        Remove an entity that no longer exists in the integration.

        Delegates to ``EntityIntegrationOperations.remove_entities_with_closure``
        — the same path the integration-disable flow uses. The
        closure walk picks up delegate entities (e.g., the Area
        auto-created when a camera was placed in a view) when their
        only remaining principal is being removed. Whether
        operator-added attributes trigger the detach-and-preserve
        branch is controlled by ``self._preserve_user_data`` (set on
        ``sync()`` entry from the operator's pre-sync choice;
        defaults to True / preserve when not explicitly set).
        """
        EntityIntegrationOperations.remove_entities_with_closure(
            seed_entity_ids = { entity.id },
            integration_name = self.get_integration_metadata().label,
            preserve_user_data = getattr( self, '_preserve_user_data', True ),
            result = result,
        )
