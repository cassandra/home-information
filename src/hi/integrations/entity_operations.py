"""
Operations on entities with respect to their integration attachment.

This module holds mutating operations (disconnect, preserve, detach) that
act on Entity instances relative to the integration that owns them. These
are distinct from the read-only analytical methods on EntityUserDataDetector.
"""

import logging
from typing import Iterable, Optional, Set

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

            added_this_pass : Set[int] = set()
            for candidate_id in candidate_ids:
                principal_ids = set(
                    EntityStateDelegation.objects.filter(
                        delegate_entity_id = candidate_id,
                    ).values_list( 'entity_state__entity_id', flat = True )
                )
                if principal_ids and principal_ids.issubset( closure ):
                    added_this_pass.add( candidate_id )

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
            result.message_list.append(
                f'Preserved {integration_name} entity "{original_name}" with user data, '
                f'disconnected from integration and renamed to "{entity.name}"'
            )
