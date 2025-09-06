import json
import logging
import os
from unittest.mock import Mock, patch
from django.test import TestCase

from hi.apps.common.processing_result import ProcessingResult
from hi.apps.entity.models import Entity
from hi.integrations.transient_models import IntegrationKey

from hi.services.hass.hass_sync import HassSynchronizer
from hi.services.hass.hass_models import HassDevice, HassState

logging.disable(logging.CRITICAL)


class TestHassSynchronizerInitialization(TestCase):
    """Test HassSynchronizer initialization and basic setup"""
    
    def test_init_creates_instance_successfully(self):
        """Test HassSynchronizer initialization"""
        synchronizer = HassSynchronizer()
        self.assertIsInstance(synchronizer, HassSynchronizer)
    
    def test_synchronization_lock_name_constant(self):
        """Test SYNCHRONIZATION_LOCK_NAME constant is properly defined"""
        self.assertEqual(HassSynchronizer.SYNCHRONIZATION_LOCK_NAME, 'hass_integration_sync')
    
    def test_inherits_from_mixins(self):
        """Test that HassSynchronizer inherits from required mixins"""
        synchronizer = HassSynchronizer()
        
        # Should inherit from HassMixin
        self.assertTrue(hasattr(synchronizer, 'hass_manager'))
        
        # Should inherit from IntegrationSyncMixin  
        self.assertTrue(hasattr(synchronizer, '_remove_entity_intelligently'))


class TestHassSynchronizerSyncMethod(TestCase):
    """Test main sync() method with database transactions"""
    
    def setUp(self):
        self.synchronizer = HassSynchronizer()
    
    @patch('hi.services.hass.hass_sync.ExclusionLockContext')
    @patch.object(HassSynchronizer, '_sync_helper')
    def test_sync_success_with_lock(self, mock_sync_helper, mock_lock_context):
        """Test successful sync operation with proper locking"""
        # Mock successful sync result
        expected_result = ProcessingResult(title='HAss Sync Result')
        expected_result.message_list.append('Sync completed successfully')
        mock_sync_helper.return_value = expected_result
        
        # Mock lock context manager
        mock_lock_context.return_value.__enter__ = Mock()
        mock_lock_context.return_value.__exit__ = Mock()
        
        result = self.synchronizer.sync()
        
        # Verify lock was used with correct name
        mock_lock_context.assert_called_once_with(name='hass_integration_sync')
        
        # Verify helper was called
        mock_sync_helper.assert_called_once()
        
        # Verify result
        self.assertEqual(result, expected_result)
        self.assertIn('Sync completed successfully', result.message_list)
    
    @patch('hi.services.hass.hass_sync.ExclusionLockContext')
    @patch.object(HassSynchronizer, '_sync_helper')
    def test_sync_handles_runtime_error(self, mock_sync_helper, mock_lock_context):
        """Test sync method handles RuntimeError exceptions"""
        # Mock RuntimeError in sync helper
        mock_sync_helper.side_effect = RuntimeError("Database connection failed")
        
        # Mock lock context manager properly
        mock_context = Mock()
        mock_context.__enter__ = Mock()
        mock_context.__exit__ = Mock(return_value=False)
        mock_lock_context.return_value = mock_context
        
        result = self.synchronizer.sync()
        
        # Verify error handling
        self.assertEqual(result.title, 'HAss Sync Result')
        self.assertIn('Database connection failed', result.error_list[0])
    
    @patch('hi.services.hass.hass_sync.ExclusionLockContext')
    @patch.object(HassSynchronizer, '_sync_helper')
    def test_sync_returns_error_result_on_exception(self, mock_sync_helper, mock_lock_context):
        """Test sync method returns proper error result when _sync_helper raises exception"""
        # Mock RuntimeError in sync helper
        mock_sync_helper.side_effect = RuntimeError("Database connection failed")
        
        # Mock lock context manager properly
        mock_context = Mock()
        mock_context.__enter__ = Mock()
        mock_context.__exit__ = Mock(return_value=False)
        mock_lock_context.return_value = mock_context
        
        result = self.synchronizer.sync()
        
        # Verify actual error result structure and content
        self.assertEqual(result.title, 'HAss Sync Result')
        self.assertEqual(len(result.error_list), 1)
        self.assertIn('Database connection failed', result.error_list[0])
        self.assertEqual(len(result.message_list), 0)  # No success messages on error


