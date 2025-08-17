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

    @patch.object(ControllerManager, '_instance', None)
    @patch('hi.apps.control.controller_manager.IntegrationManager')
    def test_do_control_returns_integration_result(self, mock_integration_manager_class):
        """Test do_control returns actual control result from integration layer."""
        # Create real controller with integration details
        entity = Entity.objects.create(
            name='Test Light',
            entity_type_str='LIGHT'
        )
        entity_state = EntityState.objects.create(
            entity=entity,
            entity_state_type_str='ON_OFF'
        )
        
        controller = Controller.objects.create(
            name='Living Room Light',
            entity_state=entity_state,
            controller_type_str='DEFAULT',
            integration_id='home_assistant',
            integration_name='Home Assistant'
        )
        
        # Mock only at integration boundary
        mock_control_result = IntegrationControlResult(
            new_value='on',
            error_list=[]
        )
        mock_integration_controller = Mock()
        mock_integration_controller.do_control.return_value = mock_control_result
        
        mock_integration_gateway = Mock()
        mock_integration_gateway.get_controller.return_value = mock_integration_controller
        
        mock_integration_manager = Mock()
        mock_integration_manager.get_integration_gateway.return_value = mock_integration_gateway
        mock_integration_manager_class.return_value = mock_integration_manager
        
        # Test the control operation
        manager = ControllerManager()
        result = manager.do_control(controller=controller, control_value='on')
        
        # Test actual return value and behavior
        self.assertIsInstance(result, IntegrationControlResult)
        self.assertFalse(result.has_errors)
        self.assertEqual(result.new_value, 'on')
        self.assertEqual(result.error_list, [])
        
        # Verify integration details passed correctly
        call_args = mock_integration_controller.do_control.call_args
        self.assertEqual(call_args.kwargs['control_value'], 'on')
        integration_details = call_args.kwargs['integration_details']
        self.assertEqual(integration_details.key, controller.integration_key)
        self.assertEqual(integration_details.payload, controller.integration_payload)
        return

    @patch.object(ControllerManager, '_instance', None)
    @patch('hi.apps.control.controller_manager.IntegrationManager')
    def test_do_control_handles_integration_errors(self, mock_integration_manager_class):
        """Test do_control properly handles and returns integration errors."""
        entity = Entity.objects.create(
            name='Test Switch',
            entity_type_str='SWITCH'
        )
        entity_state = EntityState.objects.create(
            entity=entity,
            entity_state_type_str='ON_OFF'
        )
        
        controller = Controller.objects.create(
            name='Broken Switch',
            entity_state=entity_state,
            controller_type_str='DEFAULT',
            integration_id='unreliable_integration',
            integration_name='Unreliable Integration'
        )
        
        # Mock integration failure
        mock_control_result = IntegrationControlResult(
            new_value='',
            error_list=['Device is offline', 'Connection timeout']
        )
        mock_integration_controller = Mock()
        mock_integration_controller.do_control.return_value = mock_control_result
        
        mock_integration_gateway = Mock()
        mock_integration_gateway.get_controller.return_value = mock_integration_controller
        
        mock_integration_manager = Mock()
        mock_integration_manager.get_integration_gateway.return_value = mock_integration_gateway
        mock_integration_manager_class.return_value = mock_integration_manager
        
        # Test error handling
        manager = ControllerManager()
        result = manager.do_control(controller=controller, control_value='on')
        
        # Test that error information is properly returned
        self.assertIsInstance(result, IntegrationControlResult)
        self.assertTrue(result.has_errors)
        self.assertEqual(result.error_list, ['Device is offline', 'Connection timeout'])
        self.assertEqual(result.new_value, '')
        return

    @patch.object(ControllerManager, '_instance', None)
    @patch('hi.apps.control.controller_manager.IntegrationManager')
    def test_do_control_async_returns_same_result_as_sync(self, mock_integration_manager_class):
        """Test async control returns identical result to sync version."""
        entity = Entity.objects.create(
            name='Test Dimmer',
            entity_type_str='LIGHT'
        )
        entity_state = EntityState.objects.create(
            entity=entity,
            entity_state_type_str='DISCRETE'
        )
        
        controller = Controller.objects.create(
            name='Bedroom Dimmer',
            entity_state=entity_state,
            controller_type_str='DEFAULT',
            integration_id='zigbee_integration',
            integration_name='Zigbee Integration'
        )
        
        # Mock successful dimmer control
        mock_control_result = IntegrationControlResult(
            new_value='75',
            error_list=[]
        )
        mock_integration_controller = Mock()
        mock_integration_controller.do_control.return_value = mock_control_result
        
        mock_integration_gateway = Mock()
        mock_integration_gateway.get_controller.return_value = mock_integration_controller
        
        mock_integration_manager = Mock()
        mock_integration_manager.get_integration_gateway.return_value = mock_integration_gateway
        mock_integration_manager_class.return_value = mock_integration_manager
        
        # Test both sync and async produce same result
        manager = ControllerManager()
        sync_result = manager.do_control(controller=controller, control_value='75')
        
        async def run_async_test():
            return await manager.do_control_async(controller=controller, control_value='75')
        
        async_result = asyncio.run(run_async_test())
        
        # Both should return identical IntegrationControlResult objects
        self.assertEqual(sync_result.has_errors, async_result.has_errors)
        self.assertEqual(sync_result.error_list, async_result.error_list)
        self.assertEqual(sync_result.new_value, async_result.new_value)
        
        # Verify both called integration with same parameters
        self.assertEqual(mock_integration_controller.do_control.call_count, 2)
        for call in mock_integration_controller.do_control.call_args_list:
            self.assertEqual(call.kwargs['control_value'], '75')
        return
