"""
Unit tests for EntityTypeTransitionHandler.

Tests the complex entity type transition logic including change detection,
transaction management, and response determination.
"""
import logging
from unittest.mock import Mock, patch
from django.http import HttpRequest, HttpResponse

from hi.apps.entity.entity_edit_form_handler import EntityEditFormHandler
from hi.apps.entity.entity_type_transition_handler import EntityTypeTransitionHandler
from hi.apps.entity.enums import EntityType, EntityTransitionType
from hi.apps.entity.forms import EntityForm, EntityAttributeRegularFormSet
from hi.testing.base_test_case import BaseTestCase
from .synthetic_data import EntityAttributeSyntheticData

logging.disable(logging.CRITICAL)


class TestEntityTypeTransitionHandlerFormSaving(BaseTestCase):
    """Test form saving with transition detection."""

    def setUp(self):
        super().setUp()
        self.handler = EntityTypeTransitionHandler()
        self.entity = EntityAttributeSyntheticData.create_test_entity(entity_type_str=str(EntityType.LIGHT))
        self.request = Mock(spec=HttpRequest)

    def test_handle_entity_form_save_uses_transaction(self):
        """Test that form saving uses database transaction properly."""
        # Test that entity changes are saved atomically
        new_name = 'Transactionally Updated Name'
        
        # Create valid form data that changes the entity name
        form_data = EntityAttributeSyntheticData.create_form_data_for_entity_edit(
            self.entity, name=new_name
        )
        entity_form = EntityForm(form_data, instance=self.entity)
        
        self.assertTrue(entity_form.is_valid())
        
        result = self.handler.handle_entity_form_save(
            request=self.request,
            entity=self.entity,
            entity_form=entity_form
        )
        
        # Should return None for no entity type change
        self.assertIsNone(result)
        
        # Verify the entity was actually saved (transactional success)
        self.entity.refresh_from_db()
        self.assertEqual(self.entity.name, new_name)

    def test_handle_entity_form_save_no_type_change(self):
        """Test form saving when entity type doesn't change."""
        original_type = self.entity.entity_type_str
        
        # Create form data with same entity type
        form_data = EntityAttributeSyntheticData.create_form_data_for_entity_edit(
            self.entity, entity_type_str=original_type
        )
        entity_form = EntityForm(form_data, instance=self.entity)
        
        self.assertTrue(entity_form.is_valid())
        
        result = self.handler.handle_entity_form_save(
            request=self.request,
            entity=self.entity,
            entity_form=entity_form,
            original_entity_type_str=original_type
        )
        
        # Should return None (no transition response needed)
        self.assertIsNone(result)
        
        # Entity should be saved with same type
        self.entity.refresh_from_db()
        self.assertEqual(self.entity.entity_type_str, original_type)

    @patch.object(EntityTypeTransitionHandler, 'handle_entity_type_change')
    def test_handle_entity_form_save_with_type_change(self, mock_handle_change):
        """Test form saving when entity type changes."""
        mock_handle_change.return_value = Mock(spec=HttpResponse)
        
        original_type = EntityType.LIGHT
        new_type = EntityType.WALL_SWITCH
        
        # Create form data with different entity type
        form_data = EntityAttributeSyntheticData.create_form_data_for_entity_edit(
            self.entity, entity_type_str=str(new_type)
        )
        entity_form = EntityForm(form_data, instance=self.entity)
        
        self.assertTrue(entity_form.is_valid())
        
        result = self.handler.handle_entity_form_save(
            request=self.request,
            entity=self.entity,
            entity_form=entity_form,
            original_entity_type_str=original_type
        )
        
        # Should call type change handler
        mock_handle_change.assert_called_once_with(self.request, self.entity)
        
        # Should return the transition response
        self.assertIsNotNone(result)
        self.assertIsInstance(result, HttpResponse)

    def test_handle_entity_form_save_with_formset(self):
        """Test form saving with both entity form and attribute formset."""
        # Create attribute for formset
        attr = EntityAttributeSyntheticData.create_test_text_attribute(entity=self.entity)
        
        # Create form data for both entity and formset
        entity_data = EntityAttributeSyntheticData.create_form_data_for_entity_edit(
            self.entity, name='Updated Name'
        )
        formset_data = EntityAttributeSyntheticData.create_formset_data_for_attributes([attr], self.entity)
        prefix = EntityEditFormHandler.get_formset_prefix(self.entity)
        formset_data[f'{prefix}-0-value'] = 'Updated Value'
        
        form_data = {**entity_data, **formset_data}
        
        entity_form = EntityForm(entity_data, instance=self.entity)
        formset = EntityAttributeRegularFormSet(
            form_data, instance=self.entity, prefix=prefix
        )
        
        self.assertTrue(entity_form.is_valid())
        self.assertTrue(formset.is_valid())
        
        result = self.handler.handle_entity_form_save(
            request=self.request,
            entity=self.entity,
            entity_form=entity_form,
            entity_attribute_formset=formset
        )
        
        # Verify both were saved
        self.entity.refresh_from_db()
        attr.refresh_from_db()
        
        self.assertEqual(self.entity.name, 'Updated Name')
        self.assertEqual(attr.value, 'Updated Value')
        
        # No type change, should return None
        self.assertIsNone(result)

    def test_handle_entity_form_save_defaults_original_type(self):
        """Test that original_entity_type_str defaults to current entity type."""
        new_type = EntityType.WALL_SWITCH
        form_data = EntityAttributeSyntheticData.create_form_data_for_entity_edit(
            self.entity, entity_type_str=str(new_type)
        )
        entity_form = EntityForm(form_data, instance=self.entity)
        
        with patch.object(self.handler, 'handle_entity_type_change') as mock_handle_change:
            mock_handle_change.return_value = None
            
            # Don't provide original_entity_type_str
            self.handler.handle_entity_form_save(
                request=self.request,
                entity=self.entity,
                entity_form=entity_form
                # original_entity_type_str not provided
            )
            
            # Should detect change from current entity type
            mock_handle_change.assert_called_once()


