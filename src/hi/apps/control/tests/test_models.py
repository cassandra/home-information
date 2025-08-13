import logging
from django.db import IntegrityError

from hi.apps.control.models import Controller, ControllerHistory
from hi.apps.control.enums import ControllerType
from hi.apps.entity.models import Entity, EntityState
from hi.apps.entity.enums import EntityType, EntityStateType
from hi.tests.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestController(BaseTestCase):

    def test_controller_integration_key_uniqueness(self):
        """Test integration key uniqueness constraint - critical for data integrity."""
        entity = Entity.objects.create(
            name='Test Entity',
            entity_type_str='CAMERA'
        )
        entity_state = EntityState.objects.create(
            entity=entity,
            entity_state_type_str='ON_OFF'
        )
        
        # Create first controller
        Controller.objects.create(
            name='Test Controller 1',
            entity_state=entity_state,
            controller_type_str='DEFAULT',
            integration_id='test_id',
            integration_name='test_integration'
        )
        
        # Duplicate integration key should fail
        with self.assertRaises(IntegrityError):
            Controller.objects.create(
                name='Test Controller 2',
                entity_state=entity_state,
                controller_type_str='DEFAULT',
                integration_id='test_id',
                integration_name='test_integration'
            )
        return

    def test_controller_type_property_conversion(self):
        """Test controller_type property enum conversion - custom business logic."""
        entity = Entity.objects.create(
            name='Test Entity',
            entity_type_str='CAMERA'
        )
        entity_state = EntityState.objects.create(
            entity=entity,
            entity_state_type_str='ON_OFF'
        )
        
        controller = Controller.objects.create(
            name='Test Controller',
            entity_state=entity_state,
            controller_type_str='DEFAULT',
            integration_id='test_id',
            integration_name='test_integration'
        )
        
        # Test getter converts string to enum
        self.assertEqual(controller.controller_type, ControllerType.DEFAULT)
        
        # Test setter converts enum to string
        controller.controller_type = ControllerType.DEFAULT
        self.assertEqual(controller.controller_type_str, 'default')
        return

    def test_controller_choices_delegation(self):
        """Test choices property delegation to entity state - critical for UI."""
        entity = Entity.objects.create(
            name='Test Entity',
            entity_type_str='CAMERA'
        )
        entity_state = EntityState.objects.create(
            entity=entity,
            entity_state_type_str='ON_OFF'
        )
        
        controller = Controller.objects.create(
            name='Test Controller',
            entity_state=entity_state,
            controller_type_str='DEFAULT',
            integration_id='test_id',
            integration_name='test_integration'
        )
        
        # Should delegate to entity_state.choices()
        choices = controller.choices
        self.assertIsNotNone(choices)
        # EntityState should provide choices based on entity_state_type
        return

    def test_controller_cascade_deletion_from_entity_state(self):
        """Test cascade deletion from entity state - critical for data integrity."""
        entity = Entity.objects.create(
            name='Test Entity',
            entity_type_str='CAMERA'
        )
        entity_state = EntityState.objects.create(
            entity=entity,
            entity_state_type_str='ON_OFF'
        )
        
        controller = Controller.objects.create(
            name='Test Controller',
            entity_state=entity_state,
            controller_type_str='DEFAULT',
            integration_id='test_id',
            integration_name='test_integration'
        )
        
        controller_id = controller.id
        
        # Delete entity state should cascade to controller
        entity_state.delete()
        
        self.assertFalse(Controller.objects.filter(id=controller_id).exists())
        return

    def test_controller_string_representation(self):
        """Test __str__ method format - important for debugging and admin."""
        entity = Entity.objects.create(
            name='Test Entity',
            entity_type_str='CAMERA'
        )
        entity_state = EntityState.objects.create(
            entity=entity,
            entity_state_type_str='ON_OFF'
        )
        
        controller = Controller.objects.create(
            name='Test Controller',
            entity_state=entity_state,
            controller_type_str='DEFAULT',
            integration_id='test_id',
            integration_name='test_integration'
        )
        
        str_repr = str(controller)
        self.assertIn('Test Controller', str_repr)
        self.assertIn('on_off', str_repr)  # entity_state_type
        self.assertIn(str(controller.id), str_repr)
        self.assertIn('test_id', str_repr)
        return


class TestControllerHistory(BaseTestCase):

    def test_controller_history_ordering_by_created_datetime(self):
        """Test ControllerHistory ordering - critical for history display."""
        entity = Entity.objects.create(
            name='Test Entity',
            entity_type_str='CAMERA'
        )
        entity_state = EntityState.objects.create(
            entity=entity,
            entity_state_type_str='ON_OFF'
        )
        
        controller = Controller.objects.create(
            name='Test Controller',
            entity_state=entity_state,
            controller_type_str='DEFAULT',
            integration_id='test_id',
            integration_name='test_integration'
        )
        
        # Create history entries (they'll have different timestamps)
        history1 = ControllerHistory.objects.create(
            controller=controller,
            value='on'
        )
        history2 = ControllerHistory.objects.create(
            controller=controller,
            value='off'
        )
        history3 = ControllerHistory.objects.create(
            controller=controller,
            value='on'
        )
        
        # Should be ordered by newest first
        history_list = list(ControllerHistory.objects.filter(controller=controller))
        self.assertEqual(history_list[0], history3)  # Most recent
        self.assertEqual(history_list[1], history2)
        self.assertEqual(history_list[2], history1)  # Oldest
        return

    def test_controller_history_cascade_deletion_from_controller(self):
        """Test cascade deletion from controller - critical for data integrity."""
        entity = Entity.objects.create(
            name='Test Entity',
            entity_type_str='CAMERA'
        )
        entity_state = EntityState.objects.create(
            entity=entity,
            entity_state_type_str='ON_OFF'
        )
        
        controller = Controller.objects.create(
            name='Test Controller',
            entity_state=entity_state,
            controller_type_str='DEFAULT',
            integration_id='test_id',
            integration_name='test_integration'
        )
        
        history = ControllerHistory.objects.create(
            controller=controller,
            value='on'
        )
        
        history_id = history.id
        
        # Delete controller should cascade to history
        controller.delete()
        
        self.assertFalse(ControllerHistory.objects.filter(id=history_id).exists())
        return

    def test_controller_history_created_datetime_indexing(self):
        """Test created_datetime field indexing - critical for query performance."""
        entity = Entity.objects.create(
            name='Test Entity',
            entity_type_str='CAMERA'
        )
        entity_state = EntityState.objects.create(
            entity=entity,
            entity_state_type_str='ON_OFF'
        )
        
        controller = Controller.objects.create(
            name='Test Controller',
            entity_state=entity_state,
            controller_type_str='DEFAULT',
            integration_id='test_id',
            integration_name='test_integration'
        )
        
        history = ControllerHistory.objects.create(
            controller=controller,
            value='on'
        )
        
        # Test that created_datetime queries work efficiently
        # (The actual index performance isn't testable in unit tests,
        # but we can verify the field is accessible and queryable)
        recent_history = ControllerHistory.objects.filter(
            created_datetime__gte=history.created_datetime
        )
        self.assertIn(history, recent_history)
        return