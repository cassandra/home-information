import logging
from unittest.mock import Mock, patch

from django.urls import reverse

from hi.apps.event.models import EventDefinition
from hi.tests.view_test_base import DualModeViewTestCase

logging.disable(logging.CRITICAL)


class TestEventDefinitionEditView(DualModeViewTestCase):
    """
    Tests for EventDefinitionEditView - demonstrates complex form editing testing.
    This view handles editing event definitions with multiple formsets.
    """

    def setUp(self):
        super().setUp()
        # Create test event definition
        self.event_definition = EventDefinition.objects.create(
            name='Test Event',
            description='Test event definition'
        )

    @patch('hi.apps.event.edit.forms.EventDefinitionForm')
    @patch('hi.apps.event.edit.forms.EventClauseFormSet')
    @patch('hi.apps.event.edit.forms.AlarmActionFormSet')
    @patch('hi.apps.event.edit.forms.ControlActionFormSet')
    def test_get_event_definition_edit(self, mock_control_formset, mock_alarm_formset, 
                                       mock_clause_formset, mock_definition_form):
        """Test getting event definition edit form."""
        # Mock forms
        mock_definition_form.return_value = Mock()
        mock_clause_formset.return_value = Mock()
        mock_alarm_formset.return_value = Mock()
        mock_control_formset.return_value = Mock()

        url = reverse('event_definition_edit', kwargs={'event_definition_id': self.event_definition.id})
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        self.assertHtmlResponse(response)
        self.assertTemplateRendered(response, 'event/edit/modals/event_definition_edit.html')
        
        # Should create forms with event definition instance
        mock_definition_form.assert_called_once_with(instance=self.event_definition)
        mock_clause_formset.assert_called_once()
        mock_alarm_formset.assert_called_once()
        mock_control_formset.assert_called_once()

    @patch('hi.apps.event.edit.forms.EventDefinitionForm')
    @patch('hi.apps.event.edit.forms.EventClauseFormSet')
    @patch('hi.apps.event.edit.forms.AlarmActionFormSet')
    @patch('hi.apps.event.edit.forms.ControlActionFormSet')
    def test_get_event_definition_edit_async(self, mock_control_formset, mock_alarm_formset,
                                             mock_clause_formset, mock_definition_form):
        """Test getting event definition edit form with AJAX request."""
        # Mock forms
        mock_definition_form.return_value = Mock()
        mock_clause_formset.return_value = Mock()
        mock_alarm_formset.return_value = Mock()
        mock_control_formset.return_value = Mock()

        url = reverse('event_definition_edit', kwargs={'event_definition_id': self.event_definition.id})
        response = self.async_get(url)

        self.assertSuccessResponse(response)
        self.assertJsonResponse(response)
        
        # HiModalView returns JSON with modal content for AJAX requests
        data = response.json()
        self.assertIn('modal', data)

    @patch('hi.apps.event.edit.views.EventDefinitionEditView.event_manager')
    @patch('hi.apps.event.edit.forms.EventDefinitionForm')
    @patch('hi.apps.event.edit.forms.EventClauseFormSet')
    @patch('hi.apps.event.edit.forms.AlarmActionFormSet')
    @patch('hi.apps.event.edit.forms.ControlActionFormSet')
    def test_post_valid_event_definition_edit(self, mock_control_formset, mock_alarm_formset,
                                              mock_clause_formset, mock_definition_form, mock_event_manager):
        """Test POST request with valid event definition data."""
        # Mock valid forms
        mock_def_form = Mock()
        mock_def_form.is_valid.return_value = True
        mock_def_form.save.return_value = self.event_definition
        mock_definition_form.return_value = mock_def_form

        mock_clause_fs = Mock()
        mock_clause_fs.is_valid.return_value = True
        mock_clause_fs.has_at_least_one = True
        mock_clause_formset.return_value = mock_clause_fs

        mock_alarm_fs = Mock()
        mock_alarm_fs.is_valid.return_value = True
        mock_alarm_fs.has_at_least_one = True
        mock_alarm_formset.return_value = mock_alarm_fs

        mock_control_fs = Mock()
        mock_control_fs.is_valid.return_value = True
        mock_control_fs.has_at_least_one = False
        mock_control_formset.return_value = mock_control_fs

        # Mock event manager
        mock_manager = Mock()
        mock_event_manager.return_value = mock_manager

        url = reverse('event_definition_edit', kwargs={'event_definition_id': self.event_definition.id})
        response = self.client.post(url, {
            'name': 'Updated Event',
            'description': 'Updated description'
        })

        self.assertEqual(response.status_code, 302)
        expected_url = reverse('event_definitions')
        self.assertEqual(response.url, expected_url)
        
        # Should save all forms and reload event manager
        mock_def_form.save.assert_called_once()
        mock_clause_fs.save.assert_called_once()
        mock_alarm_fs.save.assert_called_once()
        mock_control_fs.save.assert_called_once()
        mock_manager.reload.assert_called_once()

    @patch('hi.apps.event.edit.forms.EventDefinitionForm')
    @patch('hi.apps.event.edit.forms.EventClauseFormSet')
    @patch('hi.apps.event.edit.forms.AlarmActionFormSet')
    @patch('hi.apps.event.edit.forms.ControlActionFormSet')
    def test_post_invalid_form_data(self, mock_control_formset, mock_alarm_formset,
                                    mock_clause_formset, mock_definition_form):
        """Test POST request with invalid form data."""
        # Mock invalid forms
        mock_def_form = Mock()
        mock_def_form.is_valid.return_value = False
        mock_definition_form.return_value = mock_def_form

        mock_clause_fs = Mock()
        mock_clause_fs.is_valid.return_value = True
        mock_clause_fs.has_at_least_one = True
        mock_clause_formset.return_value = mock_clause_fs

        mock_alarm_fs = Mock()
        mock_alarm_fs.is_valid.return_value = True
        mock_alarm_fs.has_at_least_one = True
        mock_alarm_formset.return_value = mock_alarm_fs

        mock_control_fs = Mock()
        mock_control_fs.is_valid.return_value = True
        mock_control_fs.has_at_least_one = False
        mock_control_formset.return_value = mock_control_fs

        url = reverse('event_definition_edit', kwargs={'event_definition_id': self.event_definition.id})
        response = self.client.post(url, {})

        self.assertSuccessResponse(response)
        # Should render form with errors
        self.assertEqual(response.context['event_definition_form'], mock_def_form)

    @patch('hi.apps.event.edit.forms.EventDefinitionForm')
    @patch('hi.apps.event.edit.forms.EventClauseFormSet')
    @patch('hi.apps.event.edit.forms.AlarmActionFormSet')
    @patch('hi.apps.event.edit.forms.ControlActionFormSet')
    def test_post_no_event_clauses(self, mock_control_formset, mock_alarm_formset,
                                   mock_clause_formset, mock_definition_form):
        """Test POST request with no event clauses."""
        # Mock forms with no event clauses
        mock_def_form = Mock()
        mock_def_form.is_valid.return_value = True
        mock_definition_form.return_value = mock_def_form

        mock_clause_fs = Mock()
        mock_clause_fs.is_valid.return_value = True
        mock_clause_fs.has_at_least_one = False  # No clauses
        mock_clause_formset.return_value = mock_clause_fs

        mock_alarm_fs = Mock()
        mock_alarm_fs.is_valid.return_value = True
        mock_alarm_fs.has_at_least_one = True
        mock_alarm_formset.return_value = mock_alarm_fs

        mock_control_fs = Mock()
        mock_control_fs.is_valid.return_value = True
        mock_control_fs.has_at_least_one = False
        mock_control_formset.return_value = mock_control_fs

        url = reverse('event_definition_edit', kwargs={'event_definition_id': self.event_definition.id})
        response = self.client.post(url, {})

        self.assertSuccessResponse(response)
        # Should add error to definition form
        mock_def_form.add_error.assert_called_with(None, 'Must have at least one event clause.')

    @patch('hi.apps.event.edit.forms.EventDefinitionForm')
    @patch('hi.apps.event.edit.forms.EventClauseFormSet')
    @patch('hi.apps.event.edit.forms.AlarmActionFormSet')
    @patch('hi.apps.event.edit.forms.ControlActionFormSet')
    def test_post_no_actions(self, mock_control_formset, mock_alarm_formset,
                             mock_clause_formset, mock_definition_form):
        """Test POST request with no alarm or control actions."""
        # Mock forms with no actions
        mock_def_form = Mock()
        mock_def_form.is_valid.return_value = True
        mock_definition_form.return_value = mock_def_form

        mock_clause_fs = Mock()
        mock_clause_fs.is_valid.return_value = True
        mock_clause_fs.has_at_least_one = True
        mock_clause_formset.return_value = mock_clause_fs

        mock_alarm_fs = Mock()
        mock_alarm_fs.is_valid.return_value = True
        mock_alarm_fs.has_at_least_one = False  # No alarm actions
        mock_alarm_formset.return_value = mock_alarm_fs

        mock_control_fs = Mock()
        mock_control_fs.is_valid.return_value = True
        mock_control_fs.has_at_least_one = False  # No control actions
        mock_control_formset.return_value = mock_control_fs

        url = reverse('event_definition_edit', kwargs={'event_definition_id': self.event_definition.id})
        response = self.client.post(url, {})

        self.assertSuccessResponse(response)
        # Should add error to definition form
        mock_def_form.add_error.assert_called_with(None, 'Must have either alarm of control action.')

    def test_nonexistent_event_definition_returns_404(self):
        """Test that accessing nonexistent event definition returns 404."""
        url = reverse('event_definition_edit', kwargs={'event_definition_id': 99999})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)


