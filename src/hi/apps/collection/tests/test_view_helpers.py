"""
Tests for collection view helpers.
"""

from django.test import TestCase

from hi.apps.entity.models import Entity, EntityState
from hi.apps.entity.enums import EntityType, EntityStateType
from hi.apps.collection.view_helpers import CollectionViewHelpers
from hi.apps.collection.enums import CollectionDisplayCategory


class TestCollectionViewHelpers(TestCase):
    """Test CollectionViewHelpers functionality."""

    def test_get_entity_display_category_video_priority(self):
        """Test entity display category - video has highest priority."""
        # Create entity with video stream
        entity = Entity.objects.create(
            name='Security Camera',
            entity_type_str=str(EntityType.CAMERA),
            integration_id='camera_001',
            integration_name='test_integration',
            has_video_stream=True,
        )

        # Should be HAS_VIDEO regardless of other properties
        category = CollectionViewHelpers.get_entity_display_category(entity)
        self.assertEqual(category, CollectionDisplayCategory.HAS_VIDEO)

    def test_get_entity_display_category_state_priority(self):
        """Test entity display category - state has second priority."""
        # Create entity without video
        entity = Entity.objects.create(
            name='Smart Switch',
            entity_type_str=str(EntityType.LIGHT),
            integration_id='switch_001',
            integration_name='test_integration',
            has_video_stream=False,
        )

        # Should be PLAIN initially (no states)
        category = CollectionViewHelpers.get_entity_display_category(entity)
        self.assertEqual(category, CollectionDisplayCategory.PLAIN)

        # Add an EntityState
        EntityState.objects.create(
            entity=entity,
            entity_state_type_str=str(EntityStateType.ON_OFF),
            name='power_state',
        )

        # Should now be HAS_STATE
        category = CollectionViewHelpers.get_entity_display_category(entity)
        self.assertEqual(category, CollectionDisplayCategory.HAS_STATE)

    def test_get_entity_display_category_video_overrides_state(self):
        """Test entity display category - video priority over state."""
        # Create entity with both video and states
        entity = Entity.objects.create(
            name='Smart Camera with PTZ',
            entity_type_str=str(EntityType.CAMERA),
            integration_id='ptz_camera_001',
            integration_name='test_integration',
            has_video_stream=True,
        )

        # Add EntityState (pan/tilt controls)
        EntityState.objects.create(
            entity=entity,
            entity_state_type_str=str(EntityStateType.MOVEMENT),
            name='pan_tilt_state',
        )

        # Should be HAS_VIDEO (video takes priority over state)
        category = CollectionViewHelpers.get_entity_display_category(entity)
        self.assertEqual(category, CollectionDisplayCategory.HAS_VIDEO)

    def test_get_entity_display_category_plain_fallback(self):
        """Test entity display category - plain fallback for no video or state."""
        # Create entity without video or states
        entity = Entity.objects.create(
            name='Information Display',
            entity_type_str=str(EntityType.OTHER),
            integration_id='info_001',
            integration_name='test_integration',
            has_video_stream=False,
        )

        # Should be PLAIN (no video, no states)
        category = CollectionViewHelpers.get_entity_display_category(entity)
        self.assertEqual(category, CollectionDisplayCategory.PLAIN)

    def test_get_entity_display_category_multiple_states(self):
        """Test entity display category with multiple EntityState instances."""
        # Create entity
        entity = Entity.objects.create(
            name='Dimmer Switch',
            entity_type_str=str(EntityType.LIGHT),
            integration_id='dimmer_001',
            integration_name='test_integration',
            has_video_stream=False,
        )

        # Add multiple EntityState instances
        EntityState.objects.create(
            entity=entity,
            entity_state_type_str=str(EntityStateType.ON_OFF),
            name='power_state',
        )

        EntityState.objects.create(
            entity=entity,
            entity_state_type_str=str(EntityStateType.LIGHT_DIMMER),
            name='brightness_level',
        )

        # Should be HAS_STATE with multiple states
        category = CollectionViewHelpers.get_entity_display_category(entity)
        self.assertEqual(category, CollectionDisplayCategory.HAS_STATE)

    def test_get_entity_display_category_performance_with_database_queries(self):
        """Test entity display category - efficient database queries."""
        from django.db import connection

        # Create entity with states
        entity = Entity.objects.create(
            name='Performance Test Entity',
            entity_type_str=str(EntityType.OTHER),
            integration_id='perf_001',
            integration_name='test_integration',
            has_video_stream=False,
        )

        # Add states
        for i in range(3):
            EntityState.objects.create(
                entity=entity,
                entity_state_type_str=str(EntityStateType.TEMPERATURE),
                name=f'sensor_reading_{i}',
            )

        # Clear query log
        connection.queries_log.clear()

        # Call get_entity_display_category
        category = CollectionViewHelpers.get_entity_display_category(entity)

        # Should be efficient - minimal queries due to exists() usage
        self.assertEqual(category, CollectionDisplayCategory.HAS_STATE)

        # Database query should be minimal (exists() is optimized)
        query_count = len(connection.queries)
        self.assertLessEqual(query_count, 2, "Display category should use efficient queries")

    def test_get_grid_class_for_entity_count(self):
        """Test CSS Grid class calculation based on entity count."""
        # Test 1 entity
        grid_class = CollectionViewHelpers.get_grid_class_for_entity_count(1)
        self.assertEqual(grid_class, 'grid-1-item')

        # Test 2 entities
        grid_class = CollectionViewHelpers.get_grid_class_for_entity_count(2)
        self.assertEqual(grid_class, 'grid-2-items')

        # Test 3+ entities
        grid_class = CollectionViewHelpers.get_grid_class_for_entity_count(3)
        self.assertEqual(grid_class, 'grid-3-plus-items')

        grid_class = CollectionViewHelpers.get_grid_class_for_entity_count(10)
        self.assertEqual(grid_class, 'grid-3-plus-items')

    def test_css_class_method(self):
        """Test CollectionDisplayCategory.css_class() method."""
        self.assertEqual(CollectionDisplayCategory.PLAIN.css_class(), 'plain')
        self.assertEqual(CollectionDisplayCategory.HAS_STATE.css_class(), 'has-state')
        self.assertEqual(CollectionDisplayCategory.HAS_VIDEO.css_class(), 'has-video')

    def test_enhance_entity_status_data_list(self):
        """Test enhance_entity_status_data_list preserves original data and adds categories."""
        # Create entities with different characteristics
        plain_entity = Entity.objects.create(
            name='Info Display',
            entity_type_str=str(EntityType.OTHER),
            integration_id='info_001',
            integration_name='test_integration',
            has_video_stream=False,
        )

        video_entity = Entity.objects.create(
            name='Security Camera',
            entity_type_str=str(EntityType.CAMERA),
            integration_id='camera_001',
            integration_name='test_integration',
            has_video_stream=True,
        )

        state_entity = Entity.objects.create(
            name='Smart Switch',
            entity_type_str=str(EntityType.LIGHT),
            integration_id='switch_001',
            integration_name='test_integration',
            has_video_stream=False,
        )

        EntityState.objects.create(
            entity=state_entity,
            entity_state_type_str=str(EntityStateType.ON_OFF),
            name='power_state',
        )

        # Create mock entity status data list
        from hi.apps.monitor.transient_models import EntityStatusData
        entity_status_data_list = [
            EntityStatusData(entity=plain_entity, entity_state_status_data_list=[], entity_for_video=plain_entity, display_only_svg_icon_item=None),
            EntityStatusData(entity=video_entity, entity_state_status_data_list=[], entity_for_video=video_entity, display_only_svg_icon_item=None),
            EntityStatusData(entity=state_entity, entity_state_status_data_list=[], entity_for_video=state_entity, display_only_svg_icon_item=None),
        ]

        # Enhance the data
        enhanced_list = CollectionViewHelpers.enhance_entity_status_data_list(entity_status_data_list)

        # Verify correct number of items
        self.assertEqual(len(enhanced_list), 3)

        # Verify categories are correct
        categories = [item['entity_display_category'] for item in enhanced_list]
        expected_categories = ['plain', 'has-video', 'has-state']
        self.assertEqual(categories, expected_categories)

        # Verify original data is preserved
        for i, enhanced_item in enumerate(enhanced_list):
            original_context = entity_status_data_list[i].to_template_context()

            # All original keys should be present
            for key in original_context.keys():
                self.assertIn(key, enhanced_item)
                self.assertEqual(enhanced_item[key], original_context[key])

    def test_build_collection_template_context_integration(self):
        """Test build_collection_template_context with real collection and entities."""
        from hi.apps.collection.models import Collection, CollectionEntity

        # Create real collection using real database operations
        collection = Collection.objects.create(
            name='Test Collection',
            collection_type_str='OTHER',
            collection_view_type_str='GRID'
        )

        # Create real entities with different characteristics
        plain_entity = Entity.objects.create(
            name='Plain Entity',
            entity_type_str=str(EntityType.OTHER),
            integration_id='plain_001',
            integration_name='test_integration',
            has_video_stream=False
        )

        video_entity = Entity.objects.create(
            name='Video Entity',
            entity_type_str=str(EntityType.CAMERA),
            integration_id='video_001',
            integration_name='test_integration',
            has_video_stream=True
        )

        state_entity = Entity.objects.create(
            name='State Entity',
            entity_type_str=str(EntityType.LIGHT),
            integration_id='state_001',
            integration_name='test_integration',
            has_video_stream=False
        )

        # Add state to state_entity using real database operations
        EntityState.objects.create(
            entity=state_entity,
            entity_state_type_str=str(EntityStateType.ON_OFF),
            name='power_state',
        )

        # Add entities to collection using real CollectionEntity relationships
        CollectionEntity.objects.create(collection=collection, entity=plain_entity, order_id=1)
        CollectionEntity.objects.create(collection=collection, entity=video_entity, order_id=2)
        CollectionEntity.objects.create(collection=collection, entity=state_entity, order_id=3)

        # Test the method with real data - NO MOCKING of internal dependencies
        context = CollectionViewHelpers.build_collection_template_context(
            collection=collection,
            is_editing=False
        )

        # Verify original collection data is preserved
        self.assertIn('collection', context)
        self.assertIn('entity_status_data_list', context)
        self.assertEqual(context['collection'], collection)
        self.assertEqual(len(context['entity_status_data_list']), 3)

        # Verify enhanced data is added
        self.assertIn('enhanced_entity_status_data_list', context)
        self.assertIn('grid_class', context)
        self.assertIn('entity_count', context)

        # Verify grid class calculation
        self.assertEqual(context['grid_class'], 'grid-3-plus-items')  # 3 entities
        self.assertEqual(context['entity_count'], 3)

        # Verify enhanced entity data
        enhanced_list = context['enhanced_entity_status_data_list']
        self.assertEqual(len(enhanced_list), 3)

        # Verify display categories are correctly calculated through real integration
        categories = [item['entity_display_category'] for item in enhanced_list]
        expected_categories = ['plain', 'has-video', 'has-state']
        self.assertEqual(categories, expected_categories)

        # Verify all original data is preserved in enhanced format
        for enhanced_item in enhanced_list:
            self.assertIn('entity', enhanced_item)
            self.assertIn('entity_state_status_data_list', enhanced_item)
            self.assertIn('entity_display_category', enhanced_item)
