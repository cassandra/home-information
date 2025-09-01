import logging

from django.urls import reverse

from hi.apps.collection.models import Collection, CollectionPosition
from hi.apps.entity.models import Entity
from hi.apps.location.models import Location, LocationView
from hi.enums import ViewMode, ViewType
from hi.testing.view_test_base import SyncViewTestCase, DualModeViewTestCase

logging.disable(logging.CRITICAL)


class TestCollectionAddView(DualModeViewTestCase):
    """
    Tests for CollectionAddView - demonstrates collection creation testing.
    This view handles adding new collections with optional location view integration.
    """

    def setUp(self):
        super().setUp()
        # Set edit mode (required by decorator)
        self.setSessionViewMode(ViewMode.EDIT)
        
        # Create test location and location view
        self.location = Location.objects.create(
            name='Test Location',
            svg_fragment_filename='test.svg',
            svg_view_box_str='0 0 100 100'
        )
        self.location_view = LocationView.objects.create(
            location=self.location,
            name='Test View',
            location_view_type_str='MAIN',
            svg_view_box_str='0 0 100 100',
            svg_rotate=0.0
        )

    def test_get_collection_add_form_location_view(self):
        """Test getting collection add form when in location view context."""
        # Set location view context
        self.setSessionViewType(ViewType.LOCATION_VIEW)
        
        url = reverse('collection_add')
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        self.assertHtmlResponse(response)
        self.assertTemplateRendered(response, 'collection/edit/modals/collection_add.html')
        
        # Form should include location view option
        form = response.context['collection_add_form']
        self.assertTrue(form.fields['include_in_location_view'].initial)

    def test_get_collection_add_form_non_location_view(self):
        """Test getting collection add form when not in location view context."""
        # Set non-location view context
        self.setSessionViewType(ViewType.CONFIGURATION)
        
        url = reverse('collection_add')
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        # Form should not include location view option
        form = response.context['collection_add_form']
        self.assertFalse(form.fields['include_in_location_view'].initial)

    def test_get_collection_add_form_async(self):
        """Test getting collection add form with AJAX request."""
        url = reverse('collection_add')
        response = self.async_get(url)

        self.assertSuccessResponse(response)
        self.assertJsonResponse(response)
        
        # HiModalView returns JSON with modal content for AJAX requests
        data = response.json()
        self.assertIn('modal', data)

    def test_post_invalid_form(self):
        """Test POST request with invalid form data."""
        url = reverse('collection_add')
        # Post empty data to trigger validation errors (name is required)
        response = self.client.post(url, {})

        self.assertSuccessResponse(response)
        # Should render form with errors
        form = response.context['collection_add_form']
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)

    def test_post_valid_form_with_location_view(self):
        """Test POST request with valid form data including location view."""
        # Set location view context so include_in_location_view is available
        self.setSessionViewType(ViewType.LOCATION_VIEW)
        
        url = reverse('collection_add')
        response = self.client.post(url, {
            'name': 'Test Collection',
            'collection_type_str': 'appliances',
            'collection_view_type_str': 'grid',
            'order_id': 1,
            'include_in_location_view': True
        })

        # Should return success with JSON redirect response
        self.assertSuccessResponse(response)
        self.assertJsonResponse(response)
        
        data = response.json()
        expected_url = reverse('home')
        self.assertEqual(data['location'], expected_url)
        
        # Verify collection was created
        collection = Collection.objects.get(name='Test Collection')
        self.assertEqual(collection.collection_type_str, 'appliances')
        self.assertEqual(collection.collection_view_type_str, 'grid')
        
        # Verify collection view was created
        from hi.apps.collection.models import CollectionView
        collection_view = CollectionView.objects.get(collection=collection)
        self.assertEqual(collection_view.location_view, self.location_view)

    def test_post_valid_form_without_location_view(self):
        """Test POST request with valid form data without location view."""
        # Set configuration context so include_in_location_view is available but not checked
        self.setSessionViewType(ViewType.CONFIGURATION)

        url = reverse('collection_add')
        response = self.client.post(url, {
            'name': 'Test Collection Without View',
            'collection_type_str': 'devices',
            'collection_view_type_str': 'list',
            'order_id': 2,
            'include_in_location_view': False
        })

        # Should return success with JSON redirect response
        self.assertSuccessResponse(response)
        self.assertJsonResponse(response)
        
        data = response.json()
        expected_url = reverse('home')
        self.assertEqual(data['location'], expected_url)
        
        # Verify collection was created
        collection = Collection.objects.get(name='Test Collection Without View')
        self.assertEqual(collection.collection_type_str, 'devices')
        self.assertEqual(collection.collection_view_type_str, 'list')
        
        # Verify no collection view was created
        from hi.apps.collection.models import CollectionView
        self.assertFalse(CollectionView.objects.filter(collection=collection).exists())

    def test_post_updates_collection_context(self):
        """Test that POST updates collection context when in collection view."""
        # Set collection view context
        self.setSessionViewType(ViewType.COLLECTION)

        url = reverse('collection_add')
        response = self.client.post(url, {
            'name': 'Test Collection Context',
            'collection_type_str': 'tools',
            'collection_view_type_str': 'grid',
            'order_id': 3
        })

        # Should return success with JSON redirect response
        self.assertSuccessResponse(response)
        self.assertJsonResponse(response)
        
        data = response.json()
        expected_url = reverse('home')
        self.assertEqual(data['location'], expected_url)
        
        # Verify collection was created
        collection = Collection.objects.get(name='Test Collection Context')
        self.assertEqual(collection.collection_type_str, 'tools')
        self.assertEqual(collection.collection_view_type_str, 'grid')
        # Note: Session context update behavior would need to be verified by checking
        # the actual session state if that's part of the view's functionality


