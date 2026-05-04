"""
Operations on entities with respect to their integration attachment.

This module holds mutating operations (disconnect, preserve, detach) that
act on Entity instances relative to the integration that owns them. These
are distinct from the read-only analytical methods on EntityUserDataDetector.
"""

import logging
from typing import Dict, Iterable, Optional, Set

from django.db import transaction

from hi.apps.attribute.enums import AttributeType
from hi.apps.entity.models import Entity, EntityState, EntityStateDelegation
from hi.apps.sense.models import Sensor
from hi.apps.control.models import Controller

from .sync_result import IntegrationSyncResult
from .transient_models import IntegrationRemovalSummary
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
            are preserved via ``[Disconnected]`` rename; others are
            hard-deleted.

          * ``preserve_user_data=False`` (the DELETE ALL pattern):
            every entity in the closure is hard-deleted, including
            those with user-added data.

        ``result`` is optional. When provided, each closure entity's
        name is appended to ``result.removed_list``; the preserve
        path also adds its diagnostic note to ``result.info_list``.

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
            if result is not None:
                result.removed_list.append( entity.name )
            if preserve_user_data and EntityUserDataDetector.has_user_created_attributes( entity ):
                cls.preserve_with_user_data(
                    entity = entity,
                    integration_name = integration_name,
                    result = result,
                )
            else:
                entity.delete()
        return

    @staticmethod
    def summarize_for_removal( integration_id : str ) -> IntegrationRemovalSummary:
        """
        Classify the entities targeted by a Remove of the given integration
        (including orphan-after-removal delegates) for the Remove
        confirmation dialog: counts total entities and those with
        user-created data.
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

    @staticmethod
    def preserve_with_user_data( entity           : Entity,
                                 integration_name : str,
                                 result           : Optional[IntegrationSyncResult] = None ):
        """
        Preserve an entity with user-created data by disconnecting it from
        its integration and removing only integration-related components
        (sensors, controllers, orphaned states, integration-owned
        attributes). Applies the '[Disconnected]' name prefix.

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

            # Disconnect entity from integration
            entity.integration_id = None
            entity.integration_name = None

            # Restore user-management flags. These are commonly set to False
            # by integration converters to prevent the user from deleting or
            # extending an integration-managed entity. After disconnect the
            # entity is no longer integration-managed, so user-management
            # rights are restored.
            entity.can_user_delete = True
            entity.can_add_custom_attributes = True

            # Suppress integration-backed capabilities. The intrinsic
            # video-stream capability is genuinely lost (the backing sensor
            # was deleted above). The is_disabled flag is the general
            # capability gate — listing/enumeration sites use it to keep
            # a disconnected entity out of capability-driven UX (e.g., the
            # sidebar Cameras list).
            entity.has_video_stream = False
            entity.is_disabled = True

            # Update name to indicate disconnected status
            if not entity.name.startswith('[Disconnected]'):
                entity.name = f'[Disconnected] {entity.name}'

            entity.save()

        if result is not None:
            result.info_list.append(
                f'Preserved {integration_name} item "{original_name}" with user data, '
                f'disconnected from integration and renamed to "{entity.name}"'
            )
