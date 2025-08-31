"""
Django Test Pattern Examples - Best Practices from HI Application

This file contains concrete examples of well-structured Django tests that avoid
common anti-patterns. These patterns were derived from extensive refactoring
work to eliminate over-mocking and improve test reliability.
"""

import json
import uuid
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile

from hi.apps.collection.models import Collection, CollectionEntity
from hi.apps.entity.models import Entity, EntityStateDelegation
from hi.apps.location.models import Location, LocationView
from hi.apps.collection.enums import CollectionType, CollectionViewType
from hi.apps.entity.enums import EntityType
from hi.apps.location.enums import LocationViewType
from hi.enums import ViewMode, ViewType
from hi.testing.view_test_base import SyncViewTestCase, DualModeViewTestCase


# =============================================================================
# 1. BASIC CRUD TESTING WITH REAL OBJECTS
# =============================================================================

class ExampleCRUDTestCase(SyncViewTestCase):
    """Example of testing CRUD operations with real database objects."""
    
    def setUp(self):
        super().setUp()
        # Set required session state
        self.setSessionViewMode(ViewMode.EDIT)
        
        # Create test objects with proper enum string conversion
        self.collection = Collection.objects.create(
            name='Test Collection',
            collection_type_str=str(CollectionType.OTHER),  # Always use str() for enums
            collection_view_type_str=str(CollectionViewType.GRID),
            order_id=0  # Make it the default
        )
        
        self.entity = Entity.objects.create(
            name='Test Entity',
            entity_type_str=str(EntityType.LIGHT)
        )
    
    def test_create_with_real_objects(self):
        """Example: Test creation using real objects, not mocks."""
        # Verify initial state
        self.assertEqual(Collection.objects.count(), 1)
        
        url = reverse('collection_add')
        response = self.client.post(url, {
            'name': 'New Collection',
            'collection_type_str': str(CollectionType.ELECTRONICS),
            'collection_view_type_str': str(CollectionViewType.LIST),
        })
        
        # Verify the real database changes
        self.assertSuccessResponse(response)
        self.assertEqual(Collection.objects.count(), 2)
        
        new_collection = Collection.objects.get(name='New Collection')
        self.assertEqual(new_collection.collection_type_str, str(CollectionType.ELECTRONICS))
    
    def test_many_to_many_through_model(self):
        """Example: Test many-to-many relationships via through models."""
        # Don't do: self.collection.entities.add(self.entity)  # This won't work
        
        # Do: Use the through model
        self.assertFalse(CollectionEntity.objects.filter(
            collection=self.collection, 
            entity=self.entity
        ).exists())
        
        # Create the relationship via through model
        CollectionEntity.objects.create(
            collection=self.collection,
            entity=self.entity,
            order_id=0
        )
        
        # Verify the relationship exists
        self.assertTrue(CollectionEntity.objects.filter(
            collection=self.collection,
            entity=self.entity
        ).exists())


# =============================================================================
# 2. TESTING VIEWS WITH JSON/AJAX RESPONSES
# =============================================================================