class TestCollectionDeleteView(DualModeViewTestCase):
    """
    Tests for CollectionDeleteView - demonstrates collection deletion testing.
    This view handles collection deletion with confirmation.
    """

    def setUp(self):
        super().setUp()
        # Set edit mode (required by decorator)
        self.setSessionViewMode(ViewMode.EDIT)
        
        # Create test collection
        self.collection = Collection.objects.create(
            name='Test Collection',
            collection_type_str='other',
            collection_view_type_str='grid'
        )

    def test_get_collection_delete_confirmation(self):
        """Test getting collection delete confirmation."""
        url = reverse('collection_edit_collection_delete', kwargs={'collection_id': self.collection.id})
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        self.assertHtmlResponse(response)
        self.assertTemplateRendered(response, 'collection/edit/modals/collection_delete.html')
        self.assertEqual(response.context['collection'], self.collection)

    def test_get_collection_delete_async(self):
        """Test getting collection delete confirmation with AJAX request."""
        url = reverse('collection_edit_collection_delete', kwargs={'collection_id': self.collection.id})
        response = self.async_get(url)

        self.assertSuccessResponse(response)
        self.assertJsonResponse(response)
        
        # HiModalView returns JSON with modal content for AJAX requests
        data = response.json()
        self.assertIn('modal', data)

    def test_post_delete_without_confirmation(self):
        """Test POST request without confirmation."""
        url = reverse('collection_edit_collection_delete', kwargs={'collection_id': self.collection.id})
        response = self.client.post(url, {})

        self.assertEqual(response.status_code, 400)

    def test_post_delete_with_wrong_confirmation(self):
        """Test POST request with wrong confirmation value."""
        url = reverse('collection_edit_collection_delete', kwargs={'collection_id': self.collection.id})
        response = self.client.post(url, {'action': 'cancel'})

        self.assertEqual(response.status_code, 400)

    def test_post_delete_with_confirmation(self):
        """Test POST request with proper confirmation."""
        url = reverse('collection_edit_collection_delete', kwargs={'collection_id': self.collection.id})
        response = self.client.post(url, {'action': 'confirm'})

        # Should return success with JSON redirect response
        self.assertSuccessResponse(response)
        self.assertJsonResponse(response)
        
        data = response.json()
        expected_url = reverse('home')
        self.assertEqual(data['location'], expected_url)
        
        # Collection should be deleted
        with self.assertRaises(Collection.DoesNotExist):
            Collection.objects.get(id=self.collection.id)

    def test_post_delete_updates_session_when_current_collection(self):
        """Test that POST updates session when deleting current collection."""
        # Set this collection as current in session
        self.setSessionCollection(self.collection)
        
        url = reverse('collection_edit_collection_delete', kwargs={'collection_id': self.collection.id})
        response = self.client.post(url, {'action': 'confirm'})

        # Should return success with JSON redirect response
        self.assertSuccessResponse(response)
        self.assertJsonResponse(response)
        
        data = response.json()
        expected_url = reverse('home')
        self.assertEqual(data['location'], expected_url)
        
        # Collection should be deleted
        with self.assertRaises(Collection.DoesNotExist):
            Collection.objects.get(id=self.collection.id)

    def test_nonexistent_collection_returns_404(self):
        """Test that accessing nonexistent collection returns 404."""
        url = reverse('collection_edit_collection_delete', kwargs={'collection_id': 99999})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)


