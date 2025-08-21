import logging
from unittest.mock import Mock, patch

from django.urls import reverse

from hi.apps.event.models import EventDefinition
from hi.apps.entity.models import Entity, EntityState
from hi.apps.control.models import Controller
from hi.testing.view_test_base import DualModeViewTestCase

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
            event_type_str='security',
            event_window_secs=60,
            dedupe_window_secs=300
        )
        
        # Create test entities and states for formsets
        self.test_entity = Entity.objects.create(
            name='Test Entity',
            entity_type_str='switch',
            integration_id='test.entity',
            integration_name='test_integration'
        )
        
        self.test_entity_state = EntityState.objects.create(
            entity=self.test_entity,
            name='Test State',
            entity_state_type_str='on_off',
            value_range_str='on,off'
        )
        
        # Create a controller for control action tests
        self.test_controller = Controller.objects.create(
            name='Test Controller',
            entity_state=self.test_entity_state,
            controller_type_str='switch',
            integration_id='test.controller',
            integration_name='test_integration'
        )

    def test_get_event_definition_edit(self):
        """Test getting event definition edit form."""
        url = reverse('event_definition_edit', kwargs={'id': self.event_definition.id})
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        self.assertHtmlResponse(response)
        self.assertTemplateRendered(response, 'event/edit/modals/event_definition_edit.html')
        
        # Test that real forms are present in response context
        self.assertIn('event_definition_form', response.context)
        self.assertIn('event_clause_formset', response.context)
        self.assertIn('alarm_action_formset', response.context)
        self.assertIn('control_action_formset', response.context)
        self.assertIn('event_definition', response.context)
        
        # Verify form is initialized with correct instance
        form = response.context['event_definition_form']
        self.assertEqual(form.instance, self.event_definition)
        
        # Verify formsets are initialized with correct instance
        clause_formset = response.context['event_clause_formset']
        alarm_formset = response.context['alarm_action_formset']
        control_formset = response.context['control_action_formset']
        self.assertEqual(clause_formset.instance, self.event_definition)
        self.assertEqual(alarm_formset.instance, self.event_definition)
        self.assertEqual(control_formset.instance, self.event_definition)

    def test_get_event_definition_edit_async(self):
        """Test getting event definition edit form with AJAX request."""
        url = reverse('event_definition_edit', kwargs={'id': self.event_definition.id})
        response = self.async_get(url)

        self.assertSuccessResponse(response)
        self.assertJsonResponse(response)
        
        # HiModalView returns JSON with modal content for AJAX requests
        data = response.json()
        self.assertIn('modal', data)

    @patch('hi.apps.event.edit.views.EventDefinitionEditView.event_manager')
    def test_post_valid_event_definition_edit(self, mock_event_manager):
        """Test POST request with valid event definition data."""
        # Mock event manager
        mock_manager = Mock()
        mock_event_manager.return_value = mock_manager

        # Create comprehensive form data with all formsets
        form_data = {
            # Main form fields
            'name': 'Updated Event Name',
            'event_type_str': 'automation',
            'event_window_secs': 120,
            'dedupe_window_secs': 600,
            'enabled': True,
            
            # Event clause formset (required)
            'event-clause-TOTAL_FORMS': '1',
            'event-clause-INITIAL_FORMS': '0',
            'event-clause-MIN_NUM_FORMS': '0',
            'event-clause-MAX_NUM_FORMS': '1000',
            'event-clause-0-entity_state': str(self.test_entity_state.id),
            'event-clause-0-value': 'on',
            
            # Alarm action formset (required to have at least one alarm or control action)
            'alarm-action-TOTAL_FORMS': '1',
            'alarm-action-INITIAL_FORMS': '0',
            'alarm-action-MIN_NUM_FORMS': '0',
            'alarm-action-MAX_NUM_FORMS': '1000',
            'alarm-action-0-security_level_str': 'low',
            'alarm-action-0-alarm_level_str': 'warning',
            'alarm-action-0-alarm_lifetime_secs': 300,
            
            # Control action formset (empty - only one of alarm/control is required)
            'control-action-TOTAL_FORMS': '0',
            'control-action-INITIAL_FORMS': '0',
            'control-action-MIN_NUM_FORMS': '0',
            'control-action-MAX_NUM_FORMS': '1000',
        }

        url = reverse('event_definition_edit', kwargs={'id': self.event_definition.id})
        response = self.client.post(url, form_data)

        # Test actual redirect behavior (JSON redirect)
        self.assertSuccessResponse(response)
        self.assertJsonResponse(response)
        
        data = response.json()
        expected_url = reverse('event_definitions')
        self.assertEqual(data['location'], expected_url)
        
        # Test actual database changes to EventDefinition
        self.event_definition.refresh_from_db()
        self.assertEqual(self.event_definition.name, 'Updated Event Name')
        self.assertEqual(self.event_definition.event_type_str, 'automation')
        self.assertEqual(self.event_definition.event_window_secs, 120)
        self.assertEqual(self.event_definition.dedupe_window_secs, 600)
        
        # Test that formsets were properly saved
        event_clauses = self.event_definition.event_clauses.all()
        self.assertEqual(len(event_clauses), 1)
        self.assertEqual(event_clauses[0].entity_state, self.test_entity_state)
        self.assertEqual(event_clauses[0].value, 'on')
        
        alarm_actions = self.event_definition.alarm_actions.all()
        self.assertEqual(len(alarm_actions), 1)
        self.assertEqual(alarm_actions[0].security_level_str, 'low')
        self.assertEqual(alarm_actions[0].alarm_level_str, 'warning')
        
        # Verify event manager reload was called
        mock_manager.reload.assert_called_once()

    def test_post_invalid_form_data(self):
        """Test POST request with invalid form data."""
        # Submit form with invalid data (missing required fields)
        form_data = {
            # Missing required event_type_str, event_window_secs, dedupe_window_secs
            'name': '',  # Empty name should be invalid
            
            # Event clause formset - still need at least one
            'event-clause-TOTAL_FORMS': '1',
            'event-clause-INITIAL_FORMS': '0',
            'event-clause-MIN_NUM_FORMS': '0',
            'event-clause-MAX_NUM_FORMS': '1000',
            'event-clause-0-entity_state': str(self.test_entity_state.id),
            'event-clause-0-value': 'on',
            
            # Alarm action formset
            'alarm-action-TOTAL_FORMS': '1',
            'alarm-action-INITIAL_FORMS': '0',
            'alarm-action-MIN_NUM_FORMS': '0',
            'alarm-action-MAX_NUM_FORMS': '1000',
            'alarm-action-0-security_level_str': 'low',
            'alarm-action-0-alarm_level_str': 'warning',
            'alarm-action-0-alarm_lifetime_secs': 300,
            
            # Control action formset
            'control-action-TOTAL_FORMS': '0',
            'control-action-INITIAL_FORMS': '0',
            'control-action-MIN_NUM_FORMS': '0',
            'control-action-MAX_NUM_FORMS': '1000',
        }

        url = reverse('event_definition_edit', kwargs={'id': self.event_definition.id})
        response = self.client.post(url, form_data)

        # Should return success with form errors (not redirect)
        self.assertSuccessResponse(response)
        self.assertHtmlResponse(response)
        
        # Test that form errors are present in context
        self.assertIn('event_definition_form', response.context)
        form = response.context['event_definition_form']
        self.assertFalse(form.is_valid())
        
        # Should have validation errors for required fields
        self.assertTrue(form.errors)
        
        # Verify EventDefinition was not updated with invalid data
        self.event_definition.refresh_from_db()
        self.assertEqual(self.event_definition.name, 'Test Event')  # Original name unchanged

    def test_post_no_event_clauses(self):
        """Test POST request with no event clauses."""
        # Submit form with valid main form but no event clauses
        form_data = {
            # Valid main form fields
            'name': 'Updated Event Name',
            'event_type_str': 'automation',
            'event_window_secs': 120,
            'dedupe_window_secs': 600,
            'enabled': True,
            
            # No event clauses (empty formset)
            'event-clause-TOTAL_FORMS': '0',
            'event-clause-INITIAL_FORMS': '0',
            'event-clause-MIN_NUM_FORMS': '0',
            'event-clause-MAX_NUM_FORMS': '1000',
            
            # Valid alarm action
            'alarm-action-TOTAL_FORMS': '1',
            'alarm-action-INITIAL_FORMS': '0',
            'alarm-action-MIN_NUM_FORMS': '0',
            'alarm-action-MAX_NUM_FORMS': '1000',
            'alarm-action-0-security_level_str': 'low',
            'alarm-action-0-alarm_level_str': 'warning',
            'alarm-action-0-alarm_lifetime_secs': 300,
            
            # Control action formset
            'control-action-TOTAL_FORMS': '0',
            'control-action-INITIAL_FORMS': '0',
            'control-action-MIN_NUM_FORMS': '0',
            'control-action-MAX_NUM_FORMS': '1000',
        }

        url = reverse('event_definition_edit', kwargs={'id': self.event_definition.id})
        response = self.client.post(url, form_data)

        # Should return success with form errors (not redirect)
        self.assertSuccessResponse(response)
        self.assertHtmlResponse(response)
        
        # Should have error about missing event clauses
        form = response.context['event_definition_form']
        self.assertIn('Must have at least one event clause.', form.non_field_errors())
        
        # Verify EventDefinition was not updated
        self.event_definition.refresh_from_db()
        self.assertEqual(self.event_definition.name, 'Test Event')  # Original name unchanged

    def test_post_no_actions(self):
        """Test POST request with no alarm or control actions."""
        # Submit form with valid main form and event clauses but no actions
        form_data = {
            # Valid main form fields
            'name': 'Updated Event Name',
            'event_type_str': 'automation',
            'event_window_secs': 120,
            'dedupe_window_secs': 600,
            'enabled': True,
            
            # Valid event clause
            'event-clause-TOTAL_FORMS': '1',
            'event-clause-INITIAL_FORMS': '0',
            'event-clause-MIN_NUM_FORMS': '0',
            'event-clause-MAX_NUM_FORMS': '1000',
            'event-clause-0-entity_state': str(self.test_entity_state.id),
            'event-clause-0-value': 'on',
            
            # No alarm actions
            'alarm-action-TOTAL_FORMS': '0',
            'alarm-action-INITIAL_FORMS': '0',
            'alarm-action-MIN_NUM_FORMS': '0',
            'alarm-action-MAX_NUM_FORMS': '1000',
            
            # No control actions
            'control-action-TOTAL_FORMS': '0',
            'control-action-INITIAL_FORMS': '0',
            'control-action-MIN_NUM_FORMS': '0',
            'control-action-MAX_NUM_FORMS': '1000',
        }

        url = reverse('event_definition_edit', kwargs={'id': self.event_definition.id})
        response = self.client.post(url, form_data)

        # Should return success with form errors (not redirect)
        self.assertSuccessResponse(response)
        self.assertHtmlResponse(response)
        
        # Should have error about missing actions
        form = response.context['event_definition_form']
        self.assertIn('Must have either alarm of control action.', form.non_field_errors())
        
        # Verify EventDefinition was not updated
        self.event_definition.refresh_from_db()
        self.assertEqual(self.event_definition.name, 'Test Event')  # Original name unchanged

    def test_nonexistent_event_definition_returns_404(self):
        """Test that accessing nonexistent event definition returns 404."""
        url = reverse('event_definition_edit', kwargs={'id': 99999})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)


