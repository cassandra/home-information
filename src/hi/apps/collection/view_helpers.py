"""
Collection view helpers for template context building and display logic.

This module contains view-specific logic that supports template rendering
but is not core business logic or domain concepts.
"""

from typing import Dict, Any, List

from hi.apps.entity.models import Entity
from hi.apps.collection.enums import CollectionDisplayCategory
from hi.apps.collection.collection_manager import CollectionManager


class CollectionViewHelpers:
    """
    Helper class for collection view template context building and display logic.

    Contains view-specific logic that supports template rendering but is not
    core business logic or domain concepts.
    """

    @staticmethod
    def get_entity_display_category(entity: Entity) -> CollectionDisplayCategory:
        """
        Determine the display category for an entity in collection views.

        Priority order:
        1. HAS_VIDEO - entity has video stream capability
        2. HAS_STATE - entity has EntityState instances
        3. PLAIN - entity has no states and no video stream

        This is a collection display concern, not a core entity domain concept.

        Args:
            entity: Entity instance to classify

        Returns:
            CollectionDisplayCategory enum value
        """
        if entity.has_video_stream:
            return CollectionDisplayCategory.HAS_VIDEO

        if entity.states.exists():
            return CollectionDisplayCategory.HAS_STATE

        return CollectionDisplayCategory.PLAIN

    @staticmethod
    def get_grid_class_for_entity_count(entity_count: int) -> str:
        """
        Determine CSS Grid class based on number of entities in collection.

        Grid layout rules:
        - 1 entity: Constrained width (1fr 2fr) to prevent over-expansion
        - 2 entities: 2-column grid (1fr 1fr)
        - 3+ entities: 3-column grid maximum (1fr 1fr 1fr)

        Args:
            entity_count: Number of entities in the collection

        Returns:
            CSS class name for grid layout
        """
        if entity_count == 1:
            return 'grid-1-item'
        elif entity_count == 2:
            return 'grid-2-items'
        else:
            return 'grid-3-plus-items'

    @staticmethod
    def enhance_entity_status_data_list(entity_status_data_list) -> List[Dict[str, Any]]:
        """
        Enhance entity status data with display categories for template rendering.

        Takes the original entity_status_data_list from CollectionData and adds
        entity_display_category information for CSS styling and layout decisions.

        Args:
            entity_status_data_list: List of EntityStatusData instances

        Returns:
            List of enhanced dictionaries with original data plus display category
        """
        enhanced_list = []

        for entity_status_data in entity_status_data_list:
            display_category = CollectionViewHelpers.get_entity_display_category(
                entity_status_data.entity
            )

            enhanced_data = {
                **entity_status_data.to_template_context(),
                'entity_display_category': display_category.css_class(),
            }
            enhanced_list.append(enhanced_data)

        return enhanced_list

    @staticmethod
    def build_collection_template_context(collection, is_editing: bool) -> Dict[str, Any]:
        """
        Build complete template context for collection views.

        Handles all the work: gets collection data from manager,
        enhances with display categories and grid classes.

        Args:
            collection: Collection instance
            is_editing: Whether the view is in editing mode

        Returns:
            Complete template context dictionary
        """
        # Get collection data internally
        collection_data = CollectionManager().get_collection_data(
            collection=collection,
            is_editing=is_editing
        )

        # Get original template context
        original_context = collection_data.to_template_context()

        # Calculate grid class based on entity count
        entity_count = len(collection_data.entity_status_data_list)
        grid_class = CollectionViewHelpers.get_grid_class_for_entity_count(entity_count)

        # Enhance entity data with display categories
        enhanced_entity_status_data_list = CollectionViewHelpers.enhance_entity_status_data_list(
            collection_data.entity_status_data_list
        )

        # Build enhanced context
        enhanced_context = {
            **original_context,
            'enhanced_entity_status_data_list': enhanced_entity_status_data_list,
            'grid_class': grid_class,
            'entity_count': entity_count,
        }

        return enhanced_context