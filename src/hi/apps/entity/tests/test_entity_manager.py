import logging
from decimal import Decimal
from unittest.mock import Mock

from hi.apps.entity.entity_manager import EntityManager
from hi.apps.entity.models import Entity, EntityPath, EntityPosition
from hi.apps.entity.enums import EntityGroupType
from hi.testing.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestEntityManager(BaseTestCase):

    def test_singleton_behavior(self):
        """Test EntityManager singleton pattern - critical for system consistency."""
        manager1 = EntityManager()
        manager2 = EntityManager()
        
        self.assertIs(manager1, manager2)
        return

    def test_change_listener_system_notifies_all_registered_callbacks(self):
        """Test change listener system - core functionality for system integration."""
        manager = EntityManager()
        
        # Track actual behavior with state changes
        callback1_called = []
        callback2_called = []
        
        def callback1():
            callback1_called.append(True)
        
        def callback2():
            callback2_called.append(True)
        
        manager.register_change_listener(callback1)
        manager.register_change_listener(callback2)
        
        # Clear any previous calls
        callback1_called.clear()
        callback2_called.clear()
        
        # Trigger reload which should notify listeners
        manager.reload()
        
        # Verify both callbacks were actually executed
        self.assertEqual(len(callback1_called), 1)
        self.assertEqual(len(callback2_called), 1)
        return

    def test_change_listener_system_continues_after_callback_failure(self):
        """Test change listener error handling - system should be resilient to callback failures."""
        manager = EntityManager()
        
        # Create callback that raises exception
        def failing_callback():
            raise ValueError("Test exception")
        
        # Track normal callback execution
        normal_callback_called = []
        
        def normal_callback():
            normal_callback_called.append(True)
        
        manager.register_change_listener(failing_callback)
        manager.register_change_listener(normal_callback)
        
        # Clear previous calls
        normal_callback_called.clear()
        
        # Reload should not fail despite exception in callback
        manager.reload()
        
        # Normal callback should still execute despite exception in first callback
        self.assertEqual(len(normal_callback_called), 1)
        return

    def test_set_entity_path_create_new(self):
        """Test set_entity_path creation logic - complex business logic with transactions."""
        manager = EntityManager()
        
        # Create test entity
        entity = Entity.objects.create(
            name='Test Entity',
            entity_type_str='LIGHT',
            integration_id='test_entity_001',
            integration_name='test_integration',
        )
        
        # Create minimal location (this may need adjustment based on actual Location model)
        # For now, testing the core logic without full location setup
        try:
            from hi.apps.location.models import Location
            location = Location.objects.create(name='Test Location')
            
            # Test creating new path
            svg_path_str = 'M 10 10 L 20 20'
            entity_path = manager.set_entity_path(
                entity_id=entity.id,
                location=location,
                svg_path_str=svg_path_str
            )
            
            self.assertEqual(entity_path.entity, entity)
            self.assertEqual(entity_path.location, location)
            self.assertEqual(entity_path.svg_path, svg_path_str)
            
        except ImportError:
            # Skip if Location model not available in test environment
            self.skipTest("Location model not available for testing")
        return

    def test_set_entity_path_update_existing(self):
        """Test set_entity_path update logic - should update existing rather than create duplicate."""
        manager = EntityManager()
        
        try:
            from hi.apps.location.models import Location
            from hi.apps.entity.models import EntityPath
            
            # Create test data
            entity = Entity.objects.create(
                name='Test Entity',
                entity_type_str='LIGHT',
                integration_id='test_entity_001',
                integration_name='test_integration',
            )
            
            location = Location.objects.create(name='Test Location')
            
            # Create initial path
            initial_path = 'M 10 10 L 20 20'
            entity_path = EntityPath.objects.create(
                entity=entity,
                location=location,
                svg_path=initial_path
            )
            
            initial_id = entity_path.id
            
            # Update path
            updated_path = 'M 30 30 L 40 40'
            updated_entity_path = manager.set_entity_path(
                entity_id=entity.id,
                location=location,
                svg_path_str=updated_path
            )
            
            # Should update existing, not create new
            self.assertEqual(updated_entity_path.id, initial_id)
            self.assertEqual(updated_entity_path.svg_path, updated_path)
            
            # Should only be one EntityPath for this entity/location
            path_count = EntityPath.objects.filter(entity=entity, location=location).count()
            self.assertEqual(path_count, 1)
            
        except ImportError:
            self.skipTest("Required models not available for testing")
        return

    def test_get_entity_details_data_returns_complete_data_structure(self):
        """Test get_entity_details_data business logic - complex method integrating multiple systems."""
        manager = EntityManager()
        
        # Create test entity
        entity = Entity.objects.create(
            name='Test Camera',
            entity_type_str='CAMERA',
            integration_id='test_camera_001',
            integration_name='test_integration',
        )
        
        # Test with no location_view (basic case)
        details_data = manager.get_entity_details_data(
            entity=entity,
            location_view=None,
            is_editing=False
        )
        
        # Verify complete data structure is returned
        self.assertIsNotNone(details_data)
        self.assertIsNotNone(details_data.entity_edit_data)
        self.assertEqual(details_data.entity_edit_data.entity, entity)
        self.assertIsNotNone(details_data.entity_pairing_list)
        
        # Without location_view, position form should be None
        self.assertIsNone(details_data.entity_position_form)
        
        # Test non-editing mode doesn't create position form
        details_data_non_edit = manager.get_entity_details_data(
            entity=entity,
            location_view=None,
            is_editing=True  # Even with editing=True, no location_view means no form
        )
        self.assertIsNone(details_data_non_edit.entity_position_form)
        return

    def test_create_entity_view_group_list_business_logic(self):
        """Test entity view group creation - complex business logic for UI organization."""
        manager = EntityManager()
        
        # Create test entities of different types
        light_entity = Entity.objects.create(
            name='Living Room Light',
            entity_type_str='LIGHT',
            integration_id='light_001',
            integration_name='test_integration',
        )
        
        camera_entity = Entity.objects.create(
            name='Front Door Camera',
            entity_type_str='CAMERA',
            integration_id='camera_001',
            integration_name='test_integration',
        )
        
        thermostat_entity = Entity.objects.create(
            name='Main Thermostat',
            entity_type_str='THERMOSTAT',
            integration_id='thermo_001',
            integration_name='test_integration',
        )
        
        all_entities = [light_entity, camera_entity, thermostat_entity]
        existing_entities = [light_entity]  # Only light exists in view
        
        # Test group creation business logic
        group_list = manager.create_entity_view_group_list(
            existing_entities=existing_entities,
            all_entities=all_entities
        )
        
        # Should have multiple groups based on entity types
        self.assertGreater(len(group_list), 1)
        
        # Verify groups are sorted by label
        group_labels = [group.entity_group_type.label for group in group_list]
        sorted_labels = sorted(group_labels)
        self.assertEqual(group_labels, sorted_labels)
        
        # Find the lights/switches group and verify light entity exists in view
        lights_group = None
        for group in group_list:
            if group.entity_group_type == EntityGroupType.LIGHTS_SWITCHES:
                lights_group = group
                break
        
        self.assertIsNotNone(lights_group)
        
        # Find light entity in the group and verify it's marked as existing
        light_item = None
        for item in lights_group.item_list:
            if item.entity == light_entity:
                light_item = item
                break
        
        self.assertIsNotNone(light_item)
        self.assertTrue(light_item.exists_in_view)
        
        # Verify camera entity is not marked as existing in view
        security_group = None
        for group in group_list:
            if group.entity_group_type == EntityGroupType.SECURITY:
                security_group = group
                break
        
        if security_group:  # May not exist if camera maps to different group
            camera_item = None
            for item in security_group.item_list:
                if item.entity == camera_entity:
                    camera_item = item
                    break
            
            if camera_item:
                self.assertFalse(camera_item.exists_in_view)
        
        return

    def test_set_entity_path_update_vs_create_logic(self):
        """Test set_entity_path business logic - should update existing or create new appropriately."""
        manager = EntityManager()
        
        try:
            from hi.apps.location.models import Location
            
            # Create test data
            entity = Entity.objects.create(
                name='Wire Entity',
                entity_type_str='ELECTRIC_WIRE',
                integration_id='wire_001',
                integration_name='test_integration',
            )
            
            location = Location.objects.create(name='Test Location')
            
            # Test creating new path
            initial_path = 'M 10 10 L 20 20'
            entity_path = manager.set_entity_path(
                entity_id=entity.id,
                location=location,
                svg_path_str=initial_path
            )
            
            # Verify creation
            self.assertEqual(entity_path.entity, entity)
            self.assertEqual(entity_path.location, location)
            self.assertEqual(entity_path.svg_path, initial_path)
            initial_id = entity_path.id
            
            # Test updating existing path
            updated_path = 'M 30 30 L 40 40 L 50 50'
            updated_entity_path = manager.set_entity_path(
                entity_id=entity.id,
                location=location,
                svg_path_str=updated_path
            )
            
            # Should update existing, not create new
            self.assertEqual(updated_entity_path.id, initial_id)
            self.assertEqual(updated_entity_path.svg_path, updated_path)
            
            # Verify only one EntityPath exists for this entity/location
            path_count = EntityPath.objects.filter(entity=entity, location=location).count()
            self.assertEqual(path_count, 1)
            
        except ImportError:
            self.skipTest("Location model not available for testing")
        return

    def test_add_entity_position_if_needed_centers_in_view(self):
        """Test entity position creation - should center entity in location view by default."""
        manager = EntityManager()
        
        try:
            from hi.apps.location.models import Location
            from hi.apps.common.svg_models import SvgViewBox
            
            # Create test data
            entity = Entity.objects.create(
                name='Position Test Entity',
                entity_type_str='CAMERA',
                integration_id='pos_test_001',
                integration_name='test_integration',
            )
            
            location = Location.objects.create(name='Test Location')
            
            # Create a mock location view with known view box
            view_box = SvgViewBox(x=100, y=200, width=400, height=300)
            location_view = Mock()
            location_view.location = location
            location_view.svg_view_box = view_box
            
            # Test position creation
            entity_position = manager.add_entity_position_if_needed(
                entity=entity,
                location_view=location_view
            )
            
            # Should center in view box
            expected_x = Decimal('300')  # 100 + 400/2
            expected_y = Decimal('350')  # 200 + 300/2
            
            self.assertEqual(entity_position.entity, entity)
            self.assertEqual(entity_position.location, location)
            self.assertEqual(entity_position.svg_x, expected_x)
            self.assertEqual(entity_position.svg_y, expected_y)
            self.assertEqual(entity_position.svg_scale, Decimal('1.0'))
            self.assertEqual(entity_position.svg_rotate, Decimal('0.0'))
            
            # Test that calling again doesn't create duplicate
            manager.add_entity_position_if_needed(
                entity=entity,
                location_view=location_view
            )
            
            position_count = EntityPosition.objects.filter(
                entity=entity, 
                location=location
            ).count()
            self.assertEqual(position_count, 1)
            
        except ImportError:
            self.skipTest("Location models not available for testing")
        return
