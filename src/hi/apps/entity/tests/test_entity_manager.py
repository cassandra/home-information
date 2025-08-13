import logging
from unittest.mock import Mock, patch
from threading import Lock

from hi.apps.entity.entity_manager import EntityManager
from hi.apps.entity.models import Entity
from hi.tests.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestEntityManager(BaseTestCase):

    def test_singleton_behavior(self):
        """Test EntityManager singleton pattern - critical for system consistency."""
        manager1 = EntityManager()
        manager2 = EntityManager()
        
        self.assertIs(manager1, manager2)
        return

    def test_change_listener_registration_and_notification(self):
        """Test change listener system - core functionality for system integration."""
        manager = EntityManager()
        
        # Create mock callbacks
        callback1 = Mock()
        callback2 = Mock()
        
        manager.register_change_listener(callback1)
        manager.register_change_listener(callback2)
        
        # Clear any previous calls
        callback1.reset_mock()
        callback2.reset_mock()
        
        # Trigger reload which should notify listeners
        manager.reload()
        
        callback1.assert_called_once()
        callback2.assert_called_once()
        return

    def test_change_listener_exception_handling(self):
        """Test change listener error handling - system should be resilient to callback failures."""
        manager = EntityManager()
        
        # Create callback that raises exception
        def failing_callback():
            raise ValueError("Test exception")
        
        # Create normal callback
        normal_callback = Mock()
        
        manager.register_change_listener(failing_callback)
        manager.register_change_listener(normal_callback)
        
        # Clear previous calls
        normal_callback.reset_mock()
        
        # Reload should not fail despite exception in callback
        manager.reload()
        
        # Normal callback should still be called
        normal_callback.assert_called_once()
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

    def test_get_entity_details_data_integration(self):
        """Test get_entity_details_data business logic - complex method integrating multiple systems."""
        manager = EntityManager()
        
        try:
            from hi.apps.location.models import Location, LocationView
            
            # Create test data
            entity = Entity.objects.create(
                name='Test Entity',
                entity_type_str='CAMERA',
                integration_id='test_entity_001',
                integration_name='test_integration',
            )
            
            location = Location.objects.create(name='Test Location')
            # LocationView requires additional fields, skip detailed integration test
            # Focus on testing the business logic we can test without complex setup
            location_view = None
            
            # Test with simple case (no location_view)
            details_data = manager.get_entity_details_data(
                entity=entity,
                location_view=location_view,
                is_editing=False
            )
            
            # Should return EntityDetailsData
            self.assertIsNotNone(details_data)
            self.assertIsNotNone(details_data.entity_edit_data)
            self.assertEqual(details_data.entity_edit_data.entity, entity)
            
            # Without location_view, position form should be None
            self.assertIsNone(details_data.entity_position_form)
            
        except ImportError:
            self.skipTest("Required models not available for testing")
        return