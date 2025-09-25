import logging
from unittest.mock import patch

from django.urls import reverse

from hi.apps.collection.collection_manager import CollectionManager
from hi.apps.collection.models import Collection, CollectionEntity
from hi.apps.entity.models import Entity
from hi.apps.location.models import Location, LocationView
from hi.enums import ViewType
from hi.testing.view_test_base import SyncViewTestCase, DualModeViewTestCase

logging.disable(logging.CRITICAL)


class TestCollectionViewDefaultView(SyncViewTestCase):
    """
    Tests for CollectionViewDefaultView - demonstrates redirect view testing.
    This view redirects to the default collection view.
    """

    def setUp(self):
        super().setUp()
        # Create test location and collection
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

    @patch.object(CollectionManager, 'get_default_collection')
    def test_redirects_to_default_collection(self, mock_get_default):
        """Test that view redirects to default collection."""
        mock_get_default.return_value = self.collection

        url = reverse('collection_view_default')
        response = self.client.get(url)

        expected_url = reverse('collection_view', kwargs={'collection_id': self.collection.id})
        self.assertRedirects(response, expected_url, fetch_redirect_response=False)

    @patch.object(CollectionManager, 'get_default_collection')
    def test_sets_view_parameters_in_session(self, mock_get_default):
        """Test that view parameters are set correctly in session."""
        mock_get_default.return_value = self.collection

        url = reverse('collection_view_default')
        _ = self.client.get(url)

        # Check session values
        session = self.client.session
        self.assertEqual(session.get('view_type'), str(ViewType.COLLECTION))
        self.assertEqual(session.get('collection_id'), self.collection.id)

    @patch.object(CollectionManager, 'get_default_collection')
    def test_raises_bad_request_when_no_collections(self, mock_get_default):
        """Test that BadRequest is raised when no collections exist."""
        mock_get_default.side_effect = Collection.DoesNotExist()

        url = reverse('collection_view_default')
        response = self.client.get(url)

        # BadRequest should result in 400 status
        self.assertEqual(response.status_code, 400)


class TestCollectionViewView(DualModeViewTestCase):
    """
    Tests for CollectionViewView - demonstrates HiGridView testing.
    This view displays a collection in both sync and async modes.
    """

    def setUp(self):
        super().setUp()
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
        # Create some entities in the collection
        self.entity1 = Entity.objects.create(
            name='Entity 1',
            entity_type_str='LIGHT'
        )
        self.entity2 = Entity.objects.create(
            name='Entity 2',
            entity_type_str='SWITCH'
        )
        # Create collection-entity relationships
        CollectionEntity.objects.create(
            collection=self.collection,
            entity=self.entity1,
            order_id=1
        )
        CollectionEntity.objects.create(
            collection=self.collection,
            entity=self.entity2,
            order_id=2
        )

    def test_get_collection_view_sync(self):
        """Test getting collection view with synchronous request."""
        url = reverse('collection_view', kwargs={'collection_id': self.collection.id})
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        self.assertHtmlResponse(response)
        self.assertTemplateRendered(response, 'collection/panes/collection_view.html')

    def test_get_collection_view_async(self):
        """Test getting collection view with AJAX request."""
        url = reverse('collection_view', kwargs={'collection_id': self.collection.id})
        response = self.async_get(url)

        self.assertSuccessResponse(response)
        self.assertJsonResponse(response)
        
        # HiGridView returns JSON with insert and pushUrl for AJAX requests
        data = response.json()
        self.assertIn('insert', data)  # Contains the main content
        self.assertIn('pushUrl', data)  # Contains the URL for browser history

    def test_updates_session_view_parameters(self):
        """Test that accessing collection updates session view parameters."""
        url = reverse('collection_view', kwargs={'collection_id': self.collection.id})
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        
        # Check session was updated
        session = self.client.session
        self.assertEqual(session.get('view_type'), str(ViewType.COLLECTION))
        self.assertEqual(session.get('collection_id'), self.collection.id)

    def test_nonexistent_collection_returns_404(self):
        """Test that accessing nonexistent collection returns 404."""
        url = reverse('collection_view', kwargs={'collection_id': 99999})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)


class TestCollectionDetailsView(DualModeViewTestCase):
    """
    Tests for CollectionDetailsView - demonstrates HiSideView testing.
    This view displays collection details in the side panel.
    """

    def setUp(self):
        super().setUp()
        # Create test data
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
        self.collection = Collection.objects.create(
            name='Test Collection',
            collection_type_str='ROOM',
            collection_view_type_str='MAIN'
        )

    def test_get_collection_edit_mode_sync(self):
        """Test getting collection edit mode with synchronous request."""
        url = reverse('collection_edit_mode', kwargs={'collection_id': self.collection.id})
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        self.assertJsonResponse(response)  # HiSideView always returns JSON with antinode response
        
        # Check that response contains insert_map
        data = response.json()
        self.assertIn('insert', data)

    def test_get_collection_edit_mode_async(self):
        """Test getting collection edit mode with AJAX request."""
        url = reverse('collection_edit_mode', kwargs={'collection_id': self.collection.id})
        response = self.async_get(url)

        self.assertSuccessResponse(response)
        self.assertJsonResponse(response)
        
        # HiSideView returns JSON with antinode response
        data = response.json()
        self.assertIn('insert', data)

    def test_includes_location_view_when_in_location_context(self):
        """Test that location view is included when viewing from location context."""
        # Set session to location view type
        self.setSessionViewType(ViewType.LOCATION_VIEW)
        self.setSessionLocationView(self.location_view)

        url = reverse('collection_edit_mode', kwargs={'collection_id': self.collection.id})
        response = self.client.get(url)

        self.assertSuccessResponse(response)

    def test_handles_collection_without_location_context(self):
        """Test that view works without location context."""
        # Set session to collection view type
        self.setSessionViewType(ViewType.COLLECTION)

        url = reverse('collection_edit_mode', kwargs={'collection_id': self.collection.id})
        response = self.client.get(url)

        self.assertSuccessResponse(response)

    def test_nonexistent_collection_returns_404(self):
        """Test that accessing nonexistent collection returns 404."""
        url = reverse('collection_edit_mode', kwargs={'collection_id': 99999})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)