class TestHassSynchronizerSyncHelper(TestCase):
    """Test _sync_helper method logic"""
    
    def setUp(self):
        self.synchronizer = HassSynchronizer()
        
        # Mock hass_manager and dependencies
        self.mock_manager = Mock()
        self.mock_client = Mock()
        self.mock_manager.hass_client = self.mock_client
        
    @patch.object(HassSynchronizer, 'hass_manager')
    def test_sync_helper_client_not_available(self, mock_hass_manager):
        """Test sync helper handles missing HASS client"""
        # Mock manager without client
        self.mock_manager.hass_client = None
        mock_hass_manager.return_value = self.mock_manager
        
        result = self.synchronizer._sync_helper()
        
        self.assertEqual(result.title, 'HAss Sync Result')
        self.assertIn('Sync problem. HAss integration disabled?', result.error_list)
    
    @patch('hi.services.hass.hass_sync.HassConverter.hass_states_to_hass_devices')
    @patch('hi.services.hass.hass_sync.HassConverter.hass_device_to_integration_key')
    @patch.object(HassSynchronizer, '_get_existing_hass_entities')
    @patch.object(HassSynchronizer, 'hass_manager')
    @patch('hi.services.hass.hass_sync.transaction')
    def test_sync_helper_successful_flow(self, mock_transaction, mock_hass_manager,
                                         mock_get_entities, mock_device_to_key,
                                         mock_states_to_devices):
        """Test successful sync helper flow with data processing"""
        # Setup mocks
        mock_hass_manager.return_value = self.mock_manager
        
        # Mock API data
        mock_hass_states = {
            'light.living_room': Mock(spec=HassState),
            'switch.kitchen': Mock(spec=HassState)
        }
        self.mock_manager.fetch_hass_states_from_api.return_value = mock_hass_states
        
        # Mock existing entities
        mock_entities = {}
        mock_get_entities.return_value = mock_entities
        
        # Mock device conversion
        mock_device = Mock(spec=HassDevice)
        mock_devices = {'device_1': mock_device}
        mock_states_to_devices.return_value = mock_devices
        
        # Mock integration key conversion
        mock_key = IntegrationKey(integration_id='hass', integration_name='light.living_room')
        mock_device_to_key.return_value = mock_key
        
        # Mock transaction context
        mock_transaction.atomic.return_value.__enter__ = Mock()
        mock_transaction.atomic.return_value.__exit__ = Mock()
        
        with patch.object(self.synchronizer, '_create_entity') as mock_create:
            result = self.synchronizer._sync_helper()
        
        # Verify API was called
        self.mock_manager.fetch_hass_states_from_api.assert_called_once()
        
        # Verify data processing calls
        mock_get_entities.assert_called_once()
        mock_states_to_devices.assert_called_once_with(hass_entity_id_to_state=mock_hass_states)
        
        # Verify entity creation was called
        mock_create.assert_called_once()
        
        # Verify result messages
        self.assertIn('Found 2 current HAss states.', result.message_list)
        self.assertIn('Found 0 existing HAss entities.', result.message_list)
        self.assertIn('Found 1 current HAss devices.', result.message_list)


class TestHassSynchronizerStateConversion(TestCase):
    """Test HassSynchronizer with real HASS API data"""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Load real HASS API response data
        test_data_dir = os.path.join(os.path.dirname(__file__), 'data')
        try:
            with open(os.path.join(test_data_dir, 'hass-states.json'), 'r') as f:
                cls.real_hass_states_data = json.load(f)
        except FileNotFoundError:
            cls.real_hass_states_data = []
    
    def setUp(self):
        self.synchronizer = HassSynchronizer()
    
    @patch('hi.services.hass.hass_sync.HassConverter.hass_states_to_hass_devices')
    @patch('hi.services.hass.hass_sync.HassConverter.create_hass_state')
    @patch.object(HassSynchronizer, '_get_existing_hass_entities')
    @patch.object(HassSynchronizer, 'hass_manager')
    def test_sync_helper_with_real_hass_data_structure(self, mock_hass_manager,
                                                       mock_get_entities, mock_create_state,
                                                       mock_states_to_devices):
        """Test sync helper processes real HASS API data structure correctly"""
        if not self.real_hass_states_data:
            self.skipTest("No real HASS data available for testing")
        
        # Setup mocks with real data
        mock_manager = Mock()
        mock_manager.hass_client = Mock()
        
        # Convert real data to HassState mocks
        mock_hass_states = {}
        for entity_data in self.real_hass_states_data[:5]:  # Use first 5 entities
            entity_id = entity_data['entity_id']
            mock_state = Mock(spec=HassState)
            mock_state.entity_id = entity_id
            mock_create_state.return_value = mock_state
            mock_hass_states[entity_id] = mock_state
        
        mock_manager.fetch_hass_states_from_api.return_value = mock_hass_states
        mock_hass_manager.return_value = mock_manager
        
        mock_get_entities.return_value = {}
        mock_states_to_devices.return_value = {}
        
        with patch('hi.services.hass.hass_sync.transaction.atomic') as mock_atomic:
            mock_atomic.return_value.__enter__ = Mock()
            mock_atomic.return_value.__exit__ = Mock()
            
            result = self.synchronizer._sync_helper()
        
        # Verify real data was processed
        expected_count = len(mock_hass_states)
        self.assertIn(f'Found {expected_count} current HAss states.', result.message_list)
        
        # Verify API fetch was called
        mock_manager.fetch_hass_states_from_api.assert_called_once()
    
    def test_real_data_entity_id_diversity(self):
        """Test that real HASS data contains diverse entity types for comprehensive testing"""
        if not self.real_hass_states_data:
            self.skipTest("No real HASS data available for testing")
        
        entity_ids = [entity['entity_id'] for entity in self.real_hass_states_data]
        
        # Extract domains
        domains = set()
        for entity_id in entity_ids:
            if '.' in entity_id:
                domain = entity_id.split('.', 1)[0]
                domains.add(domain)
        
        # Verify diverse entity types for sync testing
        expected_domains = ['camera', 'sensor', 'script']
        for expected_domain in expected_domains:
            self.assertIn(expected_domain, domains, 
                          f"Should have {expected_domain} entities for sync testing")
        
        # Verify substantial data for comprehensive sync testing
        self.assertGreaterEqual(len(entity_ids), 10, "Should have substantial entities for sync testing")


