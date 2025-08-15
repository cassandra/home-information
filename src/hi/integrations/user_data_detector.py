"""
Utility for detecting user-created data associated with entities.

This module provides functionality to determine whether an entity has
user-created data that should be preserved during integration sync operations.
All methods are purely analytical and perform no database operations.
"""

import logging
from typing import Set

from hi.apps.entity.models import Entity

logger = logging.getLogger(__name__)


class EntityUserDataDetector:
    """
    Detects user-created data associated with entities to determine
    whether an entity should be preserved during integration deletion.
    
    This class provides analysis methods only - no database operations
    are performed. The calling code is responsible for acting on the
    information provided by these methods.
    """

    @staticmethod
    def has_user_created_attributes(entity: Entity) -> bool:
        """
        Check if an entity has user-created attributes that justify preservation.
        
        This is the primary decision criteria for whether to preserve an entity
        during integration sync deletion. Only user-created attributes (those
        without integration_key_str) are considered significant enough to preserve
        the entire entity.
        
        Args:
            entity: The Entity to check for user-created attributes
            
        Returns:
            True if the entity has user-created attributes, False otherwise
        """
        user_attributes = entity.attributes.filter(
            integration_key_str__isnull=True
        ).exists()
        
        if user_attributes:
            logger.debug(f'Entity {entity} has user-created attributes - should be preserved')
            return True
        
        logger.debug(f'Entity {entity} has no user-created attributes - can be deleted')
        return False

    @staticmethod
    def get_integration_related_sensors(entity: Entity) -> Set[int]:
        """
        Get sensor IDs that are integration-related for this entity.
        
        Args:
            entity: The Entity to check
            
        Returns:
            Set of sensor IDs that have integration keys and should be removed
        """
        sensor_ids = set()
        for state in entity.states.all():
            integration_sensors = state.sensors.filter(
                integration_id__isnull=False
            )
            sensor_ids.update(integration_sensors.values_list('id', flat=True))
        return sensor_ids

    @staticmethod
    def get_integration_related_controllers(entity: Entity) -> Set[int]:
        """
        Get controller IDs that are integration-related for this entity.
        
        Args:
            entity: The Entity to check
            
        Returns:
            Set of controller IDs that have integration keys and should be removed
        """
        controller_ids = set()
        for state in entity.states.all():
            integration_controllers = state.controllers.filter(
                integration_id__isnull=False
            )
            controller_ids.update(integration_controllers.values_list('id', flat=True))
        return controller_ids

    @staticmethod
    def get_orphaned_entity_states(entity: Entity, 
                                   removed_sensor_ids: Set[int], 
                                   removed_controller_ids: Set[int]) -> Set[int]:
        """
        Get entity state IDs that would become orphaned after removing integration components.
        
        Args:
            entity: The Entity to check
            removed_sensor_ids: Set of sensor IDs being removed
            removed_controller_ids: Set of controller IDs being removed
            
        Returns:
            Set of entity state IDs that would have no remaining sensors or controllers
            and should be removed
        """
        orphaned_state_ids = set()
        
        for state in entity.states.all():
            # Check if state will have any remaining sensors
            remaining_sensors = state.sensors.exclude(
                id__in=removed_sensor_ids
            ).exists()
            
            # Check if state will have any remaining controllers
            remaining_controllers = state.controllers.exclude(
                id__in=removed_controller_ids
            ).exists()
            
            # If no remaining sensors or controllers, this state can be deleted
            if not remaining_sensors and not remaining_controllers:
                orphaned_state_ids.add(state.id)
                logger.debug(f'EntityState {state} will be orphaned and should be removed')
            else:
                logger.debug(f'EntityState {state} will retain sensors/controllers, should keep')
        
        return orphaned_state_ids