class TestEntityTypeTransitionHandlerTransitionLogic(BaseTestCase):
    """Test entity type change handling and transition logic."""

    def setUp(self):
        super().setUp()
        self.handler = EntityTypeTransitionHandler()
        self.entity = EntityAttributeSyntheticData.create_test_entity(entity_type_str=str(EntityType.LIGHT))
        self.request = Mock(spec=HttpRequest)

    @patch('hi.apps.entity.entity_type_transition_handler.EntityManager')
    @patch('hi.apps.entity.entity_type_transition_handler.LocationManager')
    def test_handle_entity_type_change_successful_transition(self, mock_location_manager, mock_entity_manager):
        """Test successful entity type change with transition."""
        # Mock location manager
        mock_location_view = Mock()
        mock_location_manager.return_value.get_default_location_view.return_value = mock_location_view
        
        # Mock entity manager transition
        mock_entity_manager.return_value.handle_entity_type_transition.return_value = (True, EntityTransitionType.ICON_TO_ICON)
        
        result = self.handler.handle_entity_type_change(self.request, self.entity)
        
        # Should attempt transition
        mock_entity_manager.return_value.handle_entity_type_transition.assert_called_once_with(
            entity=self.entity,
            location_view=mock_location_view
        )
        
        # Should return refresh response for icon_to_icon transition
        self.assertIsNotNone(result)

    @patch('hi.apps.entity.entity_type_transition_handler.EntityManager')
    @patch('hi.apps.entity.entity_type_transition_handler.LocationManager')
    def test_handle_entity_type_change_failed_transition(self, mock_location_manager, mock_entity_manager):
        """Test entity type change when transition fails."""
        # Mock location manager
        mock_location_view = Mock()
        mock_location_manager.return_value.get_default_location_view.return_value = mock_location_view
        
        # Mock failed transition
        mock_entity_manager.return_value.handle_entity_type_transition.return_value = (False, EntityTransitionType.NO_TRANSITION_NEEDED)
        
        with patch('hi.apps.entity.entity_type_transition_handler.antinode.refresh_response') as mock_refresh:
            mock_refresh.return_value = Mock(spec=HttpResponse)
            
            result = self.handler.handle_entity_type_change(self.request, self.entity)
            
            # Should return refresh response for failed transition
            mock_refresh.assert_called_once()
            self.assertIsNotNone(result)

    @patch('hi.apps.entity.entity_type_transition_handler.EntityManager')
    @patch('hi.apps.entity.entity_type_transition_handler.LocationManager')
    def test_handle_entity_type_change_exception_handling(self, mock_location_manager, mock_entity_manager):
        """Test entity type change exception handling."""
        # Mock location manager to raise exception
        mock_location_manager.return_value.get_default_location_view.side_effect = Exception("Test error")
        
        with patch('hi.apps.entity.entity_type_transition_handler.antinode.refresh_response') as mock_refresh:
            mock_refresh.return_value = Mock(spec=HttpResponse)
            
            result = self.handler.handle_entity_type_change(self.request, self.entity)
            
            # Should return refresh response (observable behavior)
            mock_refresh.assert_called_once()
            self.assertIsNotNone(result)
            # The actual important behavior is that an HttpResponse is returned for error handling

    @patch('hi.apps.entity.entity_type_transition_handler.EntityManager')
    @patch('hi.apps.entity.entity_type_transition_handler.LocationManager')
    def test_handle_entity_type_change_path_to_path_transition(self, mock_location_manager, mock_entity_manager):
        """Test path_to_path transition returns None (sidebar refresh only)."""
        # Mock successful path_to_path transition
        mock_location_view = Mock()
        mock_location_manager.return_value.get_default_location_view.return_value = mock_location_view
        mock_entity_manager.return_value.handle_entity_type_transition.return_value = (True, EntityTransitionType.PATH_TO_PATH)
        
        result = self.handler.handle_entity_type_change(self.request, self.entity)
        
        # path_to_path transition should return None (no full page refresh needed)
        self.assertIsNone(result)