class TestHassSynchronizerTransactionBehavior(TestCase):
    """Test transaction handling and atomicity in sync operations"""
    
    def setUp(self):
        self.synchronizer = HassSynchronizer()
    
    def test_sync_helper_executes_entity_operations_atomically(self):
        """Test that all entity operations in sync_helper execute within single transaction"""
        with patch.object(self.synchronizer, 'hass_manager') as mock_hass_manager, \
             patch.object(self.synchronizer, '_get_existing_hass_entities') as mock_get_entities, \
             patch.object(self.synchronizer, '_create_entity') as mock_create, \
             patch.object(self.synchronizer, '_remove_entity') as mock_remove:
            
            # Setup manager
            mock_manager = Mock()
            mock_manager.hass_client = Mock()
            mock_hass_manager.return_value = mock_manager
            
            # Setup scenario: one new device, one entity to remove
            api_states = {'light.new': self._create_mock_hass_state('light.new', 'light', 'on')}
            mock_manager.fetch_hass_states_from_api.return_value = api_states
            
            old_entity = Mock(spec=Entity)
            old_key = IntegrationKey(integration_id='hass', integration_name='old_device')
            mock_get_entities.return_value = {old_key: old_entity}
            
            # Track transaction usage
            with patch('hi.services.hass.hass_sync.transaction.atomic') as mock_atomic:
                mock_atomic.return_value.__enter__ = Mock()
                mock_atomic.return_value.__exit__ = Mock()
                
                result = self.synchronizer._sync_helper()
                
                # Verify atomic transaction was used exactly once
                mock_atomic.assert_called_once()
                
                # Verify both operations occurred (would be within same transaction)
                mock_create.assert_called_once()
                mock_remove.assert_called_once()
                
                # Verify successful result
                self.assertEqual(len(result.error_list), 0)
    
    def test_sync_helper_rollback_behavior_on_entity_operation_failure(self):
        """Test that transaction rollback works when entity operations fail"""
        with patch.object(self.synchronizer, 'hass_manager') as mock_hass_manager, \
             patch.object(self.synchronizer, '_get_existing_hass_entities') as mock_get_entities:
            
            # Setup manager  
            mock_manager = Mock()
            mock_manager.hass_client = Mock()
            mock_hass_manager.return_value = mock_manager
            
            # Setup API data
            api_states = {'light.test': self._create_mock_hass_state('light.test', 'light', 'on')}
            mock_manager.fetch_hass_states_from_api.return_value = api_states
            mock_get_entities.return_value = {}
            
            # Mock entity creation failure within transaction
            with patch.object(self.synchronizer, '_create_entity') as mock_create:
                mock_create.side_effect = Exception("Entity creation failed")
                
                # Transaction should propagate the exception (allowing rollback)
                with self.assertRaises(Exception) as context:
                    self.synchronizer._sync_helper()
                
                self.assertEqual(str(context.exception), "Entity creation failed")
    
    def _create_mock_hass_state(self, entity_id, domain, state):
        """Helper to create mock HASS state for testing"""
        hass_state = Mock(spec=HassState)
        hass_state.entity_id = entity_id
        hass_state.domain = domain
        hass_state.state_value = state
        hass_state.entity_name_sans_prefix = entity_id.split('.', 1)[1]
        hass_state.entity_name_sans_suffix = hass_state.entity_name_sans_prefix
        hass_state.device_group_id = None
        hass_state.attributes = {}
        hass_state.device_class = None
        hass_state.friendly_name = None
        return hass_state