class ExampleAjaxViewTestCase(SyncViewTestCase):
    """Example of testing views that return JSON responses via antinode."""
    
    def setUp(self):
        super().setUp()
        self.setSessionViewMode(ViewMode.EDIT)
        
        self.collection = Collection.objects.create(
            name='Test Collection',
            collection_type_str=str(CollectionType.OTHER),
            collection_view_type_str=str(CollectionViewType.GRID)
        )
    
    def test_ajax_view_returns_json_not_redirect(self):
        """Example: Test modern AJAX views that return JSON, not redirects."""
        url = reverse('collection_edit_collection_delete', kwargs={
            'collection_id': self.collection.id
        })
        response = self.client.post(url, {'action': 'confirm'})
        
        # Don't expect: self.assertEqual(response.status_code, 302)  # Wrong!
        
        # Do expect: JSON response with location field
        self.assertSuccessResponse(response)
        self.assertJsonResponse(response)
        
        data = response.json()
        self.assertEqual(data['location'], reverse('home'))
        
        # Verify the real business logic occurred
        with self.assertRaises(Collection.DoesNotExist):
            Collection.objects.get(id=self.collection.id)
    
    def test_view_delegation_with_real_integration(self):
        """Example: Test view delegation by verifying end results, not mocking."""
        entity1 = Entity.objects.create(name='Entity 1', entity_type_str=str(EntityType.LIGHT))
        entity2 = Entity.objects.create(name='Entity 2', entity_type_str=str(EntityType.LIGHT))
        
        # Add entities to collection with initial order
        CollectionEntity.objects.create(collection=self.collection, entity=entity1, order_id=0)
        CollectionEntity.objects.create(collection=self.collection, entity=entity2, order_id=1)
        
        # Set required session state for delegation
        self.setSessionViewType(ViewType.COLLECTION)
        self.setSessionCollection(self.collection)
        
        # Test reordering (view delegates to CollectionReorderEntitiesView)
        url = reverse('edit_reorder_items')
        post_data = {
            'html_id_list': json.dumps([
                f'hi-entity-{entity2.id}',  # Move entity2 first
                f'hi-entity-{entity1.id}',  # Move entity1 second
            ])
        }
        response = self.client.post(url, post_data)
        
        self.assertSuccessResponse(response)
        
        # Verify the delegation worked by checking database state
        reordered = list(CollectionEntity.objects.filter(
            collection=self.collection
        ).order_by('order_id'))
        self.assertEqual(reordered[0].entity, entity2)
        self.assertEqual(reordered[1].entity, entity1)


# =============================================================================
# 3. FORM VALIDATION AND FILE UPLOAD TESTING
# =============================================================================

class ExampleFormValidationTestCase(SyncViewTestCase):
    """Example of testing forms with proper field requirements."""
    
    def setUp(self):
        super().setUp()
        self.setSessionViewMode(ViewMode.EDIT)
        
        self.location = Location.objects.create(
            name='Test Location',
            svg_fragment_filename='test.svg',
            svg_view_box_str='0 0 100 100',
            order_id=1
        )
        
        self.collection = Collection.objects.create(
            name='Test Collection',
            collection_type_str=str(CollectionType.OTHER),
            collection_view_type_str=str(CollectionViewType.GRID)
        )
        
        # Create position for testing
        from hi.apps.collection.models import CollectionPosition
        self.collection_position = CollectionPosition.objects.create(
            collection=self.collection,
            location=self.location,
            svg_x=50.0,
            svg_y=50.0
        )
    
    def test_form_with_all_required_fields(self):
        """Example: Include ALL required form fields, not just the obvious ones."""
        url = reverse('collection_position_edit', kwargs={
            'collection_id': self.collection.id
        })
        
        # Don't submit incomplete data:
        # response = self.client.post(url, {
        #     'svg_x': '60.0',
        #     'svg_y': '70.0'  # Missing svg_scale and svg_rotate!
        # })
        
        # Do submit complete form data:
        response = self.client.post(url, {
            'svg_x': '60.0',
            'svg_y': '70.0',
            'svg_scale': '1.0',    # Required!
            'svg_rotate': '0.0'    # Required!
        })
        
        self.assertSuccessResponse(response)
        self.assertJsonResponse(response)
        
        # Verify the database was actually updated
        updated_position = CollectionPosition.objects.get(collection=self.collection)
        self.assertEqual(float(updated_position.svg_x), 60.0)
        self.assertEqual(float(updated_position.svg_y), 70.0)
    
    def test_file_upload_without_mocking(self):
        """Example: Test file uploads with real files, not mocked file handling."""
        # Create a real test SVG file
        svg_content = b'''<svg viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
            <rect x="50" y="50" width="100" height="100" fill="blue"/>
        </svg>'''
        
        svg_file = SimpleUploadedFile(
            'test_location.svg', 
            svg_content, 
            content_type='image/svg+xml'
        )
        
        url = reverse('location_svg_replace', kwargs={'location_id': self.location.id})
        response = self.client.post(url, {
            'svg_file': svg_file,
            'remove_dangerous_svg_items': False
        })
        
        self.assertSuccessResponse(response)
        
        # Verify the file was processed (not just that a method was called)
        updated_location = Location.objects.get(id=self.location.id)
        # The SVG processing should have extracted content and updated viewBox
        self.assertIsNotNone(updated_location.svg_view_box_str)


# =============================================================================
# 4. TESTING COMPLEX BUSINESS LOGIC WITH REAL RELATIONSHIPS
# =============================================================================

