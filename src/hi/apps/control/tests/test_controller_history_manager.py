import logging

from hi.apps.control.controller_history_manager import ControllerHistoryManager
from hi.apps.control.models import Controller, ControllerHistory
from hi.apps.entity.models import Entity, EntityState
from hi.testing.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestControllerHistoryManager(BaseTestCase):

    def test_controller_history_manager_singleton_behavior(self):
        """Test ControllerHistoryManager singleton pattern - critical for system consistency."""
        manager1 = ControllerHistoryManager()
        manager2 = ControllerHistoryManager()
        
        # Should be the same instance
        self.assertIs(manager1, manager2)
        return

    def test_add_to_controller_history_creates_record(self):
        """Test history record creation - critical for audit trail."""
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
            integration_name='test_integration',
            persist_history=True
        )
        
        manager = ControllerHistoryManager()
        history_record = manager.add_to_controller_history(controller, 'on')
        
        # Should create history record
        self.assertIsNotNone(history_record)
        self.assertEqual(history_record.controller, controller)
        self.assertEqual(history_record.value, 'on')
        
        # Should be saved to database
        self.assertTrue(ControllerHistory.objects.filter(id=history_record.id).exists())
        return

    def test_add_to_controller_history_respects_persist_flag(self):
        """Test history persistence flag - critical for storage control."""
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
            integration_name='test_integration',
            persist_history=False  # Disabled
        )
        
        manager = ControllerHistoryManager()
        history_record = manager.add_to_controller_history(controller, 'on')
        
        # Should not create history record when disabled
        self.assertIsNone(history_record)
        
        # Should not be in database
        self.assertEqual(ControllerHistory.objects.filter(controller=controller).count(), 0)
        return

        return
