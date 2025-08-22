import logging

from hi.apps.control.controller_history_manager import ControllerHistoryManager
from hi.apps.control.models import Controller, ControllerHistory
from hi.apps.entity.models import Entity, EntityState, EntityStateDelegation
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

    def test_get_latest_entity_controller_history_direct_states(self):
        """Test entity controller history retrieval for direct states - complex data aggregation."""
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
        
        # Create history records
        history1 = ControllerHistory.objects.create(
            controller=controller,
            value='on'
        )
        history2 = ControllerHistory.objects.create(
            controller=controller,
            value='off'
        )
        
        manager = ControllerHistoryManager()
        history_map = manager.get_latest_entity_controller_history(entity, max_items=5)
        
        # Should return map with controller history
        self.assertIn(controller, history_map)
        controller_history = list(history_map[controller])
        
        # Should be ordered newest first
        self.assertEqual(len(controller_history), 2)
        self.assertEqual(controller_history[0], history2)  # Most recent
        self.assertEqual(controller_history[1], history1)
        return

    def test_get_latest_entity_controller_history_delegated_states(self):
        """Test entity controller history for delegated states - complex relationship handling."""
        # Create primary entity
        primary_entity = Entity.objects.create(
            name='Primary Entity',
            entity_type_str='CAMERA'
        )
        
        # Create delegated entity and state
        delegated_entity = Entity.objects.create(
            name='Delegated Entity',
            entity_type_str='LIGHT'
        )
        delegated_state = EntityState.objects.create(
            entity=delegated_entity,
            entity_state_type_str='ON_OFF'
        )
        
        # Create delegation
        EntityStateDelegation.objects.create(
            delegate_entity=primary_entity,
            entity_state=delegated_state
        )
        
        # Create controller for delegated state
        controller = Controller.objects.create(
            name='Delegated Controller',
            entity_state=delegated_state,
            controller_type_str='DEFAULT',
            integration_id='test_id',
            integration_name='test_integration'
        )
        
        # Create history
        history = ControllerHistory.objects.create(
            controller=controller,
            value='on'
        )
        
        manager = ControllerHistoryManager()
        history_map = manager.get_latest_entity_controller_history(primary_entity, max_items=5)
        
        # Should include controllers from delegated states
        self.assertIn(controller, history_map)
        controller_history = list(history_map[controller])
        self.assertEqual(len(controller_history), 1)
        self.assertEqual(controller_history[0], history)
        return

    def test_get_latest_entity_controller_history_max_items_limit(self):
        """Test history retrieval max items limit - performance optimization."""
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
        
        # Create more history records than the limit
        for i in range(10):
            ControllerHistory.objects.create(
                controller=controller,
                value=f'value_{i}'
            )
        
        manager = ControllerHistoryManager()
        history_map = manager.get_latest_entity_controller_history(entity, max_items=3)
        
        # Should limit to max_items
        controller_history = list(history_map[controller])
        self.assertEqual(len(controller_history), 3)
        
        # Should be the most recent ones
        self.assertEqual(controller_history[0].value, 'value_9')  # Most recent
        self.assertEqual(controller_history[1].value, 'value_8')
        self.assertEqual(controller_history[2].value, 'value_7')
        return

    def test_entity_state_history_item_max_constant(self):
        """Test ENTITY_STATE_HISTORY_ITEM_MAX constant - important for default behavior."""
        manager = ControllerHistoryManager()
        
        # Should have reasonable default limit
        self.assertEqual(manager.ENTITY_STATE_HISTORY_ITEM_MAX, 5)
        self.assertGreater(manager.ENTITY_STATE_HISTORY_ITEM_MAX, 0)
        self.assertLess(manager.ENTITY_STATE_HISTORY_ITEM_MAX, 100)
        return