class ExampleComplexBusinessLogicTestCase(SyncViewTestCase):
    """Example of testing complex business relationships without over-mocking."""
    
    def setUp(self):
        super().setUp()
        self.setSessionViewMode(ViewMode.EDIT)
        
        # Create entities for pairing
        self.entity = Entity.objects.create(
            name='Main Entity',
            entity_type_str=str(EntityType.LIGHT)
        )
        self.paired_entity = Entity.objects.create(
            name='Paired Entity', 
            entity_type_str=str(EntityType.LIGHT)
        )
        
        # Create entity states (required for pairing)
        from hi.apps.entity.models import EntityState
        self.entity_state = EntityState.objects.create(
            entity=self.entity,
            attribute_name='state',
            current_value='off'
        )
    
    def test_entity_pairing_system(self):
        """Example: Test complex relationships like entity pairing via delegation models."""
        # Don't assume direct relationships - use the actual business model
        
        # Entity pairing works through EntityStateDelegation, not direct relationships
        EntityStateDelegation.objects.create(
            entity_state=self.entity_state,
            delegate_entity=self.paired_entity
        )
        
        # Test the business logic
        url = reverse('entity_edit_manage_pairings', kwargs={'entity_id': self.entity.id})
        response = self.client.get(url)
        
        self.assertSuccessResponse(response)
        
        # Verify the pairing relationship is reflected in the response
        content = response.content.decode()
        self.assertIn(self.paired_entity.name, content)
        
        # Or test removal
        url = reverse('entity_edit_pairing_remove', kwargs={
            'entity_id': self.entity.id,
            'paired_entity_id': self.paired_entity.id
        })
        response = self.client.post(url)
        
        self.assertSuccessResponse(response)
        
        # Verify the delegation was removed
        self.assertFalse(EntityStateDelegation.objects.filter(
            entity_state__entity=self.entity,
            delegate_entity=self.paired_entity
        ).exists())


# =============================================================================
# 5. TESTING WITH PROPER SESSION AND MIDDLEWARE SETUP
# =============================================================================

class ExampleSessionDependentTestCase(SyncViewTestCase):
    """Example of testing views that depend on middleware-managed session state."""
    
    def setUp(self):
        super().setUp()
        # Many views require specific session state
        self.setSessionViewMode(ViewMode.EDIT)
        
        # Create objects that middleware needs to find
        self.location = Location.objects.create(
            name='Test Location',
            svg_fragment_filename='test.svg',
            svg_view_box_str='0 0 100 100',
            order_id=1  # Make it findable as default
        )
        
        self.location_view = LocationView.objects.create(
            location=self.location,
            name='Test View',
            location_view_type_str=str(LocationViewType.DEFAULT),
            svg_view_box_str='0 0 100 100',
            svg_rotate=0.0,
            order_id=0  # Make it findable as default
        )
        
        self.collection = Collection.objects.create(
            name='Test Collection',
            collection_type_str=str(CollectionType.OTHER),
            collection_view_type_str=str(CollectionViewType.GRID),
            order_id=0  # Make it findable as default
        )
    
    def test_view_requiring_session_context(self):
        """Example: Test views that need proper session context."""
        # This view requires collection context and default location/view
        url = reverse('collection_edit_collection_manage_items')
        response = self.client.get(url)
        
        self.assertSuccessResponse(response)
        self.assertJsonResponse(response)  # HiSideView returns JSON
        
        # Verify the view rendered properly with session context
        data = response.json()
        self.assertIn('insert', data)
        self.assertIn('hi-side-content', data['insert'])
        
        side_content = data['insert']['hi-side-content']
        self.assertIn('Items in Collection', side_content)
        self.assertIn(self.location.name, side_content)  # Location context
    
    def test_method_not_allowed_with_proper_setup(self):
        """Example: Test method restrictions with proper database setup."""
        # The view needs objects to exist to avoid 500 errors before method checking
        url = reverse('collection_edit_collection_manage_items')
        response = self.client.post(url)  # POST not allowed
        
        # With proper setup, we get 405 instead of 500
        self.assertEqual(response.status_code, 405)


# =============================================================================
# 6. SYNTHETIC DATA USAGE PATTERNS  
# =============================================================================