class TestHassSynchronizerErrorScenarios(TestCase):
    """Test comprehensive error handling scenarios"""
    
    def setUp(self):
        self.synchronizer = HassSynchronizer()
    
    @patch('hi.services.hass.hass_sync.ExclusionLockContext')
    def test_sync_handles_exclusion_lock_timeout(self, mock_lock_context):
        """Test sync handles exclusion lock timeout gracefully"""
        # Mock lock timeout
        mock_lock_context.side_effect = RuntimeError("Lock acquisition timeout")
        
        result = self.synchronizer.sync()
        
        # Verify error handling
        self.assertEqual(result.title, 'HAss Sync Result')
        self.assertIn('Lock acquisition timeout', result.error_list[0])
    
    @patch.object(HassSynchronizer, 'hass_manager')
    def test_sync_helper_handles_api_fetch_failure(self, mock_hass_manager):
        """Test sync helper handles API fetch failures"""
        # Mock manager with client that fails API fetch
        mock_manager = Mock()
        mock_manager.hass_client = Mock()
        mock_manager.fetch_hass_states_from_api.side_effect = Exception("API connection failed")
        mock_hass_manager.return_value = mock_manager
        
        with self.assertRaises(Exception) as context:
            self.synchronizer._sync_helper()
        
        self.assertEqual(str(context.exception), "API connection failed")
    
    @patch('hi.services.hass.hass_sync.HassConverter.hass_states_to_hass_devices')
    @patch.object(HassSynchronizer, '_get_existing_hass_entities')
    @patch.object(HassSynchronizer, 'hass_manager')
    def test_sync_helper_handles_converter_failure(
            self, mock_hass_manager, 
            mock_get_entities, mock_states_to_devices ):
        """Test sync helper handles converter failures"""
        # Setup mocks
        mock_manager = Mock()
        mock_manager.hass_client = Mock()
        mock_manager.fetch_hass_states_from_api.return_value = {'test': Mock()}
        mock_hass_manager.return_value = mock_manager
        
        mock_get_entities.return_value = {}
        
        # Mock converter failure
        mock_states_to_devices.side_effect = ValueError("Invalid state data format")
        
        with self.assertRaises(ValueError) as context:
            self.synchronizer._sync_helper()
        
        self.assertEqual(str(context.exception), "Invalid state data format")
    
    @patch('hi.services.hass.hass_sync.Entity.objects')
    def test_get_existing_entities_handles_database_error(self, mock_entity_objects):
        """Test _get_existing_hass_entities handles database errors"""
        # Mock database query failure
        mock_entity_objects.filter.side_effect = Exception("Database connection lost")
        
        result = ProcessingResult(title='Test')
        
        with self.assertRaises(Exception) as context:
            self.synchronizer._get_existing_hass_entities(result)
        
        self.assertEqual(str(context.exception), "Database connection lost")


class TestHassSynchronizerMixinIntegration(TestCase):
    """Test integration with HassMixin and IntegrationSyncMixin"""
    
    def setUp(self):
        self.synchronizer = HassSynchronizer()
    
    @patch('hi.services.hass.hass_mixins.HassManager')
    def test_hass_mixin_integration(self, mock_manager_class):
        """Test HassMixin integration provides hass_manager access"""
        mock_manager_instance = Mock()
        mock_manager_class.return_value = mock_manager_instance
        
        # Should be able to access hass_manager through mixin
        result = self.synchronizer.hass_manager()
        
        self.assertEqual(result, mock_manager_instance)
    
    def test_integration_sync_mixin_methods_available(self):
        """Test IntegrationSyncMixin methods are available"""
        # Should have _remove_entity_intelligently method from mixin
        self.assertTrue(hasattr(self.synchronizer, '_remove_entity_intelligently'))
        self.assertTrue(callable(getattr(self.synchronizer, '_remove_entity_intelligently')))
    
    @patch.object(HassSynchronizer, '_remove_entity_intelligently')
    def test_remove_entity_uses_mixin_method(self, mock_remove_intelligently):
        """Test _remove_entity properly delegates to mixin method"""
        mock_entity = Mock(spec=Entity)
        result = ProcessingResult(title='Test')
        
        self.synchronizer._remove_entity(mock_entity, result)
        
        # Verify mixin method was called with correct parameters
        mock_remove_intelligently.assert_called_once_with(mock_entity, result, 'HASS')
