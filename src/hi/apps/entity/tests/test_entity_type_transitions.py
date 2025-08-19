"""
Tests for EntityType transition handling functionality.
Focus on actual behavior and database state changes per testing guidelines.
"""
from decimal import Decimal

from django.db import transaction
from django.test import TransactionTestCase

from hi.apps.entity.entity_manager import EntityManager
from hi.apps.entity.enums import EntityType
from hi.apps.entity.models import Entity, EntityPath, EntityPosition
from hi.apps.location.models import Location, LocationView


class TestEntityTypeTransitions(TransactionTestCase):
    """Test EntityType transition handling with preservation strategy"""
    
    def setUp(self):
        super().setUp()
        
        # Reset singleton state for test isolation
        EntityManager._instances = {}
        self.manager = EntityManager()
        
        # Create test data
        self.location = Location.objects.create(
            name = 'Test Location',
            svg_fragment_filename = 'test.svg',
            svg_view_box_str = '0 0 1000 1000',
        )
        self.location_view = LocationView.objects.create(
            location = self.location,
            name = 'Test View',
            location_view_type_str = 'DEFAULT',
            svg_view_box_str = '0 0 1000 1000',
            svg_rotate = Decimal('0'),
            svg_style_name_str = 'COLOR',
        )
        self.entity = Entity.objects.create(
            name = 'Test Entity',
            entity_type_str = str(EntityType.LIGHT),  # Start with icon type
        )
        return
    
    def test_icon_to_path_transition_preserves_position(self):
        """Test that icon->path transition preserves EntityPosition"""
        # Create initial position
        EntityPosition.objects.create(
            entity = self.entity,
            location = self.location,
            svg_x = Decimal('500'),
            svg_y = Decimal('300'),
            svg_scale = Decimal('1.0'),
            svg_rotate = Decimal('0'),
        )
        
        # Change to path type (WALL is a path type)
        self.entity.entity_type_str = str(EntityType.WALL)
        self.entity.save()
        
        # Perform transition
        transition_occurred, transition_type = self.manager.handle_entity_type_transition(
            entity = self.entity,
            location_view = self.location_view,
        )
        
        # Verify transition occurred
        self.assertTrue(transition_occurred)
        self.assertEqual(transition_type, "icon_to_path")
        
        # Verify EntityPosition is preserved
        self.assertTrue(
            EntityPosition.objects.filter(
                entity = self.entity,
                location = self.location,
            ).exists()
        )
        
        # Verify EntityPath was created
        self.assertTrue(
            EntityPath.objects.filter(
                entity = self.entity,
                location = self.location,
            ).exists()
        )
        
        # Both should coexist
        self.assertEqual(EntityPosition.objects.filter(entity=self.entity).count(), 1)
        self.assertEqual(EntityPath.objects.filter(entity=self.entity).count(), 1)
        return
    
    def test_path_to_icon_transition_preserves_path(self):
        """Test that path->icon transition preserves EntityPath"""
        # Start with path type
        self.entity.entity_type_str = str(EntityType.WALL)
        self.entity.save()
        
        # Create initial path
        EntityPath.objects.create(
            entity = self.entity,
            location = self.location,
            svg_path = 'M 100,100 L 200,200 L 300,100 Z',
        )
        
        # Change to icon type
        self.entity.entity_type_str = str(EntityType.LIGHT)
        self.entity.save()
        
        # Perform transition
        transition_occurred, transition_type = self.manager.handle_entity_type_transition(
            entity = self.entity,
            location_view = self.location_view,
        )
        
        # Verify transition occurred
        self.assertTrue(transition_occurred)
        self.assertEqual(transition_type, "path_to_icon")
        
        # Verify EntityPath is preserved
        self.assertTrue(
            EntityPath.objects.filter(
                entity = self.entity,
                location = self.location,
            ).exists()
        )
        
        # Verify EntityPosition was created
        self.assertTrue(
            EntityPosition.objects.filter(
                entity = self.entity,
                location = self.location,
            ).exists()
        )
        
        # Both should coexist
        self.assertEqual(EntityPosition.objects.filter(entity=self.entity).count(), 1)
        self.assertEqual(EntityPath.objects.filter(entity=self.entity).count(), 1)
        return
    
    def test_repeated_transitions_preserve_geometry(self):
        """Test that switching back and forth preserves original geometry"""
        # Create initial position
        original_x = Decimal('123.45')
        original_y = Decimal('678.90')
        EntityPosition.objects.create(
            entity = self.entity,
            location = self.location,
            svg_x = original_x,
            svg_y = original_y,
            svg_scale = Decimal('1.0'),
            svg_rotate = Decimal('0'),
        )
        
        # Transition icon->path
        self.entity.entity_type_str = str(EntityType.WALL)
        self.entity.save()
        self.manager.handle_entity_type_transition(
            entity = self.entity,
            location_view = self.location_view,
        )
        
        # Transition path->icon (back to original)
        self.entity.entity_type_str = str(EntityType.LIGHT)
        self.entity.save()
        transition_occurred, transition_type = self.manager.handle_entity_type_transition(
            entity = self.entity,
            location_view = self.location_view,
        )
        
        # Should be path to icon since both representations now exist 
        self.assertTrue(transition_occurred)
        self.assertEqual(transition_type, "path_to_icon")
        
        # Verify original position is preserved
        entity_position = EntityPosition.objects.get(
            entity = self.entity,
            location = self.location,
        )
        self.assertEqual(entity_position.svg_x, original_x)
        self.assertEqual(entity_position.svg_y, original_y)
        return
    
    def test_both_exist_edge_case(self):
        """Test handling when both EntityPosition and EntityPath already exist"""
        # Create both position and path
        EntityPosition.objects.create(
            entity = self.entity,
            location = self.location,
            svg_x = Decimal('500'),
            svg_y = Decimal('500'),
            svg_scale = Decimal('1.0'),
            svg_rotate = Decimal('0'),
        )
        EntityPath.objects.create(
            entity = self.entity,
            location = self.location,
            svg_path = 'M 0,0 L 100,0',
        )
        
        # Transition to icon type
        transition_occurred, transition_type = self.manager.handle_entity_type_transition(
            entity = self.entity,
            location_view = self.location_view,
        )
        
        # Should recognize transition from preserved path to icon
        self.assertTrue(transition_occurred)
        self.assertEqual(transition_type, "path_to_icon")
        
        # Transition to path type  
        self.entity.entity_type_str = str(EntityType.WALL)
        self.entity.save()
        transition_occurred, transition_type = self.manager.handle_entity_type_transition(
            entity = self.entity,
            location_view = self.location_view,
        )
        
        # Should recognize transition to path when both exist (icon_to_path)
        self.assertTrue(transition_occurred)
        self.assertEqual(transition_type, "icon_to_path")
        
        # Both should still exist
        self.assertEqual(EntityPosition.objects.filter(entity=self.entity).count(), 1)
        self.assertEqual(EntityPath.objects.filter(entity=self.entity).count(), 1)
        return
    
    def test_icon_to_icon_transition(self):
        """Test transition between two icon types"""
        # Create initial position
        EntityPosition.objects.create(
            entity = self.entity,
            location = self.location,
            svg_x = Decimal('500'),
            svg_y = Decimal('500'),
            svg_scale = Decimal('1.0'),
            svg_rotate = Decimal('0'),
        )
        
        # Change to different icon type
        self.entity.entity_type_str = str(EntityType.CAMERA)
        self.entity.save()
        
        transition_occurred, transition_type = self.manager.handle_entity_type_transition(
            entity = self.entity,
            location_view = self.location_view,
        )
        
        self.assertTrue(transition_occurred)
        self.assertEqual(transition_type, "icon_to_icon")
        
        # Only position should exist
        self.assertEqual(EntityPosition.objects.filter(entity=self.entity).count(), 1)
        self.assertEqual(EntityPath.objects.filter(entity=self.entity).count(), 0)
        return
    
    def test_path_to_path_transition(self):
        """Test transition between two path types"""
        # Start with path type
        self.entity.entity_type_str = str(EntityType.WALL)
        self.entity.save()
        
        # Create initial path
        EntityPath.objects.create(
            entity = self.entity,
            location = self.location,
            svg_path = 'M 0,0 L 100,100',
        )
        
        # Change to different path type
        self.entity.entity_type_str = str(EntityType.FENCE)
        self.entity.save()
        
        transition_occurred, transition_type = self.manager.handle_entity_type_transition(
            entity = self.entity,
            location_view = self.location_view,
        )
        
        self.assertTrue(transition_occurred)
        self.assertEqual(transition_type, "path_to_path")
        
        # Only path should exist
        self.assertEqual(EntityPosition.objects.filter(entity=self.entity).count(), 0)
        self.assertEqual(EntityPath.objects.filter(entity=self.entity).count(), 1)
        return
    
    def test_no_location_view_returns_false(self):
        """Test that transition fails gracefully without location view"""
        transition_occurred, transition_type = self.manager.handle_entity_type_transition(
            entity = self.entity,
            location_view = None,
        )
        
        self.assertFalse(transition_occurred)
        self.assertEqual(transition_type, "no_location_view")
        return
    
    def test_path_center_calculation(self):
        """Test geometric center calculation for paths"""
        # Test simple rectangle path
        svg_path = 'M 100,100 L 300,100 L 300,200 L 100,200 Z'
        center_x, center_y = self.manager._calculate_path_center(svg_path)
        
        # Center should be at (200, 150)
        self.assertAlmostEqual(center_x, 200.0, places=1)
        self.assertAlmostEqual(center_y, 150.0, places=1)
        
        # Test malformed path
        bad_path = 'invalid path data'
        center_x, center_y = self.manager._calculate_path_center(bad_path)
        
        # Should return None for invalid paths
        self.assertIsNone(center_x)
        self.assertIsNone(center_y)
        return
    
    def test_transaction_rollback_on_transition_failure(self):
        """Test that database transaction rolls back if transition logic fails"""
        from unittest.mock import patch
        
        # Start with valid entity
        original_name = self.entity.name
        original_type = self.entity.entity_type_str
        
        # Mock handle_entity_type_transition to raise an exception
        with patch.object(EntityManager, 'handle_entity_type_transition') as mock_transition:
            mock_transition.side_effect = Exception("Simulated transition failure")
            
            # Attempt entity update with EntityType change
            try:
                with transaction.atomic():
                    self.entity.name = "Updated Name"
                    self.entity.entity_type_str = str(EntityType.WALL)
                    self.entity.save()
                    
                    # This should raise exception and rollback transaction
                    EntityManager().handle_entity_type_transition(
                        entity = self.entity,
                        location_view = self.location_view,
                    )
            except Exception:
                pass  # Expected due to mock
        
        # Reload entity from database
        self.entity.refresh_from_db()
        
        # Verify transaction was rolled back - changes should be reverted
        self.assertEqual(self.entity.name, original_name)
        self.assertEqual(self.entity.entity_type_str, original_type)
        
        # Verify no orphaned EntityPosition/EntityPath records created
        self.assertEqual(EntityPosition.objects.filter(entity=self.entity).count(), 0)
        self.assertEqual(EntityPath.objects.filter(entity=self.entity).count(), 0)
        return

