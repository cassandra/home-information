import json
import logging
from unittest.mock import Mock, patch

from django.urls import reverse

from hi.apps.collection.collection_manager import CollectionManager
from hi.apps.collection.models import Collection, CollectionPosition
from hi.apps.entity.models import Entity
from hi.apps.location.location_manager import LocationManager
from hi.apps.location.models import Location, LocationView
from hi.enums import ViewMode, ViewType
from hi.tests.view_test_base import SyncViewTestCase, DualModeViewTestCase

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
        self.assertTrue(form.include_in_location_view)

    def test_get_collection_add_form_non_location_view(self):
        """Test getting collection add form when not in location view context."""
        # Set non-location view context
        self.setSessionViewType(ViewType.CONFIGURATION)
        
        url = reverse('collection_add')
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        # Form should not include location view option
        form = response.context['collection_add_form']
        self.assertFalse(form.include_in_location_view)

    def test_get_collection_add_form_async(self):
        """Test getting collection add form with AJAX request."""
        url = reverse('collection_add')
        response = self.async_get(url)

        self.assertSuccessResponse(response)
        self.assertJsonResponse(response)
        
        # HiModalView returns JSON with modal content for AJAX requests
        data = response.json()
        self.assertIn('modal', data)

    @patch('hi.apps.collection.edit.forms.CollectionAddForm')
    def test_post_invalid_form(self, mock_form_class):
        """Test POST request with invalid form data."""
        # Mock invalid form
        mock_form = Mock()
        mock_form.is_valid.return_value = False
        mock_form_class.return_value = mock_form

        url = reverse('collection_add')
        response = self.client.post(url, {})

        self.assertSuccessResponse(response)
        # Should render form with errors
        self.assertEqual(response.context['collection_add_form'], mock_form)

    @patch.object(CollectionManager, 'create_collection_view')
    @patch.object(LocationManager, 'get_default_location_view')
    @patch('hi.apps.collection.edit.forms.CollectionAddForm')
    def test_post_valid_form_with_location_view(
            self, mock_form_class, mock_get_location_view, mock_create_view):
        """Test POST request with valid form data including location view."""
        # Mock valid form
        mock_form = Mock()
        mock_form.is_valid.return_value = True
        mock_form.clean.return_value = {'include_in_location_view': True}
        mock_collection = Mock()
        mock_form.save.return_value = mock_collection
        mock_form_class.return_value = mock_form

        # Mock location manager
        mock_get_location_view.return_value = self.location_view

        url = reverse('collection_add')
        response = self.client.post(url, {
            'name': 'Test Collection',
            'include_in_location_view': True
        })

        self.assertEqual(response.status_code, 302)
        expected_url = reverse('home')
        self.assertEqual(response.url, expected_url)
        
        # Should create collection view
        mock_create_view.assert_called_once_with(
            collection=mock_collection,
            location_view=self.location_view
        )

    @patch('hi.apps.collection.edit.forms.CollectionAddForm')
    def test_post_valid_form_without_location_view(self, mock_form_class):
        """Test POST request with valid form data without location view."""
        # Mock valid form
        mock_form = Mock()
        mock_form.is_valid.return_value = True
        mock_form.clean.return_value = {'include_in_location_view': False}
        mock_collection = Mock()
        mock_form.save.return_value = mock_collection
        mock_form_class.return_value = mock_form

        url = reverse('collection_add')
        response = self.client.post(url, {
            'name': 'Test Collection',
            'include_in_location_view': False
        })

        self.assertEqual(response.status_code, 302)
        expected_url = reverse('home')
        self.assertEqual(response.url, expected_url)

    @patch('hi.apps.collection.edit.forms.CollectionAddForm')
    def test_post_updates_collection_context(self, mock_form_class):
        """Test that POST updates collection context when in collection view."""
        # Set collection view context
        self.setSessionViewType(ViewType.COLLECTION)
        
        # Mock valid form
        mock_form = Mock()
        mock_form.is_valid.return_value = True
        mock_form.clean.return_value = {'include_in_location_view': False}
        mock_collection = Mock()
        mock_collection.id = 123
        mock_form.save.return_value = mock_collection
        mock_form_class.return_value = mock_form

        url = reverse('collection_add')
        response = self.client.post(url, {'name': 'Test Collection'})

        self.assertEqual(response.status_code, 302)
        # Should update session with new collection


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
            collection_type_str='ROOM',
            collection_view_type_str='MAIN'
        )

    def test_get_collection_delete_confirmation(self):
        """Test getting collection delete confirmation."""
        url = reverse('collection_delete', kwargs={'collection_id': self.collection.id})
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        self.assertHtmlResponse(response)
        self.assertTemplateRendered(response, 'collection/edit/modals/collection_delete.html')
        self.assertEqual(response.context['collection'], self.collection)

    def test_get_collection_delete_async(self):
        """Test getting collection delete confirmation with AJAX request."""
        url = reverse('collection_delete', kwargs={'collection_id': self.collection.id})
        response = self.async_get(url)

        self.assertSuccessResponse(response)
        self.assertJsonResponse(response)
        
        # HiModalView returns JSON with modal content for AJAX requests
        data = response.json()
        self.assertIn('modal', data)

    def test_post_delete_without_confirmation(self):
        """Test POST request without confirmation."""
        url = reverse('collection_delete', kwargs={'collection_id': self.collection.id})
        response = self.client.post(url, {})

        self.assertEqual(response.status_code, 400)

    def test_post_delete_with_wrong_confirmation(self):
        """Test POST request with wrong confirmation value."""
        url = reverse('collection_delete', kwargs={'collection_id': self.collection.id})
        response = self.client.post(url, {'action': 'cancel'})

        self.assertEqual(response.status_code, 400)

    def test_post_delete_with_confirmation(self):
        """Test POST request with proper confirmation."""
        url = reverse('collection_delete', kwargs={'collection_id': self.collection.id})
        response = self.client.post(url, {'action': 'confirm'})

        self.assertEqual(response.status_code, 302)
        expected_url = reverse('home')
        self.assertEqual(response.url, expected_url)
        
        # Collection should be deleted
        with self.assertRaises(Collection.DoesNotExist):
            Collection.objects.get(id=self.collection.id)

    def test_post_delete_updates_session_when_current_collection(self):
        """Test that POST updates session when deleting current collection."""
        # Set this collection as current in session
        self.setSessionCollection(self.collection)
        
        url = reverse('collection_delete', kwargs={'collection_id': self.collection.id})
        response = self.client.post(url, {'action': 'confirm'})

        self.assertEqual(response.status_code, 302)
        # Should clear collection from session

    def test_nonexistent_collection_returns_404(self):
        """Test that accessing nonexistent collection returns 404."""
        url = reverse('collection_delete', kwargs={'collection_id': 99999})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)


