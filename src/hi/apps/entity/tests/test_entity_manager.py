import logging

from hi.apps.entity.entity_manager import EntityManager
from hi.apps.entity.models import Entity
from hi.apps.entity.enums import EntityGroupType, EntityType
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

    def test_get_entity_edit_mode_data_returns_complete_data_structure(self):
        """Test get_entity_edit_mode_data business logic - complex method integrating multiple systems."""
        manager = EntityManager()
        
        # Create test entity
        entity = Entity.objects.create(
            name='Test Camera',
            entity_type_str=str(EntityType.CAMERA),
            integration_id='test_camera_001',
            integration_name='test_integration',
        )
        
        # Test with no location_view (basic case)
        edit_mode_data = manager.get_entity_edit_mode_data(
            entity=entity,
            location_view=None,
            is_editing=False
        )
        
        # Verify complete data structure is returned
        self.assertIsNotNone(edit_mode_data)
        self.assertEqual(edit_mode_data.entity, entity)
        self.assertIsNotNone(edit_mode_data.entity_form)
        self.assertIsNotNone(edit_mode_data.entity_pairing_list)
        
        # Without location_view, position form should be None
        self.assertIsNone(edit_mode_data.entity_position_form)
        
        # Test non-editing mode doesn't create position form
        edit_mode_data_non_edit = manager.get_entity_edit_mode_data(
            entity=entity,
            location_view=None,
            is_editing=True  # Even with editing=True, no location_view means no form
        )
        self.assertIsNone(edit_mode_data_non_edit.entity_position_form)
        return

    def test_create_entity_view_group_list_business_logic(self):
        """Test entity view group creation - complex business logic for UI organization."""
        manager = EntityManager()
        
        # Create test entities of different types
        light_entity = Entity.objects.create(
            name='Living Room Light',
            entity_type_str=str(EntityType.LIGHT),
            integration_id='light_001',
            integration_name='test_integration',
        )
        
        camera_entity = Entity.objects.create(
            name='Front Door Camera',
            entity_type_str=str(EntityType.CAMERA),
            integration_id='camera_001',
            integration_name='test_integration',
        )
        
        thermostat_entity = Entity.objects.create(
            name='Main Thermostat',
            entity_type_str=str(EntityType.THERMOSTAT),
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