class TestEventDefinitionAddView(DualModeViewTestCase):
    """
    Tests for EventDefinitionAddView - demonstrates event definition creation testing.
    This view inherits from EventDefinitionEditView but creates new event definitions.
    """

    @patch('hi.apps.event.edit.forms.EventDefinitionForm')
    @patch('hi.apps.event.edit.forms.EventClauseFormSet')
    @patch('hi.apps.event.edit.forms.AlarmActionFormSet')
    @patch('hi.apps.event.edit.forms.ControlActionFormSet')
    def test_get_event_definition_add(self, mock_control_formset, mock_alarm_formset,
                                      mock_clause_formset, mock_definition_form):
        """Test getting event definition add form."""
        # Mock forms
        mock_definition_form.return_value = Mock()
        mock_clause_formset.return_value = Mock()
        mock_alarm_formset.return_value = Mock()
        mock_control_formset.return_value = Mock()

        url = reverse('event_definition_add')
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        self.assertHtmlResponse(response)
        self.assertTemplateRendered(response, 'event/edit/modals/event_definition_add.html')
        
        # Should create forms with no instance (None)
        mock_definition_form.assert_called_once_with(instance=None)

    @patch('hi.apps.event.edit.forms.EventDefinitionForm')
    @patch('hi.apps.event.edit.forms.EventClauseFormSet')
    @patch('hi.apps.event.edit.forms.AlarmActionFormSet')
    @patch('hi.apps.event.edit.forms.ControlActionFormSet')
    def test_get_event_definition_add_async(self, mock_control_formset, mock_alarm_formset,
                                            mock_clause_formset, mock_definition_form):
        """Test getting event definition add form with AJAX request."""
        # Mock forms
        mock_definition_form.return_value = Mock()
        mock_clause_formset.return_value = Mock()
        mock_alarm_formset.return_value = Mock()
        mock_control_formset.return_value = Mock()

        url = reverse('event_definition_add')
        response = self.async_get(url)

        self.assertSuccessResponse(response)
        self.assertJsonResponse(response)
        
        # HiModalView returns JSON with modal content for AJAX requests
        data = response.json()
        self.assertIn('modal', data)

    @patch('hi.apps.event.edit.views.EventDefinitionEditView.event_manager')
    @patch('hi.apps.event.edit.forms.EventDefinitionForm')
    @patch('hi.apps.event.edit.forms.EventClauseFormSet')
    @patch('hi.apps.event.edit.forms.AlarmActionFormSet')
    @patch('hi.apps.event.edit.forms.ControlActionFormSet')
    def test_post_valid_event_definition_add(self, mock_control_formset, mock_alarm_formset,
                                             mock_clause_formset, mock_definition_form, mock_event_manager):
        """Test POST request to create new event definition."""
        # Create new event definition for saving
        new_event_definition = EventDefinition.objects.create(
            name='New Event',
            description='New event definition'
        )

        # Mock valid forms
        mock_def_form = Mock()
        mock_def_form.is_valid.return_value = True
        mock_def_form.save.return_value = new_event_definition
        mock_definition_form.return_value = mock_def_form

        mock_clause_fs = Mock()
        mock_clause_fs.is_valid.return_value = True
        mock_clause_fs.has_at_least_one = True
        mock_clause_formset.return_value = mock_clause_fs

        mock_alarm_fs = Mock()
        mock_alarm_fs.is_valid.return_value = True
        mock_alarm_fs.has_at_least_one = True
        mock_alarm_formset.return_value = mock_alarm_fs

        mock_control_fs = Mock()
        mock_control_fs.is_valid.return_value = True
        mock_control_fs.has_at_least_one = False
        mock_control_formset.return_value = mock_control_fs

        # Mock event manager
        mock_manager = Mock()
        mock_event_manager.return_value = mock_manager

        url = reverse('event_definition_add')
        response = self.client.post(url, {
            'name': 'New Event',
            'description': 'New event description'
        })

        self.assertEqual(response.status_code, 302)
        expected_url = reverse('event_definitions')
        self.assertEqual(response.url, expected_url)
        
        # Should save all forms and reload event manager
        mock_def_form.save.assert_called_once()
        mock_clause_fs.save.assert_called_once()
        mock_alarm_fs.save.assert_called_once()
        mock_control_fs.save.assert_called_once()
        mock_manager.reload.assert_called_once()

    def test_get_event_definition_returns_none(self):
        """Test that get_event_definition returns None for add view."""
        from hi.apps.event.edit.views import EventDefinitionAddView
        view = EventDefinitionAddView()
        
        # Should return None since we're adding, not editing
        result = view.get_event_definition(None)
        self.assertIsNone(result)