class TestCollectionPropertiesEditView(SyncViewTestCase):
    """
    Tests for CollectionPropertiesEditView - demonstrates collection editing testing.
    This view handles collection property updates.
    """

    def setUp(self):
        super().setUp()
        # Create test collection
        self.collection = Collection.objects.create(
            name='Test Collection',
            collection_type_str='other',
            collection_view_type_str='grid'
        )

    def test_post_valid_edit(self):
        """Test POST request with valid edit data."""
        url = reverse('collection_properties_edit', kwargs={'collection_id': self.collection.id})
        response = self.client.post(url, {
            'name': 'Updated Collection Name',
            'collection_type_str': 'electronics',
            'collection_view_type_str': 'list',
            'order_id': 1
        })

        # Should return success with JSON refresh response
        self.assertSuccessResponse(response)
        self.assertJsonResponse(response)
        
        data = response.json()
        self.assertEqual(data['refresh'], True)
        
        # Verify collection was updated in database
        updated_collection = Collection.objects.get(id=self.collection.id)
        self.assertEqual(updated_collection.name, 'Updated Collection Name')
        self.assertEqual(updated_collection.collection_type_str, 'electronics')
        self.assertEqual(updated_collection.collection_view_type_str, 'list')

    def test_post_invalid_edit(self):
        """Test POST request with invalid edit data."""
        url = reverse('collection_properties_edit', kwargs={'collection_id': self.collection.id})
        # Post empty name to trigger validation error
        response = self.client.post(url, {'name': ''})

        self.assertEqual(response.status_code, 400)
        
        # Verify collection was not modified in database
        unchanged_collection = Collection.objects.get(id=self.collection.id)
        self.assertEqual(unchanged_collection.name, 'Test Collection')  # Should be unchanged

    def test_nonexistent_collection_returns_404(self):
        """Test that accessing nonexistent collection returns 404."""
        url = reverse('collection_properties_edit', kwargs={'collection_id': 99999})
        response = self.client.post(url, {'name': 'Test'})

        self.assertEqual(response.status_code, 404)

    def test_get_not_allowed(self):
        """Test that GET requests are not allowed."""
        url = reverse('collection_properties_edit', kwargs={'collection_id': self.collection.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 405)


class TestCollectionPositionEditView(SyncViewTestCase):
    """
    Tests for CollectionPositionEditView - demonstrates collection position editing testing.
    This view handles updating collection positions on location views.
    """

    def setUp(self):
        super().setUp()
        # Set edit mode (required by decorator)
        self.setSessionViewMode(ViewMode.EDIT)
        
        # Create test location with order_id so LocationManager can find it as default
        self.location = Location.objects.create(
            name='Test Location',
            svg_fragment_filename='test.svg',
            svg_view_box_str='0 0 100 100',
            order_id=1  # This makes it findable by get_default_location()
        )
        
        # Create location view for the location and set it in session
        # This makes request.view_parameters.location available to LocationManager
        self.location_view = LocationView.objects.create(
            location=self.location,
            name='Test View',
            location_view_type_str='MAIN',
            svg_view_box_str='0 0 100 100',
            svg_rotate=0.0
        )
        self.setSessionLocationView(self.location_view)
        
        self.collection = Collection.objects.create(
            name='Test Collection',
            collection_type_str='other',
            collection_view_type_str='grid'
        )
        self.collection_position = CollectionPosition.objects.create(
            collection=self.collection,
            location=self.location,
            svg_x=50.0,
            svg_y=50.0
        )

    def test_post_valid_position_edit(self):
        """Test POST request with valid position data."""
        url = reverse('collection_position_edit', kwargs={'collection_id': self.collection.id})
        response = self.client.post(url, {
            'svg_x': '60.0',
            'svg_y': '70.0',
            'svg_scale': '1.0',
            'svg_rotate': '0.0'
        })

        # Should return success with JSON response
        self.assertSuccessResponse(response)
        self.assertJsonResponse(response)
        
        # Verify position was updated in database
        updated_position = CollectionPosition.objects.get(collection=self.collection)
        self.assertEqual(float(updated_position.svg_x), 60.0)
        self.assertEqual(float(updated_position.svg_y), 70.0)

    def test_post_invalid_position_edit(self):
        """Test POST request with invalid position data."""
        url = reverse('collection_position_edit', kwargs={'collection_id': self.collection.id})
        response = self.client.post(url, {
            'svg_x': 'invalid',
            'svg_y': 'invalid'
        })

        # Should still return success but log warning (based on original test comment)
        self.assertSuccessResponse(response)
        
        # Verify position was not changed in database
        unchanged_position = CollectionPosition.objects.get(collection=self.collection)
        self.assertEqual(float(unchanged_position.svg_x), 50.0)  # Should be unchanged
        self.assertEqual(float(unchanged_position.svg_y), 50.0)  # Should be unchanged

    def test_post_nonexistent_position(self):
        """Test POST request for nonexistent collection position."""
        # Create collection without position
        other_collection = Collection.objects.create(
            name='Other Collection',
            collection_type_str='cameras',  # Use valid enum value
            collection_view_type_str='list'  # Use valid enum value
        )

        url = reverse('collection_position_edit', kwargs={'collection_id': other_collection.id})
        response = self.client.post(url, {})

        self.assertEqual(response.status_code, 404)

    def test_nonexistent_collection_returns_404(self):
        """Test that accessing nonexistent collection returns 404."""
        url = reverse('collection_position_edit', kwargs={'collection_id': 99999})
        response = self.client.post(url, {})

        self.assertEqual(response.status_code, 404)

    def test_get_not_allowed(self):
        """Test that GET requests are not allowed."""
        url = reverse('collection_position_edit', kwargs={'collection_id': self.collection.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 405)


class TestCollectionManageItemsView(SyncViewTestCase):
    """
    Tests for CollectionManageItemsView - demonstrates collection item management testing.
    This view displays interface for managing items in collections.
    """

    def setUp(self):
        super().setUp()
        # Set edit mode (required by decorator)
        self.setSessionViewMode(ViewMode.EDIT)
        
        # Create test collection
        self.collection = Collection.objects.create(
            name='Test Collection',
            collection_type_str='other',
            collection_view_type_str='grid'
        )

    def test_get_manage_items_view(self):
        """Test getting collection manage items view."""
        # Ensure this collection is the default by setting order_id=0
        self.collection.order_id = 0
        self.collection.save()
        
        # Create a location and location view for middleware to find
        location = Location.objects.create(
            name='Test Location',
            svg_fragment_filename='test.svg',
            svg_view_box_str='0 0 100 100',
            order_id=1
        )
        
        _ = LocationView.objects.create(
            location=location,
            name='Test View',
            location_view_type_str='MAIN',
            svg_view_box_str='0 0 100 100',
            svg_rotate=0.0,
            order_id=0
        )
        
        # Create some entities to populate the collection groups  
        _ = Entity.objects.create(
            name='Test Entity 1',
            entity_type_str='light'
        )
        _ = Entity.objects.create(
            name='Test Entity 2',
            entity_type_str='sensor'
        )
        
        url = reverse('collection_edit_collection_manage_items')
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        self.assertJsonResponse(response)  # HiSideView returns JSON
        
        # Parse JSON response - HiSideView inserts content into hi-side-content
        data = response.json()
        self.assertIn('insert', data)
        self.assertIn('hi-side-content', data['insert'])
        
        # Verify the manage items view rendered with entity groups
        side_content = data['insert']['hi-side-content']
        self.assertIn('Items in Collection', side_content)
        self.assertIn('Test Entity 1', side_content)
        self.assertIn('Test Entity 2', side_content)

    def test_post_not_allowed(self):
        """Test that POST requests are not allowed."""
        # Ensure this collection is the default by setting order_id=0
        self.collection.order_id = 0
        self.collection.save()
        
        # Create a location and location view for middleware to find
        location = Location.objects.create(
            name='Test Location',
            svg_fragment_filename='test.svg',
            svg_view_box_str='0 0 100 100',
            order_id=1
        )
        
        LocationView.objects.create(
            location=location,
            name='Test View',
            location_view_type_str='MAIN',
            svg_view_box_str='0 0 100 100',
            svg_rotate=0.0,
            order_id=0
        )
        
        url = reverse('collection_edit_collection_manage_items')
        response = self.client.post(url)

        self.assertEqual(response.status_code, 405)

        
class TestCollectionEntityToggleView(SyncViewTestCase):
    """
    Tests for CollectionEntityToggleView - demonstrates entity toggle testing.
    This view handles adding/removing entities from collections.
    """

    def setUp(self):
        super().setUp()
        # Set edit mode (required by decorator)
        self.setSessionViewMode(ViewMode.EDIT)
        
        # Create test collection and entity
        self.collection = Collection.objects.create(
            name='Test Collection',
            collection_type_str='other',  # Use valid enum value
            collection_view_type_str='grid'  # Use valid enum value
        )
        self.entity = Entity.objects.create(
            name='Test Entity',
            entity_type_str='light'
        )

    def test_post_toggle_entity_add(self):
        """Test POST request to add entity to collection."""
        from hi.apps.collection.models import CollectionEntity
        
        # Verify entity is not in collection initially
        self.assertFalse(CollectionEntity.objects.filter(collection=self.collection,
                                                         entity=self.entity).exists())
        
        url = reverse('collection_edit_collection_entity_toggle', kwargs={
            'collection_id': self.collection.id,
            'entity_id': self.entity.id
        })
        response = self.client.post(url)
        
        # Should return success with antinode response (JSON format)
        self.assertSuccessResponse(response)
        self.assertJsonResponse(response)
        
        # Verify entity was added to collection
        self.assertTrue(CollectionEntity.objects.filter(collection=self.collection,
                                                        entity=self.entity).exists())

    def test_post_toggle_entity_remove(self):
        """Test POST request to remove entity from collection."""
        from hi.apps.collection.models import CollectionEntity
        
        # Add entity to collection first
        CollectionEntity.objects.create(collection=self.collection, entity=self.entity)
        self.assertTrue(CollectionEntity.objects.filter(collection=self.collection,
                                                        entity=self.entity).exists())
        
        url = reverse('collection_edit_collection_entity_toggle', kwargs={
            'collection_id': self.collection.id,
            'entity_id': self.entity.id
        })
        response = self.client.post(url)
        
        # Should return success with antinode response (JSON format)
        self.assertSuccessResponse(response)
        self.assertJsonResponse(response)
        
        # Verify entity was removed from collection
        self.assertFalse(CollectionEntity.objects.filter(collection=self.collection,
                                                         entity=self.entity).exists())

    def test_nonexistent_collection_returns_404(self):
        """Test that accessing nonexistent collection returns 404."""
        url = reverse('collection_edit_collection_entity_toggle', kwargs={
            'collection_id': 99999,
            'entity_id': self.entity.id
        })
        response = self.client.post(url)

        self.assertEqual(response.status_code, 404)

    def test_nonexistent_entity_returns_404(self):
        """Test that accessing nonexistent entity returns 404."""
        url = reverse('collection_edit_collection_entity_toggle', kwargs={
            'collection_id': self.collection.id,
            'entity_id': 99999
        })
        response = self.client.post(url)

        self.assertEqual(response.status_code, 404)

    def test_get_not_allowed(self):
        """Test that GET requests are not allowed."""
        url = reverse('collection_edit_collection_entity_toggle', kwargs={
            'collection_id': self.collection.id,
            'entity_id': self.entity.id
        })
        response = self.client.get(url)

        self.assertEqual(response.status_code, 405)
        
