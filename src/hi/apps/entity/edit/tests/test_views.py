import logging
from unittest.mock import Mock, patch

from django.core.exceptions import PermissionDenied
from django.urls import reverse

from hi.apps.collection.collection_manager import CollectionManager
from hi.apps.collection.models import Collection
from hi.apps.entity.edit.views import ManagePairingsView
from hi.apps.entity.entity_manager import EntityManager
from hi.apps.entity.entity_pairing_manager import EntityPairingManager
from hi.apps.entity.models import Entity, EntityPosition
from hi.apps.location.location_manager import LocationManager
from hi.apps.location.models import Location, LocationView
from hi.enums import ViewMode, ViewType
from hi.testing.view_test_base import SyncViewTestCase, DualModeViewTestCase

logging.disable(logging.CRITICAL)


class TestEntityAddView(DualModeViewTestCase):
    """
    Tests for EntityAddView - demonstrates entity creation testing.
    This view handles adding new entities with automatic view integration.
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
        # Create test collection
        self.collection = Collection.objects.create(
            name='Test Collection',
            collection_type_str='ROOM',
            collection_view_type_str='MAIN'
        )

    def test_get_entity_add_form(self):
        """Test getting entity add form."""
        url = reverse('entity_edit_entity_add')
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        self.assertHtmlResponse(response)
        self.assertTemplateRendered(response, 'entity/edit/modals/entity_add.html')
        self.assertIn('entity_form', response.context)

    def test_get_entity_add_form_async(self):
        """Test getting entity add form with AJAX request."""
        url = reverse('entity_edit_entity_add')
        response = self.async_get(url)

        self.assertSuccessResponse(response)
        self.assertJsonResponse(response)
        
        # HiModalView returns JSON with modal content for AJAX requests
        data = response.json()
        self.assertIn('modal', data)

    def test_post_invalid_form(self):
        """Test POST request with invalid form data."""
        # Submit form with missing required fields
        form_data = {
            'name': '',  # Required field is empty
            # Missing entity_type_str (required)
        }

        url = reverse('entity_edit_entity_add')
        response = self.client.post(url, form_data)

        # Should return success with form errors (not redirect)
        self.assertSuccessResponse(response)
        self.assertHtmlResponse(response)
        
        # Test that form errors are present in context
        self.assertIn('entity_form', response.context)
        form = response.context['entity_form']
        self.assertFalse(form.is_valid())
        
        # Should have validation errors for required fields
        self.assertTrue(form.errors)
        self.assertIn('name', form.errors)
        self.assertIn('entity_type_str', form.errors)
        
        # Verify no Entity was created with invalid data
        self.assertFalse(Entity.objects.filter(name='').exists())

    def test_post_valid_form_location_view(self):
        """Test POST request with valid form data in location view context."""
        # Set location view context
        self.setSessionViewType(ViewType.LOCATION_VIEW)
        
        # Create comprehensive form data for new entity
        form_data = {
            'name': 'Test Entity',
            'entity_type_str': 'light'
        }

        # Count existing entities before
        initial_entity_count = Entity.objects.count()
        initial_position_count = EntityPosition.objects.count()

        url = reverse('entity_edit_entity_add')
        response = self.client.post(url, form_data)

        # Test actual redirect behavior (JSON redirect)
        self.assertSuccessResponse(response)
        self.assertJsonResponse(response)
        
        data = response.json()
        expected_url = reverse('home')
        self.assertEqual(data['location'], expected_url)
        
        # Test that new Entity was created
        self.assertEqual(Entity.objects.count(), initial_entity_count + 1)
        
        # Get the newly created entity
        new_entity = Entity.objects.get(name='Test Entity')
        self.assertEqual(new_entity.entity_type_str, 'light')
        
        # Test that entity was added to the location view (EntityPosition created)
        # The real managers should handle this integration
        self.assertEqual(EntityPosition.objects.count(), initial_position_count + 1)
        
        # Verify the EntityPosition links the entity to the location
        entity_position = EntityPosition.objects.get(entity=new_entity)
        self.assertEqual(entity_position.location, self.location_view.location)

    @patch.object(CollectionManager, 'add_entity_to_collection')
    @patch.object(CollectionManager, 'get_default_collection')
    @patch('hi.apps.entity.forms.EntityForm')
    def test_post_valid_form_collection_view(self, mock_form_class, mock_get_collection,
                                             mock_add_to_collection):
        """Test POST request with valid form data in collection view context."""
        # Set collection view context
        self.setSessionViewType(ViewType.COLLECTION)
        
        # Mock valid form
        mock_form = Mock()
        mock_form.is_valid.return_value = True
        mock_entity = Mock()
        mock_form.save.return_value = mock_entity
        mock_form_class.return_value = mock_form

        # Mock collection manager
        mock_get_collection.return_value = self.collection

        url = reverse('entity_edit_entity_add')
        response = self.client.post(url, {
            'name': 'Test Entity',
            'entity_type_str': 'SWITCH'
        })

        self.assertEqual(response.status_code, 302)
        expected_url = reverse('home')
        self.assertEqual(response.url, expected_url)
        
        # Should add entity to collection
        mock_add_to_collection.assert_called_once_with(
            entity=mock_entity,
            collection=self.collection
        )

    @patch('hi.apps.entity.forms.EntityForm')
    def test_post_valid_form_other_view_type(self, mock_form_class):
        """Test POST request with valid form data in other view type context."""
        # Set other view type context
        self.setSessionViewType(ViewType.CONFIGURATION)
        
        # Mock valid form
        mock_form = Mock()
        mock_form.is_valid.return_value = True
        mock_entity = Mock()
        mock_form.save.return_value = mock_entity
        mock_form_class.return_value = mock_form

        url = reverse('entity_edit_entity_add')
        response = self.client.post(url, {
            'name': 'Test Entity',
            'entity_type_str': 'SENSOR'
        })

        self.assertEqual(response.status_code, 302)
        expected_url = reverse('home')
        self.assertEqual(response.url, expected_url)
        
        # Should not add to any specific view

    @patch.object(LocationManager, 'get_default_location_view')
    @patch('hi.apps.entity.forms.EntityForm')
    def test_post_no_location_view_available(self, mock_form_class, mock_get_location_view):
        """Test POST request when no location view is available."""
        # Set location view context
        self.setSessionViewType(ViewType.LOCATION_VIEW)
        
        # Mock valid form
        mock_form = Mock()
        mock_form.is_valid.return_value = True
        mock_entity = Mock()
        mock_form.save.return_value = mock_entity
        mock_form_class.return_value = mock_form

        # Mock location manager raising exception
        mock_get_location_view.side_effect = LocationView.DoesNotExist()

        url = reverse('entity_edit_entity_add')
        response = self.client.post(url, {'name': 'Test Entity'})

        self.assertEqual(response.status_code, 302)
        # Should handle gracefully and not crash


class TestEntityDeleteView(DualModeViewTestCase):
    """
    Tests for EntityDeleteView - demonstrates entity deletion testing.
    This view handles entity deletion with permission checks.
    """

    def setUp(self):
        super().setUp()
        # Set edit mode (required by decorator)
        self.setSessionViewMode(ViewMode.EDIT)
        
        # Create test entity
        self.entity = Entity.objects.create(
            name='Test Entity',
            entity_type_str='LIGHT'
        )

    def test_get_entity_delete_confirmation(self):
        """Test getting entity delete confirmation."""
        # Mock entity permission
        self.entity.can_user_delete = True

        url = reverse('entity_delete', kwargs={'entity_id': self.entity.id})
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        self.assertHtmlResponse(response)
        self.assertTemplateRendered(response, 'entity/edit/modals/entity_delete.html')
        self.assertEqual(response.context['entity'], self.entity)

    def test_get_entity_delete_async(self):
        """Test getting entity delete confirmation with AJAX request."""
        # Mock entity permission
        self.entity.can_user_delete = True

        url = reverse('entity_delete', kwargs={'entity_id': self.entity.id})
        response = self.async_get(url)

        self.assertSuccessResponse(response)
        self.assertJsonResponse(response)
        
        # HiModalView returns JSON with modal content for AJAX requests
        data = response.json()
        self.assertIn('modal', data)

    def test_get_entity_delete_permission_denied(self):
        """Test getting entity delete when not allowed."""
        # Mock entity permission
        self.entity.can_user_delete = False

        url = reverse('entity_delete', kwargs={'entity_id': self.entity.id})
        
        with self.assertRaises(PermissionDenied):
            _ = self.client.get(url)

    def test_post_delete_without_confirmation(self):
        """Test POST request without confirmation."""
        url = reverse('entity_delete', kwargs={'entity_id': self.entity.id})
        response = self.client.post(url, {})

        self.assertEqual(response.status_code, 400)

    def test_post_delete_with_wrong_confirmation(self):
        """Test POST request with wrong confirmation value."""
        url = reverse('entity_delete', kwargs={'entity_id': self.entity.id})
        response = self.client.post(url, {'action': 'cancel'})

        self.assertEqual(response.status_code, 400)

    def test_post_delete_permission_denied(self):
        """Test POST request when deletion not allowed."""
        # Mock entity permission
        self.entity.can_user_delete = False

        url = reverse('entity_delete', kwargs={'entity_id': self.entity.id})
        
        with self.assertRaises(PermissionDenied):
            _ = self.client.post(url, {'action': 'confirm'})

    def test_post_delete_with_confirmation(self):
        """Test POST request with proper confirmation."""
        # Mock entity permission
        self.entity.can_user_delete = True

        url = reverse('entity_delete', kwargs={'entity_id': self.entity.id})
        response = self.client.post(url, {'action': 'confirm'})

        self.assertEqual(response.status_code, 302)
        expected_url = reverse('home')
        self.assertEqual(response.url, expected_url)
        
        # Entity should be deleted
        with self.assertRaises(Entity.DoesNotExist):
            Entity.objects.get(id=self.entity.id)

    def test_nonexistent_entity_returns_404(self):
        """Test that accessing nonexistent entity returns 404."""
        url = reverse('entity_delete', kwargs={'entity_id': 99999})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)


class TestEntityPositionEditView(SyncViewTestCase):
    """
    Tests for EntityPositionEditView - demonstrates entity position editing testing.
    This view handles updating entity positions on location views.
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
        self.entity = Entity.objects.create(
            name='Test Entity',
            entity_type_str='LIGHT'
        )
        self.entity_position = EntityPosition.objects.create(
            entity=self.entity,
            location=self.location,
            x=50.0,
            y=50.0
        )

    @patch.object(LocationManager, 'get_default_location')
    @patch('hi.apps.entity.edit.forms.EntityPositionForm')
    @patch('hi.apps.common.antinode.response')
    def test_post_valid_position_edit(self, mock_antinode_response, mock_form_class, mock_get_location):
        """Test POST request with valid position data."""
        mock_get_location.return_value = self.location
        
        # Mock valid form
        mock_form = Mock()
        mock_form.is_valid.return_value = True
        mock_form_class.return_value = mock_form
        
        mock_antinode_response.return_value = 'success_response'

        url = reverse('entity_position_edit', kwargs={'entity_id': self.entity.id})
        _ = self.client.post(url, {
            'x': '60.0',
            'y': '70.0'
        })

        mock_form.save.assert_called_once()
        mock_antinode_response.assert_called_once()

    @patch.object(LocationManager, 'get_default_location')
    @patch('hi.apps.entity.edit.forms.EntityPositionForm')
    def test_post_invalid_position_edit(self, mock_form_class, mock_get_location):
        """Test POST request with invalid position data."""
        mock_get_location.return_value = self.location
        
        # Mock invalid form
        mock_form = Mock()
        mock_form.is_valid.return_value = False
        mock_form_class.return_value = mock_form

        url = reverse('entity_position_edit', kwargs={'entity_id': self.entity.id})
        response = self.client.post(url, {
            'x': 'invalid',
            'y': 'invalid'
        })

        # Should still return success but log warning
        self.assertSuccessResponse(response)
        mock_form.save.assert_not_called()

    @patch.object(LocationManager, 'get_default_location')
    def test_post_nonexistent_position(self, mock_get_location):
        """Test POST request for nonexistent entity position."""
        mock_get_location.return_value = self.location
        
        # Create entity without position
        other_entity = Entity.objects.create(
            name='Other Entity',
            entity_type_str='SWITCH'
        )

        url = reverse('entity_position_edit', kwargs={'entity_id': other_entity.id})
        response = self.client.post(url, {})

        self.assertEqual(response.status_code, 404)

    def test_nonexistent_entity_returns_404(self):
        """Test that accessing nonexistent entity returns 404."""
        url = reverse('entity_position_edit', kwargs={'entity_id': 99999})
        response = self.client.post(url, {})

        self.assertEqual(response.status_code, 404)

    def test_get_not_allowed(self):
        """Test that GET requests are not allowed."""
        url = reverse('entity_position_edit', kwargs={'entity_id': self.entity.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 405)


class TestManagePairingsView(DualModeViewTestCase):
    """
    Tests for ManagePairingsView - demonstrates entity pairing management testing.
    This view handles managing entity pairings.
    """

    def setUp(self):
        super().setUp()
        # Set edit mode (required by decorator)
        self.setSessionViewMode(ViewMode.EDIT)
        
        # Create test entities
        self.entity = Entity.objects.create(
            name='Primary Entity',
            entity_type_str='THERMOSTAT'
        )
        self.paired_entity1 = Entity.objects.create(
            name='Paired Entity 1',
            entity_type_str='TEMPERATURE_SENSOR'
        )
        self.paired_entity2 = Entity.objects.create(
            name='Paired Entity 2',
            entity_type_str='HUMIDITY_SENSOR'
        )
        self.candidate_entity = Entity.objects.create(
            name='Candidate Entity',
            entity_type_str='PRESSURE_SENSOR'
        )

    @patch.object(EntityManager, 'create_entity_view_group_list')
    @patch.object(EntityPairingManager, 'get_candidate_entities')
    @patch.object(EntityPairingManager, 'get_entity_pairing_list')
    def test_get_manage_pairings(self, mock_get_pairings, mock_get_candidates, mock_create_groups):
        """Test getting manage pairings view."""
        # Mock pairing data
        mock_pairing1 = Mock()
        mock_pairing1.paired_entity = self.paired_entity1
        mock_pairing2 = Mock()
        mock_pairing2.paired_entity = self.paired_entity2
        mock_get_pairings.return_value = [mock_pairing1, mock_pairing2]
        
        mock_get_candidates.return_value = [self.paired_entity1, self.paired_entity2, self.candidate_entity]
        
        mock_group_list = ['group1', 'group2']
        mock_create_groups.return_value = mock_group_list

        url = reverse('entity_edit_manage_pairings', kwargs={'entity_id': self.entity.id})
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        self.assertHtmlResponse(response)
        self.assertTemplateRendered(response, 'entity/edit/modals/manage_pairings.html')
        
        self.assertEqual(response.context['entity'], self.entity)
        self.assertEqual(response.context['entity_view_group_list'], mock_group_list)
        self.assertEqual(response.context['principal_entity_id_name_prefix'], ManagePairingsView.ENTITY_PAIR_ID_NAME_PREFIX)
        
        # Should call managers with correct data
        mock_get_pairings.assert_called_once_with(entity=self.entity)
        mock_get_candidates.assert_called_once_with(entity=self.entity)
        mock_create_groups.assert_called_once_with(
            existing_entities=[self.paired_entity1, self.paired_entity2],
            all_entities=[self.paired_entity1, self.paired_entity2, self.candidate_entity]
        )

    @patch.object(EntityManager, 'create_entity_view_group_list')
    @patch.object(EntityPairingManager, 'get_candidate_entities')
    @patch.object(EntityPairingManager, 'get_entity_pairing_list')
    def test_get_manage_pairings_async(self, mock_get_pairings, mock_get_candidates, mock_create_groups):
        """Test getting manage pairings view with AJAX request."""
        mock_get_pairings.return_value = []
        mock_get_candidates.return_value = []
        mock_create_groups.return_value = []

        url = reverse('entity_edit_manage_pairings', kwargs={'entity_id': self.entity.id})
        response = self.async_get(url)

        self.assertSuccessResponse(response)
        self.assertJsonResponse(response)
        
        # HiModalView returns JSON with modal content for AJAX requests
        data = response.json()
        self.assertIn('modal', data)

    @patch.object(EntityPairingManager, 'adjust_entity_pairings')
    @patch('hi.apps.common.antinode.refresh_response')
    def test_post_update_pairings_success(self, mock_refresh_response, mock_adjust_pairings):
        """Test POST request to update entity pairings successfully."""
        mock_refresh_response.return_value = 'refresh_response'

        url = reverse('entity_edit_manage_pairings', kwargs={'entity_id': self.entity.id})
        _ = self.client.post(url, {
            f'{ManagePairingsView.ENTITY_PAIR_ID_NAME_PREFIX}{self.paired_entity1.id}': 'on',
            f'{ManagePairingsView.ENTITY_PAIR_ID_NAME_PREFIX}{self.candidate_entity.id}': 'on',
            'other-field': 'ignored'
        })

        # Should call adjust_entity_pairings with correct entity IDs
        mock_adjust_pairings.assert_called_once_with(
            entity=self.entity,
            desired_paired_entity_ids={self.paired_entity1.id, self.candidate_entity.id}
        )
        mock_refresh_response.assert_called_once()

    @patch.object(EntityPairingManager, 'adjust_entity_pairings')
    def test_post_update_pairings_error(self, mock_adjust_pairings):
        """Test POST request to update entity pairings with error."""
        # Mock pairing manager raising error
        mock_adjust_pairings.side_effect = EntityPairingManager.EntityPairingError("Pairing error")

        url = reverse('entity_edit_manage_pairings', kwargs={'entity_id': self.entity.id})
        response = self.client.post(url, {
            f'{ManagePairingsView.ENTITY_PAIR_ID_NAME_PREFIX}{self.paired_entity1.id}': 'on'
        })

        self.assertEqual(response.status_code, 400)

    @patch.object(EntityPairingManager, 'adjust_entity_pairings')
    @patch('hi.apps.common.antinode.refresh_response')
    def test_post_update_pairings_empty_selection(self, mock_refresh_response, mock_adjust_pairings):
        """Test POST request with no paired entities selected."""
        mock_refresh_response.return_value = 'refresh_response'

        url = reverse('entity_edit_manage_pairings', kwargs={'entity_id': self.entity.id})
        _ = self.client.post(url, {
            'other-field': 'value'
        })

        # Should call with empty set
        mock_adjust_pairings.assert_called_once_with(
            entity=self.entity,
            desired_paired_entity_ids=set()
        )

    @patch.object(EntityPairingManager, 'adjust_entity_pairings')
    @patch('hi.apps.common.antinode.refresh_response')
    def test_post_update_pairings_field_parsing(self, mock_refresh_response, mock_adjust_pairings):
        """Test POST request field parsing for entity IDs."""
        mock_refresh_response.return_value = 'refresh_response'

        url = reverse('entity_edit_manage_pairings', kwargs={'entity_id': self.entity.id})
        _ = self.client.post(url, {
            f'{ManagePairingsView.ENTITY_PAIR_ID_NAME_PREFIX}{self.paired_entity1.id}': 'on',
            f'{ManagePairingsView.ENTITY_PAIR_ID_NAME_PREFIX}{self.paired_entity2.id}': 'on',
            'entity-pair-id-invalid': 'on',  # Should be ignored (no number)
            'wrong-prefix-123': 'on',  # Should be ignored (wrong prefix)
            'no-numbers-here': 'on'  # Should be ignored (no match)
        })

        # Should only include valid entity IDs
        mock_adjust_pairings.assert_called_once_with(
            entity=self.entity,
            desired_paired_entity_ids={self.paired_entity1.id, self.paired_entity2.id}
        )

    def test_nonexistent_entity_returns_404(self):
        """Test that accessing nonexistent entity returns 404."""
        url = reverse('entity_edit_manage_pairings', kwargs={'entity_id': 99999})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)
