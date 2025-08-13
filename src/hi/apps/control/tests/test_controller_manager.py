import logging
from unittest.mock import Mock, patch
import asyncio

from hi.apps.control.controller_manager import ControllerManager
from hi.apps.control.models import Controller
from hi.apps.entity.models import Entity, EntityState
from hi.integrations.transient_models import IntegrationControlResult
from hi.tests.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestControllerManager(BaseTestCase):

    def test_controller_manager_singleton_behavior(self):
        """Test ControllerManager singleton pattern - critical for system consistency."""
        manager1 = ControllerManager()
        manager2 = ControllerManager()
        
        # Should be the same instance
        self.assertIs(manager1, manager2)
        return

    def test_controller_manager_initialization_tracking(self):
        """Test initialization tracking - important for lazy loading."""
        manager = ControllerManager()
        
        # Should start uninitialized
        self.assertFalse(manager._was_initialized)
        
        # Should initialize once
        manager.ensure_initialized()
        self.assertTrue(manager._was_initialized)
        
        # Should not reinitialize
        manager.ensure_initialized()
        self.assertTrue(manager._was_initialized)
        return

    @patch('hi.apps.control.controller_manager.IntegrationManager')
    def test_do_control_integration_delegation(self, mock_integration_manager):
        """Test do_control integration delegation - critical for control operations."""
        # Setup mocks
        mock_integration_gateway = Mock()
        mock_integration_controller = Mock()
        mock_control_result = Mock(spec=IntegrationControlResult)
        
        mock_integration_manager.return_value.get_integration_gateway.return_value = mock_integration_gateway
        mock_integration_gateway.get_controller.return_value = mock_integration_controller
        mock_integration_controller.do_control.return_value = mock_control_result
        
        # Create test controller
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
        
        # Test control operation
        manager = ControllerManager()
        result = manager.do_control(controller=controller, control_value='on')
        
        # Should delegate to integration system
        mock_integration_manager.return_value.get_integration_gateway.assert_called_once_with(
            integration_id='test_id'
        )
        mock_integration_gateway.get_controller.assert_called_once()
        mock_integration_controller.do_control.assert_called_once_with(
            integration_key=controller.integration_key,
            control_value='on'
        )
        
        self.assertEqual(result, mock_control_result)
        return

    @patch('hi.apps.control.controller_manager.IntegrationManager')
    def test_do_control_async_delegation(self, mock_integration_manager):
        """Test async control delegation - critical for async operations."""
        # Setup mocks
        mock_integration_gateway = Mock()
        mock_integration_controller = Mock()
        mock_control_result = Mock(spec=IntegrationControlResult)
        
        mock_integration_manager.return_value.get_integration_gateway.return_value = mock_integration_gateway
        mock_integration_gateway.get_controller.return_value = mock_integration_controller
        mock_integration_controller.do_control.return_value = mock_control_result
        
        # Create test controller
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
        
        # Test async control operation
        manager = ControllerManager()
        
        async def run_async_test():
            result = await manager.do_control_async(controller=controller, control_value='off')
            return result
        
        # Run the async test
        result = asyncio.run(run_async_test())
        
        # Should delegate to sync method through sync_to_async
        mock_integration_controller.do_control.assert_called_once_with(
            integration_key=controller.integration_key,
            control_value='off'
        )
        
        self.assertEqual(result, mock_control_result)
        return