class TestEventDefinitionAddView(DualModeViewTestCase):
    """
    Tests for EventDefinitionAddView - demonstrates event definition creation testing.
    This view inherits from EventDefinitionEditView but creates new event definitions.
    """

    def setUp(self):
        super().setUp()
        # Create test entities and states for formsets (same as EditView)
        self.test_entity = Entity.objects.create(
            name='Test Entity',
            entity_type_str='switch',
            integration_id='test.entity',
            integration_name='test_integration'
        )
        
        self.test_entity_state = EntityState.objects.create(
            entity=self.test_entity,
            name='Test State',
            entity_state_type_str='on_off',
            value_range_str='on,off'
        )
        
        # Create a controller for control action tests
        self.test_controller = Controller.objects.create(
            name='Test Controller',
            entity_state=self.test_entity_state,
            controller_type_str='switch',
            integration_id='test.controller',
            integration_name='test_integration'
        )

    def test_get_event_definition_add(self):
        """Test getting event definition add form."""
        url = reverse('event_definition_add')
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        self.assertHtmlResponse(response)
        self.assertTemplateRendered(response, 'event/edit/modals/event_definition_add.html')
        
        # Test that real forms are present in response context
        self.assertIn('event_definition_form', response.context)
        self.assertIn('event_clause_formset', response.context)
        self.assertIn('alarm_action_formset', response.context)
        self.assertIn('control_action_formset', response.context)
        
        # Verify form is initialized with no instance (None for add)
        form = response.context['event_definition_form']
        self.assertIsNone(form.instance.pk)  # New instance has no PK

    def test_get_event_definition_add_async(self):
        """Test getting event definition add form with AJAX request."""
        url = reverse('event_definition_add')
        response = self.async_get(url)

        self.assertSuccessResponse(response)
        self.assertJsonResponse(response)
        
        # HiModalView returns JSON with modal content for AJAX requests
        data = response.json()
        self.assertIn('modal', data)

    @patch('hi.apps.event.edit.views.EventDefinitionEditView.event_manager')
    def test_post_valid_event_definition_add(self, mock_event_manager):
        """Test POST request to create new event definition."""
        # Mock event manager
        mock_manager = Mock()
        mock_event_manager.return_value = mock_manager

        # Create comprehensive form data for new event definition
        form_data = {
            # Main form fields
            'name': 'New Event Definition',
            'event_type_str': 'information',
            'event_window_secs': 90,
            'dedupe_window_secs': 450,
            'enabled': True,
            
            # Event clause formset (required)
            'event-clause-TOTAL_FORMS': '1',
            'event-clause-INITIAL_FORMS': '0',
            'event-clause-MIN_NUM_FORMS': '0',
            'event-clause-MAX_NUM_FORMS': '1000',
            'event-clause-0-entity_state': str(self.test_entity_state.id),
            'event-clause-0-value': 'off',
            
            # Alarm action formset (required to have at least one alarm or control action)
            'alarm-action-TOTAL_FORMS': '1',
            'alarm-action-INITIAL_FORMS': '0',
            'alarm-action-MIN_NUM_FORMS': '0',
            'alarm-action-MAX_NUM_FORMS': '1000',
            'alarm-action-0-security_level_str': 'high',
            'alarm-action-0-alarm_level_str': 'warning',
            'alarm-action-0-alarm_lifetime_secs': 600,
            
            # Control action formset (empty)
            'control-action-TOTAL_FORMS': '0',
            'control-action-INITIAL_FORMS': '0',
            'control-action-MIN_NUM_FORMS': '0',
            'control-action-MAX_NUM_FORMS': '1000',
        }

        # Count existing EventDefinitions before
        initial_count = EventDefinition.objects.count()

        url = reverse('event_definition_add')
        response = self.client.post(url, form_data)

        # Test actual redirect behavior (JSON redirect)
        self.assertSuccessResponse(response)
        self.assertJsonResponse(response)
        
        data = response.json()
        expected_url = reverse('event_definitions')
        self.assertEqual(data['location'], expected_url)
        
        # Test that new EventDefinition was created
        self.assertEqual(EventDefinition.objects.count(), initial_count + 1)
        
        # Get the newly created event definition
        new_event = EventDefinition.objects.get(name='New Event Definition')
        self.assertEqual(new_event.event_type_str, 'information')
        self.assertEqual(new_event.event_window_secs, 90)
        self.assertEqual(new_event.dedupe_window_secs, 450)
        
        # Test that formsets were properly saved
        event_clauses = new_event.event_clauses.all()
        self.assertEqual(len(event_clauses), 1)
        self.assertEqual(event_clauses[0].entity_state, self.test_entity_state)
        self.assertEqual(event_clauses[0].value, 'off')
        
        alarm_actions = new_event.alarm_actions.all()
        self.assertEqual(len(alarm_actions), 1)
        self.assertEqual(alarm_actions[0].security_level_str, 'high')
        self.assertEqual(alarm_actions[0].alarm_level_str, 'warning')
        
        # Verify event manager reload was called
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
            event_type_str='security',
            event_window_secs=60,
            dedupe_window_secs=300
        )

    def test_get_event_definition_delete(self):
        """Test getting event definition delete confirmation."""
        url = reverse('event_definition_delete', kwargs={'id': self.event_definition.id})
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        self.assertHtmlResponse(response)
        self.assertTemplateRendered(response, 'event/edit/modals/event_definition_delete.html')
        self.assertEqual(response.context['event_definition'], self.event_definition)

    def test_get_event_definition_delete_async(self):
        """Test getting event definition delete confirmation with AJAX request."""
        url = reverse('event_definition_delete', kwargs={'id': self.event_definition.id})
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

        url = reverse('event_definition_delete', kwargs={'id': self.event_definition.id})
        response = self.client.post(url)

        # Test actual redirect behavior (JSON redirect)
        self.assertSuccessResponse(response)
        self.assertJsonResponse(response)
        
        data = response.json()
        expected_url = reverse('event_definitions')
        self.assertEqual(data['location'], expected_url)
        
        # Event definition should be deleted
        with self.assertRaises(EventDefinition.DoesNotExist):
            EventDefinition.objects.get(id=self.event_definition.id)
        
        # Should reload event manager
        mock_manager.reload.assert_called_once()

    def test_nonexistent_event_definition_returns_404(self):
        """Test that accessing nonexistent event definition returns 404."""
        url = reverse('event_definition_delete', kwargs={'id': 99999})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)

    def test_post_nonexistent_event_definition_returns_404(self):
        """Test that deleting nonexistent event definition returns 404."""
        url = reverse('event_definition_delete', kwargs={'id': 99999})
        response = self.client.post(url)

        self.assertEqual(response.status_code, 404)
        