class TestEventDefinitionDeleteView(DualModeViewTestCase):
    """
    Tests for EventDefinitionDeleteView - demonstrates event definition deletion testing.
    This view handles deleting event definitions.
    """

    def setUp(self):
        super().setUp()
        # Create test event definition
        self.event_definition = EventDefinition.objects.create(
            name='Test Event',
            description='Test event to delete'
        )

    def test_get_event_definition_delete(self):
        """Test getting event definition delete confirmation."""
        url = reverse('event_definition_delete', kwargs={'event_definition_id': self.event_definition.id})
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        self.assertHtmlResponse(response)
        self.assertTemplateRendered(response, 'event/edit/modals/event_definition_delete.html')
        self.assertEqual(response.context['event_definition'], self.event_definition)

    def test_get_event_definition_delete_async(self):
        """Test getting event definition delete confirmation with AJAX request."""
        url = reverse('event_definition_delete', kwargs={'event_definition_id': self.event_definition.id})
        response = self.async_get(url)

        self.assertSuccessResponse(response)
        self.assertJsonResponse(response)
        
        # HiModalView returns JSON with modal content for AJAX requests
        data = response.json()
        self.assertIn('modal', data)

    @patch('hi.apps.event.edit.views.EventDefinitionDeleteView.event_manager')
    def test_post_event_definition_delete(self, mock_event_manager):
        """Test POST request to delete event definition."""
        # Mock event manager
        mock_manager = Mock()
        mock_event_manager.return_value = mock_manager

        url = reverse('event_definition_delete', kwargs={'event_definition_id': self.event_definition.id})
        response = self.client.post(url)

        self.assertEqual(response.status_code, 302)
        expected_url = reverse('event_definitions')
        self.assertEqual(response.url, expected_url)
        
        # Event definition should be deleted
        with self.assertRaises(EventDefinition.DoesNotExist):
            EventDefinition.objects.get(id=self.event_definition.id)
        
        # Should reload event manager
        mock_manager.reload.assert_called_once()

    def test_nonexistent_event_definition_returns_404(self):
        """Test that accessing nonexistent event definition returns 404."""
        url = reverse('event_definition_delete', kwargs={'event_definition_id': 99999})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)

    def test_post_nonexistent_event_definition_returns_404(self):
        """Test that deleting nonexistent event definition returns 404."""
        url = reverse('event_definition_delete', kwargs={'event_definition_id': 99999})
        response = self.client.post(url)

        self.assertEqual(response.status_code, 404)
        