class TestEntityTypeTransitionHandlerRefreshLogic(BaseTestCase):
    """Test refresh determination logic."""

    def setUp(self):
        super().setUp()
        self.handler = EntityTypeTransitionHandler()

    def test_needs_full_page_refresh_failed_transition(self):
        """Test that failed transitions require full page refresh."""
        result = self.handler.needs_full_page_refresh(
            transition_occurred=False,
            transition_type=EntityTransitionType.NO_TRANSITION_NEEDED
        )
        
        self.assertTrue(result)

    def test_needs_full_page_refresh_path_to_path(self):
        """Test that path_to_path transitions don't require full page refresh."""
        result = self.handler.needs_full_page_refresh(
            transition_occurred=True,
            transition_type=EntityTransitionType.PATH_TO_PATH
        )
        
        self.assertFalse(result)

    def test_needs_full_page_refresh_icon_transitions(self):
        """Test that icon transitions require full page refresh."""
        icon_transitions = [EntityTransitionType.ICON_TO_ICON, EntityTransitionType.ICON_TO_PATH, EntityTransitionType.PATH_TO_ICON]
        
        for transition_type in icon_transitions:
            with self.subTest(transition_type=transition_type):
                result = self.handler.needs_full_page_refresh(
                    transition_occurred=True,
                    transition_type=transition_type
                )
                
                self.assertTrue(result)

    def test_needs_full_page_refresh_unknown_transition_type(self):
        """Test that unknown transition types default to full page refresh."""
        result = self.handler.needs_full_page_refresh(
            transition_occurred=True,
            transition_type=EntityTransitionType.NO_TRANSITION_NEEDED
        )
        
        self.assertTrue(result)

    def test_needs_full_page_refresh_comprehensive_logic(self):
        """Test comprehensive refresh logic scenarios."""
        test_cases = [
            # (transition_occurred, transition_type, expected_refresh)
            (False, EntityTransitionType.PATH_TO_PATH, True),      # Failed transition
            (False, EntityTransitionType.ICON_TO_ICON, True),     # Failed transition
            (True, EntityTransitionType.PATH_TO_PATH, False),     # Success, style change only
            (True, EntityTransitionType.ICON_TO_ICON, True),      # Success, visual change needed
            (True, EntityTransitionType.ICON_TO_PATH, True),      # Success, structure change
            (True, EntityTransitionType.PATH_TO_ICON, True),      # Success, structure change
            (True, EntityTransitionType.NO_TRANSITION_NEEDED, True),       # Unknown type, safe default
        ]
        
        for transition_occurred, transition_type, expected_refresh in test_cases:
            with self.subTest(occurred=transition_occurred, type=transition_type):
                result = self.handler.needs_full_page_refresh(
                    transition_occurred=transition_occurred,
                    transition_type=transition_type
                )
                
                self.assertEqual(result, expected_refresh)


