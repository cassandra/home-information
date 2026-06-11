import logging

from hi.apps.entity.entity_manager import EntityManager
from hi.apps.entity.models import (
    Entity,
    EntityState,
    EntityStateDelegation,
    EntityView,
)
from hi.apps.entity.enums import EntityGroupType, EntityStateType, EntityType
from hi.apps.location.tests.synthetic_data import LocationSyntheticData
from hi.testing.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestEntityManager(BaseTestCase):

    def test_singleton_behavior(self):
        """Test EntityManager singleton pattern - critical for system consistency."""
        manager1 = EntityManager()
        manager2 = EntityManager()
        
        self.assertIs(manager1, manager2)
        return

    def test_change_listener_system_notifies_all_registered_callbacks(self):
        """Test change listener system - core functionality for system integration."""
        manager = EntityManager()
        
        # Track actual behavior with state changes
        callback1_called = []
        callback2_called = []
        
        def callback1():
            callback1_called.append(True)
        
        def callback2():
            callback2_called.append(True)
        
        manager.register_change_listener(callback1)
        manager.register_change_listener(callback2)
        
        # Clear any previous calls
        callback1_called.clear()
        callback2_called.clear()
        
        # Trigger reload which should notify listeners
        manager.reload()
        
        # Verify both callbacks were actually executed
        self.assertEqual(len(callback1_called), 1)
        self.assertEqual(len(callback2_called), 1)
        return

    def test_change_listener_system_continues_after_callback_failure(self):
        """Test change listener error handling - system should be resilient to callback failures."""
        manager = EntityManager()
        
        # Create callback that raises exception
        def failing_callback():
            raise ValueError("Test exception")
        
        # Track normal callback execution
        normal_callback_called = []
        
        def normal_callback():
            normal_callback_called.append(True)
        
        manager.register_change_listener(failing_callback)
        manager.register_change_listener(normal_callback)
        
        # Clear previous calls
        normal_callback_called.clear()
        
        # Reload should not fail despite exception in callback
        manager.reload()
        
        # Normal callback should still execute despite exception in first callback
        self.assertEqual(len(normal_callback_called), 1)
        return

    def test_get_entity_edit_mode_data_returns_complete_data_structure(self):
        """Test get_entity_edit_mode_data business logic - complex method integrating multiple systems."""
        manager = EntityManager()
        
        # Create test entity
        entity = Entity.objects.create(
            name='Test Camera',
            entity_type_str=str(EntityType.CAMERA),
            integration_id='test_camera_001',
            integration_name='test_integration',
        )
        
        # Test with no location_view (basic case)
        edit_mode_data = manager.get_entity_edit_mode_data(
            entity=entity,
            location_view=None,
            is_editing=False
        )
        
        # Verify complete data structure is returned
        self.assertIsNotNone(edit_mode_data)
        self.assertEqual(edit_mode_data.entity, entity)
        self.assertIsNotNone(edit_mode_data.entity_form)
        self.assertIsNotNone(edit_mode_data.entity_pairing_list)
        
        # Without location_view, position form should be None
        self.assertIsNone(edit_mode_data.entity_position_form)
        
        # Test non-editing mode doesn't create position form
        edit_mode_data_non_edit = manager.get_entity_edit_mode_data(
            entity=entity,
            location_view=None,
            is_editing=True  # Even with editing=True, no location_view means no form
        )
        self.assertIsNone(edit_mode_data_non_edit.entity_position_form)
        return

    def test_create_entity_view_group_list_business_logic(self):
        """Test entity view group creation - complex business logic for UI organization."""
        manager = EntityManager()
        
        # Create test entities of different types
        light_entity = Entity.objects.create(
            name='Living Room Light',
            entity_type_str=str(EntityType.LIGHT),
            integration_id='light_001',
            integration_name='test_integration',
        )
        
        camera_entity = Entity.objects.create(
            name='Front Door Camera',
            entity_type_str=str(EntityType.CAMERA),
            integration_id='camera_001',
            integration_name='test_integration',
        )
        
        thermostat_entity = Entity.objects.create(
            name='Main Thermostat',
            entity_type_str=str(EntityType.THERMOSTAT),
            integration_id='thermo_001',
            integration_name='test_integration',
        )
        
        all_entities = [light_entity, camera_entity, thermostat_entity]
        existing_entities = [light_entity]  # Only light exists in view
        
        # Test group creation business logic
        group_list = manager.create_entity_view_group_list(
            existing_entities=existing_entities,
            all_entities=all_entities
        )
        
        # Should have multiple groups based on entity types
        self.assertGreater(len(group_list), 1)
        
        # Verify groups are sorted by label
        group_labels = [group.entity_group_type.label for group in group_list]
        sorted_labels = sorted(group_labels)
        self.assertEqual(group_labels, sorted_labels)
        
        # Find the automation group (where LIGHT lives) and verify
        # the light entity is marked as existing in the view.
        automation_group = None
        for group in group_list:
            if group.entity_group_type == EntityGroupType.AUTOMATION:
                automation_group = group
                break

        self.assertIsNotNone(automation_group)

        light_item = None
        for item in automation_group.item_list:
            if item.entity == light_entity:
                light_item = item
                break
        
        self.assertIsNotNone(light_item)
        self.assertTrue(light_item.exists_in_view)
        
        # Verify camera entity is not marked as existing in view
        security_group = None
        for group in group_list:
            if group.entity_group_type == EntityGroupType.SECURITY:
                security_group = group
                break
        
        if security_group:  # May not exist if camera maps to different group
            camera_item = None
            for item in security_group.item_list:
                if item.entity == camera_entity:
                    camera_item = item
                    break
            
            if camera_item:
                self.assertFalse(camera_item.exists_in_view)

        return