class ExampleSyntheticDataTestCase(SyncViewTestCase):
    """Example of using synthetic data generators consistently."""
    
    def create_test_entity(self, **kwargs):
        """Example synthetic data method following project patterns."""
        unique_id = str(uuid.uuid4())[:8]
        defaults = {
            'name': f'Test Entity {unique_id}',
            'entity_type_str': str(EntityType.LIGHT),
            'integration_id': f'test.entity.{unique_id}',
            'integration_name': 'test_integration',
        }
        defaults.update(kwargs)
        return Entity.objects.create(**defaults)
    
    def create_test_collection(self, **kwargs):
        """Example synthetic data method with proper defaults."""
        unique_id = str(uuid.uuid4())[:8]
        defaults = {
            'name': f'Test Collection {unique_id}',
            'collection_type_str': str(CollectionType.OTHER),
            'collection_view_type_str': str(CollectionViewType.GRID),
        }
        defaults.update(kwargs)
        return Collection.objects.create(**defaults)
    
    def test_using_synthetic_data(self):
        """Example: Use synthetic data for consistent, unique test objects."""
        # Create multiple entities without naming conflicts
        entity1 = self.create_test_entity(name='Custom Entity 1')
        entity2 = self.create_test_entity(entity_type_str=str(EntityType.SENSOR))
        
        collection1 = self.create_test_collection()
        collection2 = self.create_test_collection(
            collection_type_str=str(CollectionType.ELECTRONICS)
        )
        
        # All objects have unique names and proper defaults
        self.assertNotEqual(entity1.name, entity2.name)
        self.assertNotEqual(collection1.name, collection2.name)
        self.assertEqual(entity2.entity_type_str, str(EntityType.SENSOR))


# =============================================================================
# 7. TESTING ERROR CONDITIONS AND EDGE CASES
# =============================================================================

class ExampleErrorHandlingTestCase(SyncViewTestCase):
    """Example of testing error conditions without mocking exceptions."""
    
    def setUp(self):
        super().setUp()
        self.setSessionViewMode(ViewMode.EDIT)
        
        self.collection = Collection.objects.create(
            name='Test Collection',
            collection_type_str=str(CollectionType.OTHER),
            collection_view_type_str=str(CollectionViewType.GRID)
        )
    
    def test_404_with_nonexistent_object(self):
        """Example: Test 404 conditions with real database queries."""
        # Don't mock the DoesNotExist exception
        url = reverse('collection_edit_collection_delete', kwargs={
            'collection_id': 99999  # Non-existent ID
        })
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 404)
    
    def test_validation_errors_with_real_forms(self):
        """Example: Test form validation with real form processing."""
        url = reverse('collection_add')
        response = self.client.post(url, {
            'name': '',  # Invalid - empty name
            'collection_type_str': str(CollectionType.OTHER),
            'collection_view_type_str': str(CollectionViewType.GRID),
        })
        
        # Should return form with validation errors
        self.assertEqual(response.status_code, 400)
        
        # Verify no collection was created
        self.assertEqual(Collection.objects.count(), 1)  # Only setUp collection


# =============================================================================
# SUMMARY OF KEY PATTERNS
# =============================================================================

"""
KEY PATTERNS DEMONSTRATED:

1. **Use Real Objects**: Create actual model instances instead of mocking
2. **Enum String Conversion**: Always use str(EnumType.VALUE) for enum fields  
3. **Through Model Relationships**: Use intermediate models for M2M relationships
4. **Complete Form Data**: Include ALL required fields, not just obvious ones
5. **JSON Response Testing**: Expect JSON from modern AJAX views, not redirects
6. **Session State Setup**: Configure required middleware state in setUp()
7. **Default Object Order**: Use order_id=0 for objects that need to be "default"
8. **Synthetic Data**: Use consistent patterns for test data generation
9. **Real File Uploads**: Use SimpleUploadedFile for file testing
10. **Integration Testing**: Test full flows rather than just delegation

ANTI-PATTERNS TO AVOID:

❌ Mocking basic CRUD operations
❌ Mocking entire view classes for delegation testing
❌ Assuming direct M2M relationships exist
❌ Expecting HTTP redirects from AJAX views
❌ Incomplete form data in tests
❌ Missing session state setup
❌ Testing mock interactions instead of business outcomes
"""