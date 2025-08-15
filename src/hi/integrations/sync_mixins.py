"""
Mixins for integration synchronization operations.

This module provides common functionality for integration sync operations,
particularly around intelligent entity deletion that preserves user data.
"""

import logging

from django.db import transaction

from hi.apps.common.processing_result import ProcessingResult
from hi.apps.entity.models import Entity, EntityState
from hi.apps.sense.models import Sensor
from hi.apps.control.models import Controller

from .user_data_detector import EntityUserDataDetector

logger = logging.getLogger(__name__)


class IntegrationSyncMixin:
    """
    Mixin providing common functionality for integration synchronization operations.
    
    This mixin provides intelligent entity deletion that preserves user-created
    data while removing integration-specific components.
    """

    def _remove_entity_intelligently(self, 
                                     entity: Entity, 
                                     result: ProcessingResult,
                                     integration_name: str):
        """
        Remove an entity that no longer exists in the integration.
        
        If the entity has user-created attributes, preserve the entity but disconnect
        it from the integration and remove only integration-related components.
        Otherwise, perform complete deletion.
        
        Args:
            entity: The Entity to remove or preserve
            result: ProcessingResult to update with messages
            integration_name: Name of the integration (for logging)
        """
        if EntityUserDataDetector.has_user_created_attributes(entity):
            self._preserve_entity_with_user_data(entity, result, integration_name)
        else:
            # No user data, safe to delete completely
            entity.delete()  # Deletion cascades to all related data
            result.message_list.append(f'Removed stale {integration_name} entity: {entity}')

    def _preserve_entity_with_user_data(self,
                                        entity: Entity,
                                        result: ProcessingResult,
                                        integration_name: str):
        """
        Preserve an entity with user-created data by disconnecting it from integration
        and removing only integration-related components.
        
        Args:
            entity: The Entity to preserve
            result: ProcessingResult to update with messages
            integration_name: Name of the integration (for logging)
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
            
            # Remove integration-related attributes (keep user-created ones)
            removed_attr_count = entity.attributes.filter(
                integration_key_str__isnull=False
            ).delete()[0]
            if removed_attr_count:
                logger.debug(f'Removed {removed_attr_count} integration attributes for {entity}')
            
            # Disconnect entity from integration
            entity.integration_id = None
            entity.integration_name = None
            
            # Update name to indicate disconnected status
            if not entity.name.startswith('[Disconnected]'):
                entity.name = f'[Disconnected] {entity.name}'
            
            entity.save()
        
        result.message_list.append(
            f'Preserved {integration_name} entity "{original_name}" with user data, '
            f'disconnected from integration and renamed to "{entity.name}"'
        )