class TestCreateLocationEntityViewGroupListExcludeDelegates(BaseTestCase):
    """``exclude_delegates`` hides entities that act as delegates of
    some principal, so the edit-mode sidebar doesn't surface them
    as separately-toggleable checkboxes."""

    def _make_principal_with_delegate(self):
        principal = Entity.objects.create(
            name='Motion Sensor',
            entity_type_str=str(EntityType.MOTION_SENSOR),
        )
        delegate_area = Entity.objects.create(
            name='Living Room',
            entity_type_str=str(EntityType.AREA),
        )
        state = EntityState.objects.create(
            entity=principal,
            entity_state_type_str=str(EntityStateType.MOVEMENT),
            name='movement',
        )
        EntityStateDelegation.objects.create(
            entity_state=state,
            delegate_entity=delegate_area,
        )
        return principal, delegate_area

    def _names_in_groups(self, group_list):
        return {
            item.entity.name
            for group in group_list
            for item in group.item_list
        }

    def _picker_groups_and_delegates(self, location_view, unused_entity_ids=None):
        """Bridges the current two-method picker API (type-grouped list +
        delegate list). The query-optimization refactor will repoint this
        single helper at the combined method without touching the test
        bodies, so these tests double as a behavior-preserving net."""
        if unused_entity_ids is None:
            unused_entity_ids = set()
        picker_data = EntityManager().create_location_entity_picker_data(
            location_view=location_view,
            unused_entity_ids=unused_entity_ids,
        )
        return picker_data.entity_view_group_list, picker_data.delegate_view_item_list

    def test_delegate_hidden_when_exclude_delegates_true(self):
        principal, delegate_area = self._make_principal_with_delegate()
        location_view = LocationSyntheticData.create_test_location_view()

        group_list = EntityManager().create_location_entity_view_group_list(
            location_view=location_view,
            exclude_delegates=True,
        )

        names = self._names_in_groups(group_list)
        self.assertIn(principal.name, names)
        self.assertNotIn(delegate_area.name, names)

    def test_delegate_visible_by_default(self):
        # Default (exclude_delegates=False) preserves the pre-change
        # behavior so the pairings modal and any other caller keeps
        # seeing delegates.
        principal, delegate_area = self._make_principal_with_delegate()
        location_view = LocationSyntheticData.create_test_location_view()

        group_list = EntityManager().create_location_entity_view_group_list(
            location_view=location_view,
        )

        names = self._names_in_groups(group_list)
        self.assertIn(principal.name, names)
        self.assertIn(delegate_area.name, names)

    def test_non_delegate_entity_unaffected_by_filter(self):
        # An entity that is neither principal nor delegate keeps
        # appearing whether the filter is on or off.
        plain = Entity.objects.create(
            name='Standalone Light',
            entity_type_str=str(EntityType.LIGHT),
        )
        location_view = LocationSyntheticData.create_test_location_view()

        group_list = EntityManager().create_location_entity_view_group_list(
            location_view=location_view,
            exclude_delegates=True,
        )

        names = self._names_in_groups(group_list)
        self.assertIn(plain.name, names)

    def test_delegate_view_item_list_contains_only_delegates(self):
        # The "Paired Items" section is the complement of the excluded
        # type-grouped list: just the delegates, neither the principal
        # nor unrelated standalone entities.
        principal, delegate_area = self._make_principal_with_delegate()
        Entity.objects.create(
            name='Standalone Light',
            entity_type_str=str(EntityType.LIGHT),
        )
        location_view = LocationSyntheticData.create_test_location_view()

        _, item_list = self._picker_groups_and_delegates(location_view)

        names = { item.entity.name for item in item_list }
        self.assertEqual(names, { delegate_area.name })

    def _make_named_delegate(self, principal_name, delegate_name):
        principal = Entity.objects.create(
            name=principal_name,
            entity_type_str=str(EntityType.MOTION_SENSOR),
        )
        state = EntityState.objects.create(
            entity=principal,
            entity_state_type_str=str(EntityStateType.MOVEMENT),
            name='movement',
        )
        delegate = Entity.objects.create(
            name=delegate_name,
            entity_type_str=str(EntityType.AREA),
        )
        EntityStateDelegation.objects.create(
            entity_state=state,
            delegate_entity=delegate,
        )
        return delegate

    def test_delegate_view_item_exists_in_view_flag(self):
        # A delegate already placed in the view is flagged in-view so the
        # picker renders it as a toggle-off; one not in the view is not.
        delegate_area = self._make_named_delegate('Front Motion', 'Front Area')
        other_delegate = self._make_named_delegate('Back Motion', 'Back Area')
        location_view = LocationSyntheticData.create_test_location_view()
        EntityView.objects.create(
            entity=delegate_area,
            location_view=location_view,
        )

        _, item_list = self._picker_groups_and_delegates(location_view)
        exists_by_name = { item.entity.name: item.exists_in_view for item in item_list }

        self.assertTrue(exists_by_name[delegate_area.name])
        self.assertFalse(exists_by_name[other_delegate.name])

    def test_delegate_partition_is_mutually_exclusive(self):
        # A delegate appears only in the delegate list; a non-delegate
        # (principal or standalone) appears only in the type-grouped
        # list. The two halves never overlap.
        principal, delegate_area = self._make_principal_with_delegate()
        standalone = Entity.objects.create(
            name='Standalone Light',
            entity_type_str=str(EntityType.LIGHT),
        )
        location_view = LocationSyntheticData.create_test_location_view()

        group_list, delegate_item_list = self._picker_groups_and_delegates(location_view)
        group_names = self._names_in_groups(group_list)
        delegate_names = { item.entity.name for item in delegate_item_list }

        self.assertEqual(delegate_names, { delegate_area.name })
        self.assertIn(principal.name, group_names)
        self.assertIn(standalone.name, group_names)
        self.assertNotIn(delegate_area.name, group_names)
        self.assertNotIn(principal.name, delegate_names)
        self.assertNotIn(standalone.name, delegate_names)

    def test_is_unused_propagates_to_delegate_list(self):
        # The delegate list carries the is_unused flag through from the
        # caller-supplied set, same as the type-grouped list.
        _, delegate_area = self._make_principal_with_delegate()
        location_view = LocationSyntheticData.create_test_location_view()

        _, delegate_item_list = self._picker_groups_and_delegates(
            location_view, unused_entity_ids={ delegate_area.id },
        )
        item = next( i for i in delegate_item_list if i.entity == delegate_area )
        self.assertTrue(item.is_unused)

        _, delegate_item_list = self._picker_groups_and_delegates(
            location_view, unused_entity_ids=set(),
        )
        item = next( i for i in delegate_item_list if i.entity == delegate_area )
        self.assertFalse(item.is_unused)