class TestCollectionEditView(SyncViewTestCase):
    """
    Tests for CollectionEditView - demonstrates collection editing testing.
    This view handles collection property updates.
    """

    def setUp(self):
        super().setUp()
        # Create test collection
        self.collection = Collection.objects.create(
            name='Test Collection',
            collection_type_str='ROOM',
            collection_view_type_str='MAIN'
        )

    @patch('hi.apps.collection.edit.forms.CollectionEditForm')
    @patch('hi.apps.common.antinode.refresh_response')
    def test_post_valid_edit(self, mock_refresh_response, mock_form_class):
        """Test POST request with valid edit data."""
        # Mock valid form
        mock_form = Mock()
        mock_form.is_valid.return_value = True
        mock_form_class.return_value = mock_form
        
        # Mock refresh response
        mock_refresh_response.return_value = 'refresh_response'

        url = reverse('collection_edit', kwargs={'collection_id': self.collection.id})
        _ = self.client.post(url, {'name': 'Updated Collection Name'})

        mock_form.save.assert_called_once()
        mock_refresh_response.assert_called_once()

    @patch('hi.apps.collection.edit.forms.CollectionEditForm')
    def test_post_invalid_edit(self, mock_form_class):
        """Test POST request with invalid edit data."""
        # Mock invalid form
        mock_form = Mock()
        mock_form.is_valid.return_value = False
        mock_form_class.return_value = mock_form

        url = reverse('collection_edit', kwargs={'collection_id': self.collection.id})
        response = self.client.post(url, {'name': ''})

        self.assertEqual(response.status_code, 400)
        mock_form.save.assert_not_called()

    def test_nonexistent_collection_returns_404(self):
        """Test that accessing nonexistent collection returns 404."""
        url = reverse('collection_edit', kwargs={'collection_id': 99999})
        response = self.client.post(url, {'name': 'Test'})

        self.assertEqual(response.status_code, 404)

    def test_get_not_allowed(self):
        """Test that GET requests are not allowed."""
        url = reverse('collection_edit', kwargs={'collection_id': self.collection.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 405)


class TestCollectionReorder(SyncViewTestCase):
    """
    Tests for CollectionReorder - demonstrates collection reordering testing.
    This view handles reordering collections.
    """

    def setUp(self):
        super().setUp()
        # Set edit mode (required by decorator)
        self.setSessionViewMode(ViewMode.EDIT)
        
        # Create test collections
        self.collection1 = Collection.objects.create(
            name='Collection 1',
            collection_type_str='ROOM',
            collection_view_type_str='MAIN'
        )
        self.collection2 = Collection.objects.create(
            name='Collection 2',
            collection_type_str='GROUP',
            collection_view_type_str='MAIN'
        )

    @patch.object(CollectionManager, 'set_collection_order')
    @patch('hi.apps.common.antinode.response')
    def test_post_valid_reorder(self, mock_antinode_response, mock_set_order):
        """Test POST request with valid reorder data."""
        mock_antinode_response.return_value = 'success_response'
        
        collection_id_list = [self.collection2.id, self.collection1.id]
        url = reverse('collection_reorder', kwargs={
            'collection_id_list': json.dumps(collection_id_list)
        })
        _ = self.client.post(url)

        mock_set_order.assert_called_once_with(collection_id_list=collection_id_list)
        mock_antinode_response.assert_called_once_with(main_content='OK')

    def test_post_invalid_json(self):
        """Test POST request with invalid JSON data."""
        url = reverse('collection_reorder', kwargs={
            'collection_id_list': 'invalid-json'
        })
        response = self.client.post(url)

        self.assertEqual(response.status_code, 400)

    def test_post_empty_collection_list(self):
        """Test POST request with empty collection list."""
        url = reverse('collection_reorder', kwargs={
            'collection_id_list': json.dumps([])
        })
        response = self.client.post(url)

        self.assertEqual(response.status_code, 400)

    def test_get_not_allowed(self):
        """Test that GET requests are not allowed."""
        url = reverse('collection_reorder', kwargs={
            'collection_id_list': json.dumps([1, 2])
        })
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
        
        # Create test data
        self.location = Location.objects.create(
            name='Test Location',
            svg_fragment_filename='test.svg',
            svg_view_box_str='0 0 100 100'
        )
        self.collection = Collection.objects.create(
            name='Test Collection',
            collection_type_str='ROOM',
            collection_view_type_str='MAIN'
        )
        self.collection_position = CollectionPosition.objects.create(
            collection=self.collection,
            location=self.location,
            x=50.0,
            y=50.0
        )

    @patch.object(LocationManager, 'get_default_location')
    @patch('hi.apps.collection.edit.forms.CollectionPositionForm')
    @patch('hi.apps.common.antinode.response')
    def test_post_valid_position_edit(self, mock_antinode_response, mock_form_class, mock_get_location):
        """Test POST request with valid position data."""
        mock_get_location.return_value = self.location
        
        # Mock valid form
        mock_form = Mock()
        mock_form.is_valid.return_value = True
        mock_form_class.return_value = mock_form
        
        mock_antinode_response.return_value = 'success_response'

        url = reverse('collection_position_edit', kwargs={'collection_id': self.collection.id})
        _ = self.client.post(url, {
            'x': '60.0',
            'y': '70.0'
        })

        mock_form.save.assert_called_once()
        mock_antinode_response.assert_called_once()

    @patch.object(LocationManager, 'get_default_location')
    @patch('hi.apps.collection.edit.forms.CollectionPositionForm')
    def test_post_invalid_position_edit(self, mock_form_class, mock_get_location):
        """Test POST request with invalid position data."""
        mock_get_location.return_value = self.location
        
        # Mock invalid form
        mock_form = Mock()
        mock_form.is_valid.return_value = False
        mock_form_class.return_value = mock_form

        url = reverse('collection_position_edit', kwargs={'collection_id': self.collection.id})
        response = self.client.post(url, {
            'x': 'invalid',
            'y': 'invalid'
        })

        # Should still return success but log warning
        self.assertSuccessResponse(response)
        mock_form.save.assert_not_called()

    @patch.object(LocationManager, 'get_default_location')
    def test_post_nonexistent_position(self, mock_get_location):
        """Test POST request for nonexistent collection position."""
        mock_get_location.return_value = self.location
        
        # Create collection without position
        other_collection = Collection.objects.create(
            name='Other Collection',
            collection_type_str='GROUP',
            collection_view_type_str='MAIN'
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
            collection_type_str='ROOM',
            collection_view_type_str='MAIN'
        )

    @patch.object(CollectionManager, 'get_default_collection')
    @patch.object(CollectionManager, 'create_entity_collection_group_list')
    def test_get_manage_items_view(self, mock_create_group_list, mock_get_default):
        """Test getting collection manage items view."""
        mock_get_default.return_value = self.collection
        mock_group_list = ['group1', 'group2']
        mock_create_group_list.return_value = mock_group_list

        url = reverse('collection_manage_items')
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        self.assertHtmlResponse(response)
        self.assertTemplateRendered(response, 'collection/edit/panes/collection_manage_items.html')
        
        self.assertEqual(response.context['entity_collection_group_list'], mock_group_list)
        mock_create_group_list.assert_called_once_with(collection=self.collection)

    def test_post_not_allowed(self):
        """Test that POST requests are not allowed."""
        url = reverse('collection_manage_items')
        response = self.client.post(url)

        self.assertEqual(response.status_code, 405)


class TestCollectionReorderEntitiesView(SyncViewTestCase):
    """
    Tests for CollectionReorderEntitiesView - demonstrates entity reordering testing.
    This view handles reordering entities within a collection.
    """

    def setUp(self):
        super().setUp()
        # Set edit mode (required by decorator)
        self.setSessionViewMode(ViewMode.EDIT)
        
        # Create test collection and entities
        self.collection = Collection.objects.create(
            name='Test Collection',
            collection_type_str='ROOM',
            collection_view_type_str='MAIN'
        )
        self.entity1 = Entity.objects.create(
            name='Entity 1',
            entity_type_str='LIGHT'
        )
        self.entity2 = Entity.objects.create(
            name='Entity 2',
            entity_type_str='SWITCH'
        )

    @patch.object(CollectionManager, 'set_collection_entity_order')
    @patch('hi.apps.common.antinode.response')
    def test_post_valid_entity_reorder(self, mock_antinode_response, mock_set_order):
        """Test POST request with valid entity reorder data."""
        mock_antinode_response.return_value = 'success_response'
        
        entity_id_list = [self.entity2.id, self.entity1.id]
        url = reverse('collection_reorder_entities', kwargs={
            'collection_id': self.collection.id,
            'entity_id_list': json.dumps(entity_id_list)
        })
        _ = self.client.post(url)

        mock_set_order.assert_called_once_with(
            collection=self.collection,
            entity_id_list=entity_id_list
        )
        mock_antinode_response.assert_called_once_with(main_content='OK')

    def test_post_invalid_json(self):
        """Test POST request with invalid JSON data."""
        url = reverse('collection_reorder_entities', kwargs={
            'collection_id': self.collection.id,
            'entity_id_list': 'invalid-json'
        })
        response = self.client.post(url)

        self.assertEqual(response.status_code, 400)

    def test_post_empty_entity_list(self):
        """Test POST request with empty entity list."""
        url = reverse('collection_reorder_entities', kwargs={
            'collection_id': self.collection.id,
            'entity_id_list': json.dumps([])
        })
        response = self.client.post(url)

        self.assertEqual(response.status_code, 400)

    def test_nonexistent_collection_returns_404(self):
        """Test that accessing nonexistent collection returns 404."""
        url = reverse('collection_reorder_entities', kwargs={
            'collection_id': 99999,
            'entity_id_list': json.dumps([1, 2])
        })
        response = self.client.post(url)

        self.assertEqual(response.status_code, 404)

    def test_get_not_allowed(self):
        """Test that GET requests are not allowed."""
        url = reverse('collection_reorder_entities', kwargs={
            'collection_id': self.collection.id,
            'entity_id_list': json.dumps([1, 2])
        })
        response = self.client.get(url)

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
            collection_type_str='ROOM',
            collection_view_type_str='MAIN'
        )
        self.entity = Entity.objects.create(
            name='Test Entity',
            entity_type_str='LIGHT'
        )

    @patch.object(CollectionManager, 'get_collection_data')
    @patch.object(CollectionManager, 'toggle_entity_in_collection')
    @patch('hi.apps.common.antinode.response')
    def test_post_toggle_entity_add(self, mock_antinode_response, mock_toggle, mock_get_data):
        """Test POST request to add entity to collection."""
        # Mock entity being added (returns True)
        mock_toggle.return_value = True
        
        # Mock collection data
        mock_collection_data = Mock()
        mock_collection_data.to_template_context.return_value = {'collection': self.collection}
        mock_get_data.return_value = mock_collection_data
        
        mock_antinode_response.return_value = 'success_response'

        url = reverse('collection_entity_toggle', kwargs={
            'collection_id': self.collection.id,
            'entity_id': self.entity.id
        })
        _ = self.client.post(url)

        mock_toggle.assert_called_once_with(
            entity=self.entity,
            collection=self.collection
        )
        mock_get_data.assert_called_once_with(
            collection=self.collection,
            is_editing=True
        )
        mock_antinode_response.assert_called_once()

    @patch.object(CollectionManager, 'get_collection_data')
    @patch.object(CollectionManager, 'toggle_entity_in_collection')
    @patch('hi.apps.common.antinode.response')
    def test_post_toggle_entity_remove(self, mock_antinode_response, mock_toggle, mock_get_data):
        """Test POST request to remove entity from collection."""
        # Mock entity being removed (returns False)
        mock_toggle.return_value = False
        
        # Mock collection data
        mock_collection_data = Mock()
        mock_collection_data.to_template_context.return_value = {'collection': self.collection}
        mock_get_data.return_value = mock_collection_data
        
        mock_antinode_response.return_value = 'success_response'

        url = reverse('collection_entity_toggle', kwargs={
            'collection_id': self.collection.id,
            'entity_id': self.entity.id
        })
        _ = self.client.post(url)

        mock_toggle.assert_called_once_with(
            entity=self.entity,
            collection=self.collection
        )

    def test_nonexistent_collection_returns_404(self):
        """Test that accessing nonexistent collection returns 404."""
        url = reverse('collection_entity_toggle', kwargs={
            'collection_id': 99999,
            'entity_id': self.entity.id
        })
        response = self.client.post(url)

        self.assertEqual(response.status_code, 404)

    def test_nonexistent_entity_returns_404(self):
        """Test that accessing nonexistent entity returns 404."""
        url = reverse('collection_entity_toggle', kwargs={
            'collection_id': self.collection.id,
            'entity_id': 99999
        })
        response = self.client.post(url)

        self.assertEqual(response.status_code, 404)

    def test_get_not_allowed(self):
        """Test that GET requests are not allowed."""
        url = reverse('collection_entity_toggle', kwargs={
            'collection_id': self.collection.id,
            'entity_id': self.entity.id
        })
        response = self.client.get(url)

        self.assertEqual(response.status_code, 405)
        
