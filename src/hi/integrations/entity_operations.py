"""
Operations on entities with respect to their integration attachment.

This module holds mutating operations (disconnect, preserve, detach) that
act on Entity instances relative to the integration that owns them. These
are distinct from the read-only analytical methods on EntityUserDataDetector.

EventDefinition cleanup (Issue #288) is integration-scoped and is
invoked here from both ``preserve_with_user_data`` and the hard-delete
branch of ``remove_entities_with_closure``. See
``EventDefinitionOperations`` for the policy: only EventDefinition rows
whose own ``integration_id`` matches are removed; user-owned
EventDefinitions referencing the entity's states are intentionally
left alone (deferred to the broader EventDefinition UX redesign).
"""

import logging
from typing import Dict, Iterable, List, Optional, Set

from django.db import transaction

from hi.apps.attribute.enums import AttributeType
from hi.apps.entity.models import Entity, EntityState, EntityStateDelegation
from hi.apps.sense.models import Sensor
from hi.apps.control.models import Controller

from .event_definition_operations import EventDefinitionOperations
from .sync_result import IntegrationSyncResult
from .transient_models import IntegrationKey, IntegrationRemovalSummary
from .user_data_detector import EntityUserDataDetector

logger = logging.getLogger(__name__)


class EntityIntegrationOperations:
    """
    Operations on an Entity relative to its integration attachment.

    Shared between sync-time preservation (when upstream drops an entity
    that has user-created data) and integration removal (the SAFE mode of
    IntegrationManager.disable_integration).
    """

    @staticmethod
    def collect_removal_closure( initial_entity_ids : Iterable[int] ) -> Set[int]:
        """
        Expand a set of entity IDs to include delegate entities that would
        be orphaned by the removal.

        Pure graph operation over EntityStateDelegation:

          - From each entity already in the closure, find delegates reached
            via that entity's EntityStates' delegations.
          - A delegate is added only when *every* entity that delegates to
            it is already in the closure (otherwise the delegate is still
            serving a non-removed entity and must remain).
          - Iterates until no new entities are added (handles chained and
            diamond-shaped delegations; cycles are bounded by the visited set).

        This function is integration-agnostic — callers pass whatever seed
        set defines the explicit removal scope.
        """
        closure : Set[int] = set(initial_entity_ids)
        if not closure:
            return closure

        while True:
            # Candidate delegates: any delegate_entity reached from an
            # entity-state owned by an entity already in the closure, that
            # isn't already in the closure itself.
            candidate_ids = set(
                EntityStateDelegation.objects.filter(
                    entity_state__entity_id__in = closure,
                ).exclude(
                    delegate_entity_id__in = closure,
                ).values_list( 'delegate_entity_id', flat = True )
            )
            if not candidate_ids:
                break

            # Single bulk query for every candidate's full principal
            # set, then group in Python — replaces a per-candidate
            # query that was O(passes × candidates) on the DB.
            principals_by_candidate : Dict[int, Set[int]] = {}
            for delegate_id, principal_id in EntityStateDelegation.objects.filter(
                    delegate_entity_id__in = candidate_ids,
            ).values_list( 'delegate_entity_id', 'entity_state__entity_id' ):
                principals_by_candidate.setdefault( delegate_id, set() ).add( principal_id )

            added_this_pass = {
                candidate_id
                for candidate_id, principal_ids in principals_by_candidate.items()
                if principal_ids and principal_ids.issubset( closure )
            }

            if not added_this_pass:
                break
            closure |= added_this_pass

        return closure

    @staticmethod
    def get_removal_entity_ids( integration_id : str ) -> Set[int]:
        """
        Return the full set of entity IDs that a Remove of the given
        integration should target: every entity attached to the integration,
        plus any delegate entities that would be orphaned by their removal.
        """
        seed = set(
            Entity.objects.filter( integration_id = integration_id )
                          .values_list( 'id', flat = True )
        )
        return EntityIntegrationOperations.collect_removal_closure( seed )

    @classmethod
    def remove_entities_with_closure(
            cls,
            seed_entity_ids    : Iterable[int],
            integration_name   : str,
            preserve_user_data : bool                              = True,
            result             : Optional[IntegrationSyncResult]   = None ):
        """Canonical removal for integration-owned entities.

        Walks ``collect_removal_closure(seed_entity_ids)`` so every
        delegate entity that would be orphaned by the removal (e.g.,
        the Area auto-created when a camera was placed in a view) is
        included. Each entity in the closure is then handled the
        same way:

          * ``preserve_user_data=True`` (the SAFE pattern, used by
            DELETE SAFE on disable and by sync-time refresh
            removals): entities carrying operator-added attributes
            are detached from the integration (active integration
            identity cleared, previous identity recorded for the
            auto-reconnect path); others are hard-deleted.

          * ``preserve_user_data=False`` (the DELETE ALL pattern):
            every entity in the closure is hard-deleted, including
            those with user-added data.

        ``result`` is optional. When provided, each closure entity's
        name is appended to either ``result.removed_list`` (the
        hard-delete branch) or ``result.detached_list`` (the
        preserve branch) — never both. The preserve branch also
        adds its diagnostic note to ``result.info_list``.

        Each entity in the closure is classified by its *own* user
        data, independent of the seed's classification. This
        produces the right outcome in the camera-preserved /
        Area-no-user-data corner: an auto-created Area's display
        purpose depends on the principal's live state, which the
        preserve path removes — so deleting the now-purposeless
        Area is correct even when its principal is being kept.
        """
        closure_ids = cls.collect_removal_closure( seed_entity_ids )
        for entity in Entity.objects.filter( id__in = closure_ids ):
            if preserve_user_data and EntityUserDataDetector.has_user_created_attributes( entity ):
                # preserve_with_user_data appends to result.detached_list
                # itself; nothing to record here on this branch.
                cls.preserve_with_user_data(
                    entity = entity,
                    integration_name = integration_name,
                    result = result,
                )
            else:
                if result is not None:
                    result.removed_list.append( entity.name )
                # Django's DB-level CASCADE from Entity.delete() reaches
                # EventClause / ControlAction (the children) but stops
                # there — the parent EventDefinition row is never
                # touched. Delete integration-owned EventDefinitions
                # for this entity first, then let CASCADE handle the
                # rest of the entity graph.
                EventDefinitionOperations.delete_for_entity( entity )
                entity.delete()
        return

    @staticmethod
    def summarize_for_removal( integration_id : str ) -> IntegrationRemovalSummary:
        """
        Classify the entities attached to the integration for the
        confirmation dialogs that gate a Disable or a Refresh: counts
        total entities (plus orphan-after-removal delegates) and how
        many carry user-created data.

        Both the Disable modal and the pre-Refresh modal use the same
        classification: each is asking the operator a *policy*
        question ("if items with custom data are about to be let go,
        retain them or delete them?") and surfaces the SAFE / ALL
        choice only when ``has_mixed_state``. Refresh's actual dropped
        set is decided at sync execution against fresh upstream — the
        operator's choice expresses the policy that applies if drops
        include user-data items, regardless of which specific items
        end up dropping.
        """
        target_ids = EntityIntegrationOperations.get_removal_entity_ids(
            integration_id = integration_id,
        )
        total_count = 0
        user_data_count = 0
        for entity in Entity.objects.filter( id__in = target_ids ):
            total_count += 1
            if EntityUserDataDetector.has_user_created_attributes( entity ):
                user_data_count += 1
        return IntegrationRemovalSummary(
            total_count = total_count,
            user_data_count = user_data_count,
        )

    @classmethod
    def find_reconnect_candidates(
            cls,
            integration_id : str,
            upstream_keys  : Iterable[ IntegrationKey ],
            result         : Optional[ IntegrationSyncResult ] = None,
    ) -> Dict[ IntegrationKey, Entity ]:
        """
        Auto-reconnect candidate lookup (Issue #281). Pure read.

        Given a set of upstream IntegrationKeys that the
        synchronizer's primary-match step did NOT match, return a
        map of ``upstream_key → matching disconnected entity`` for
        every key that uniquely aligns with a disconnected entity's
        ``previous_integration_id`` / ``previous_integration_name``.

        Ambiguous matches (multiple disconnected entities sharing
        the same previous identity) are dropped from the result map.
        The issue's contract is to leave the duplicate for the user
        to resolve via merge (#263), since the system has no basis
        to pick one side over the other. A WARNING is logged and a
        breadcrumb is appended to ``result.info_list`` (when
        provided) for each ambiguous case so the operator can find
        them.

        The per-entity reconnect mutations and converter dispatch
        are deliberately NOT performed here. Callers (the
        per-integration synchronizers) own that step because each
        integration's converter has a different signature and
        callers also want to enrich ``result`` with their own
        operator-facing messages. ``strip_disconnected_prefix`` is
        provided as a shared helper for the name-cleanup step.

        The lookup is a single batched DB query keyed on
        ``(previous_integration_id, previous_integration_name__in=...)``
        — O(1) DB round trips regardless of how many upstream keys
        the caller passes.
        """
        upstream_keys = list( upstream_keys )
        if not upstream_keys:
            return {}

        upstream_keys_by_name : Dict[ str, IntegrationKey ] = {
            key.integration_name: key for key in upstream_keys
        }

        candidate_entities = Entity.objects.filter(
            previous_integration_id = integration_id,
            previous_integration_name__in = list( upstream_keys_by_name.keys() ),
        )

        candidates_by_name : Dict[ str, List[ Entity ] ] = {}
        for entity in candidate_entities:
            candidates_by_name.setdefault(
                entity.previous_integration_name, [],
            ).append( entity )

        reconnect_map : Dict[ IntegrationKey, Entity ] = {}
        for previous_name, entities in candidates_by_name.items():
            upstream_key = upstream_keys_by_name.get( previous_name )
            # Defensive: the IN-filter guarantees previous_name is in
            # the dict, but a corrupted row could slip through.
            if upstream_key is None:
                continue

            if len( entities ) > 1:
                ambiguity_message = (
                    f'Auto-reconnect skipped for {integration_id} item '
                    f'"{previous_name}": {len(entities)} disconnected '
                    f'entities share that previous identity. Resolve via '
                    f'merge.'
                )
                logger.warning( ambiguity_message )
                if result is not None:
                    result.info_list.append( ambiguity_message )
                continue

            reconnect_map[ upstream_key ] = entities[0]

        return reconnect_map

    @staticmethod
    def preserve_with_user_data( entity           : Entity,
                                 integration_name : str,
                                 result           : Optional[IntegrationSyncResult] = None ):
        """
        Preserve an entity with user-created data by disconnecting it
        from its integration and removing only integration-related
        components (sensors, controllers, orphaned states,
        integration-owned attributes, integration-owned
        EventDefinitions). The entity's previous integration identity
        is recorded on the entity so the auto-reconnect path can
        recognize it if the same upstream key reappears later. The
        detached state is signaled structurally — ``integration_id``
        becomes NULL and ``previous_integration_id`` carries the prior
        identity — and surfaced to the operator via a "Detached from
        <integration>" badge in the entity-detail UI.

        Issue #288: integration-owned EventDefinitions are removed
        first inside the atomic block via
        ``EventDefinitionOperations.delete_for_entity``. User-owned
        EventDefinitions (``integration_id IS NULL``) referencing this
        entity's states are intentionally NOT touched here — the
        broader UX of broken/partial user rules is deferred to a
        separate redesign.

        Args:
            entity: The Entity to preserve.
            integration_name: Name of the integration (used in result messages).
            result: Optional IntegrationSyncResult to append a status
                message to.
        """
        original_name = entity.name

        # Get integration-related components to remove
        sensor_ids_to_remove = EntityUserDataDetector.get_integration_related_sensors(entity)
        controller_ids_to_remove = EntityUserDataDetector.get_integration_related_controllers(entity)

        # Get entity states that will become orphaned
        orphaned_state_ids = EntityUserDataDetector.get_orphaned_entity_states(
            entity, sensor_ids_to_remove, controller_ids_to_remove
        )

        with transaction.atomic():
            # Remove integration-owned EventDefinitions for this entity.
            # Done first so the parent rows are gone before the states/
            # controllers they reference are deleted below; CASCADE on
            # EventClause/ControlAction reaches only the children, so
            # parents must be removed explicitly here. See
            # EventDefinitionOperations docstring for the integration-
            # scoped policy.
            EventDefinitionOperations.delete_for_entity( entity )

            # Remove integration-related sensors
            if sensor_ids_to_remove:
                removed_sensor_count = Sensor.objects.filter(
                    id__in=sensor_ids_to_remove
                ).delete()[0]
                logger.debug(f'Removed {removed_sensor_count} integration sensors for {entity}')

            # Remove integration-related controllers
            if controller_ids_to_remove:
                removed_controller_count = Controller.objects.filter(
                    id__in=controller_ids_to_remove
                ).delete()[0]
                logger.debug(f'Removed {removed_controller_count} integration controllers for {entity}')

            # Remove orphaned entity states
            if orphaned_state_ids:
                removed_state_count = EntityState.objects.filter(
                    id__in=orphaned_state_ids
                ).delete()[0]
                logger.debug(f'Removed {removed_state_count} orphaned entity states for {entity}')

            # Remove integration-created attributes (keep user-added ones).
            # Provenance is determined by attribute_type_str: PREDEFINED is
            # system/integration-created, CUSTOM is user-added. Note:
            # queryset .delete() intentionally bypasses the model-level
            # SoftDeleteAttributeModel.delete() override, performing a hard
            # delete. Integration attributes should not accumulate as
            # soft-deleted records.
            removed_attr_count = entity.attributes.exclude(
                attribute_type_str=str(AttributeType.CUSTOM),
            ).delete()[0]
            if removed_attr_count:
                logger.debug(f'Removed {removed_attr_count} integration attributes for {entity}')

            # Disconnect entity from integration. The current integration
            # identity is copied to the previous_integration_* fields
            # so the auto-reconnect path can recognize this entity if
            # the same upstream key reappears later. The presence of
            # previous_integration_id is also what drives the
            # "Detached from <integration>" UI badge.
            entity.previous_integration_key = entity.integration_key
            entity.integration_key = None

            # Restore user-management flags. These are commonly set to False
            # by integration converters to prevent the user from deleting or
            # extending an integration-managed entity. After detach the
            # entity is no longer integration-managed, so user-management
            # rights are restored.
            entity.can_user_delete = True
            entity.can_add_custom_attributes = True

            # Suppress integration-backed capabilities. The intrinsic
            # video-stream capability is genuinely lost (the backing sensor
            # was deleted above). The is_disabled flag is the general
            # capability gate — listing/enumeration sites use it to keep
            # a detached entity out of capability-driven UX (e.g., the
            # sidebar Cameras list).
            entity.has_video_stream = False
            entity.is_disabled = True

            entity.save()

        if result is not None:
            # detached_list drives the operator-visible "Detached"
            # tile + per-category list in the sync result modal;
            # info_list keeps the diagnostic note for the collapsed
            # Details section.
            result.detached_list.append( entity.name )
            result.info_list.append(
                f'Preserved {integration_name} item "{original_name}" with user data; '
                f'detached from integration.'
            )