class TestEntityTypeTransitionHandlerIntegration(BaseTestCase):
    """Test integration scenarios with real entity type changes."""

    def setUp(self):
        super().setUp()
        self.handler = EntityTypeTransitionHandler()
        self.request = Mock(spec=HttpRequest)

    def test_complete_entity_type_change_scenario(self):
        """Test complete entity type change from LIGHT to WALL_SWITCH."""
        entity = EntityAttributeSyntheticData.create_test_entity(entity_type_str=str(EntityType.LIGHT))
        original_type = entity.entity_type_str
        
        # Create form data changing type
        form_data = EntityAttributeSyntheticData.create_form_data_for_entity_edit(
            entity, entity_type_str=str(EntityType.WALL_SWITCH)
        )
        entity_form = EntityForm(form_data, instance=entity)
        
        self.assertTrue(entity_form.is_valid())
        
        # Mock the complex dependencies
        with patch('hi.apps.entity.entity_type_transition_handler.LocationManager') as mock_loc_mgr, \
             patch('hi.apps.entity.entity_type_transition_handler.EntityManager') as mock_entity_mgr, \
             patch('hi.apps.entity.entity_type_transition_handler.antinode.refresh_response') as mock_refresh:
            
            # Setup mocks
            mock_location_view = Mock()
            mock_loc_mgr.return_value.get_default_location_view.return_value = mock_location_view
            mock_entity_mgr.return_value.handle_entity_type_transition.return_value = (True, EntityTransitionType.ICON_TO_ICON)
            mock_refresh.return_value = Mock(spec=HttpResponse)
            
            # Execute the transition
            result = self.handler.handle_entity_form_save(
                request=self.request,
                entity=entity,
                entity_form=entity_form,
                original_entity_type_str=original_type
            )
            
            # Verify entity was saved
            entity.refresh_from_db()
            self.assertEqual(entity.entity_type_str, str(EntityType.WALL_SWITCH).lower())
            
            # Verify transition was attempted
            mock_entity_mgr.return_value.handle_entity_type_transition.assert_called_once()
            
            # Verify refresh response was returned
            mock_refresh.assert_called_once()
            self.assertIsNotNone(result)

    def test_entity_type_change_with_attributes_formset(self):
        """Test entity type change with simultaneous attribute changes."""
        entity = EntityAttributeSyntheticData.create_test_entity(entity_type_str=str(EntityType.LIGHT))
        attr = EntityAttributeSyntheticData.create_test_text_attribute(
            entity=entity, name='brightness', value='100'
        )
        
        # Create form data changing both entity type and attribute
        entity_data = EntityAttributeSyntheticData.create_form_data_for_entity_edit(
            entity, entity_type_str=str(EntityType.WALL_SWITCH), name='Updated Light'
        )
        formset_data = EntityAttributeSyntheticData.create_formset_data_for_attributes([attr], entity)
        prefix = EntityEditFormHandler.get_formset_prefix(entity)
        formset_data[f'{prefix}-0-value'] = '75'
        
        form_data = {**entity_data, **formset_data}
        
        entity_form = EntityForm(entity_data, instance=entity)
        formset = EntityAttributeRegularFormSet(
            form_data, instance=entity, prefix=prefix
        )
        
        self.assertTrue(entity_form.is_valid())
        self.assertTrue(formset.is_valid())
        
        # Mock transition to return simple response
        with patch('hi.apps.entity.entity_type_transition_handler.LocationManager'), \
             patch('hi.apps.entity.entity_type_transition_handler.EntityManager') as mock_entity_mgr, \
             patch('hi.apps.entity.entity_type_transition_handler.antinode.refresh_response') as mock_refresh:
            
            # Mock simple transition
            mock_entity_mgr.return_value.handle_entity_type_transition.return_value = (True, EntityTransitionType.PATH_TO_PATH)
            mock_refresh.return_value = Mock(spec=HttpResponse)
            
            result = self.handler.handle_entity_form_save(
                request=self.request,
                entity=entity,
                entity_form=entity_form,
                entity_attribute_formset=formset,
                original_entity_type_str=str(EntityType.LIGHT)
            )
            
            # Verify both entity and attribute were saved
            entity.refresh_from_db()
            attr.refresh_from_db()
            
            self.assertEqual(entity.entity_type_str, str(EntityType.WALL_SWITCH).lower())
            self.assertEqual(entity.name, 'Updated Light')
            self.assertEqual(attr.value, '75')
            
            # path_to_path transition should not require full page refresh
            self.assertIsNone(result)

    def test_transaction_rollback_on_transition_failure(self):
        """Test that transaction is properly managed even if transition fails."""
        entity = EntityAttributeSyntheticData.create_test_entity(entity_type_str=str(EntityType.LIGHT))
        
        form_data = EntityAttributeSyntheticData.create_form_data_for_entity_edit(
            entity, entity_type_str=str(EntityType.WALL_SWITCH), name='Updated Name'
        )
        entity_form = EntityForm(form_data, instance=entity)
        
        # Mock transition to raise exception after forms are saved
        with patch('hi.apps.entity.entity_type_transition_handler.LocationManager') as mock_loc_mgr, \
             patch('hi.apps.entity.entity_type_transition_handler.EntityManager'):
            
            mock_loc_mgr.return_value.get_default_location_view.side_effect = Exception("Transition error")
            
            # The form save should still work, transition failure is handled gracefully
            result = self.handler.handle_entity_form_save(
                request=self.request,
                entity=entity,
                entity_form=entity_form,
                original_entity_type_str=str(EntityType.LIGHT)
            )
            
            # Entity should still be saved (transaction includes form save)
            entity.refresh_from_db()
            self.assertEqual(entity.entity_type_str, str(EntityType.WALL_SWITCH).lower())
            self.assertEqual(entity.name, 'Updated Name')
            
            # Should return error response due to transition failure
            self.assertIsNotNone(result)

    def test_no_transition_when_type_unchanged(self):
        """Test that no transition is attempted when entity type doesn't change."""
        entity = EntityAttributeSyntheticData.create_test_entity(entity_type_str=str(EntityType.LIGHT))
        
        # Create form data with same entity type
        form_data = EntityAttributeSyntheticData.create_form_data_for_entity_edit(
            entity, entity_type_str=str(EntityType.LIGHT), name='Updated Name'
        )
        entity_form = EntityForm(form_data, instance=entity)
        
        with patch('hi.apps.entity.entity_type_transition_handler.LocationManager') as mock_loc_mgr, \
             patch('hi.apps.entity.entity_type_transition_handler.EntityManager') as mock_entity_mgr:
            
            result = self.handler.handle_entity_form_save(
                request=self.request,
                entity=entity,
                entity_form=entity_form,
                original_entity_type_str=str(EntityType.LIGHT)  # Same as current type
            )
            
            # No transition should be attempted
            mock_loc_mgr.assert_not_called()
            mock_entity_mgr.assert_not_called()
            
            # Should return None (no special response needed)
            self.assertIsNone(result)
            
            # Entity should still be saved
            entity.refresh_from_db()
            self.assertEqual(entity.name, 'Updated Name')
            
