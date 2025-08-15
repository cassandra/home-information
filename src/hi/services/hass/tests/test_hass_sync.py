import json
import os
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase, TransactionTestCase
from django.db import transaction

from hi.apps.common.processing_result import ProcessingResult
from hi.apps.entity.models import Entity
from hi.integrations.transient_models import IntegrationKey

from hi.services.hass.hass_sync import HassSynchronizer
from hi.services.hass.hass_models import HassDevice, HassState
from hi.services.hass.hass_metadata import HassMetaData


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


class TestHassSynchronizerSyncMethod(TransactionTestCase):
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
        
        # Mock lock context manager
        mock_lock_context.return_value.__enter__ = Mock()
        mock_lock_context.return_value.__exit__ = Mock()
        
        result = self.synchronizer.sync()
        
        # Verify error handling
        self.assertEqual(result.title, 'HAss Sync Result')
        self.assertIn('Database connection failed', result.error_list[0])
    
    @patch('hi.services.hass.hass_sync.ExclusionLockContext')
    @patch.object(HassSynchronizer, '_sync_helper')
    @patch('hi.services.hass.hass_sync.logger')
    def test_sync_logs_start_and_end(self, mock_logger, mock_sync_helper, mock_lock_context):
        """Test sync method logs debug messages for start and end"""
        mock_sync_helper.return_value = ProcessingResult(title='HAss Sync Result')
        
        # Mock lock context manager
        mock_lock_context.return_value.__enter__ = Mock()
        mock_lock_context.return_value.__exit__ = Mock()
        
        self.synchronizer.sync()
        
        # Verify debug logging
        mock_logger.debug.assert_any_call('HAss integration sync started.')
        mock_logger.debug.assert_any_call('HAss integration sync ended.')


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


class TestHassSynchronizerEntityOperations(TransactionTestCase):
    """Test entity creation, update, and removal operations"""
    
    def setUp(self):
        self.synchronizer = HassSynchronizer()
    
    @patch('hi.services.hass.hass_sync.HassConverter.create_models_for_hass_device')
    @patch.object(HassSynchronizer, 'hass_manager')
    def test_create_entity_success(self, mock_hass_manager, mock_create_models):
        """Test successful entity creation"""
        # Setup mocks
        mock_manager = Mock()
        mock_manager.should_add_alarm_events = True
        mock_hass_manager.return_value = mock_manager
        
        mock_device = Mock(spec=HassDevice)
        mock_entity = Mock(spec=Entity)
        mock_entity.__str__ = Mock(return_value='light.living_room')
        mock_create_models.return_value = mock_entity
        
        result = ProcessingResult(title='Test')
        
        self.synchronizer._create_entity(mock_device, result)
        
        # Verify model creation was called correctly
        mock_create_models.assert_called_once_with(
            hass_device=mock_device,
            add_alarm_events=True
        )
        
        # Verify result message
        self.assertIn('Created HAss entity: light.living_room', result.message_list)
    
    @patch('hi.services.hass.hass_sync.HassConverter.update_models_for_hass_device')
    def test_update_entity_success(self, mock_update_models):
        """Test successful entity update"""
        mock_entity = Mock(spec=Entity)
        mock_device = Mock(spec=HassDevice)
        
        # Mock update messages
        update_messages = [
            'Updated entity attributes',
            'Updated entity state'
        ]
        mock_update_models.return_value = update_messages
        
        result = ProcessingResult(title='Test')
        
        self.synchronizer._update_entity(mock_entity, mock_device, result)
        
        # Verify update was called
        mock_update_models.assert_called_once_with(
            entity=mock_entity,
            hass_device=mock_device
        )
        
        # Verify messages added to result
        for message in update_messages:
            self.assertIn(message, result.message_list)
    
    @patch.object(HassSynchronizer, '_remove_entity_intelligently')
    def test_remove_entity_calls_intelligent_removal(self, mock_remove_intelligently):
        """Test entity removal uses intelligent deletion"""
        mock_entity = Mock(spec=Entity)
        result = ProcessingResult(title='Test')
        
        self.synchronizer._remove_entity(mock_entity, result)
        
        # Verify intelligent removal was called
        mock_remove_intelligently.assert_called_once_with(mock_entity, result, 'HASS')


class TestHassSynchronizerGetExistingEntities(TestCase):
    """Test _get_existing_hass_entities method"""
    
    def setUp(self):
        self.synchronizer = HassSynchronizer()
    
    @patch('hi.services.hass.hass_sync.Entity.objects')
    def test_get_existing_entities_success(self, mock_entity_objects):
        """Test successful retrieval of existing entities"""
        # Mock entities with valid integration keys
        mock_entity1 = Mock(spec=Entity)
        mock_entity1.id = 1
        mock_entity1.integration_key = IntegrationKey(
            integration_id='hass', 
            integration_name='light.living_room'
        )
        
        mock_entity2 = Mock(spec=Entity)
        mock_entity2.id = 2
        mock_entity2.integration_key = IntegrationKey(
            integration_id='hass',
            integration_name='switch.kitchen'
        )
        
        mock_queryset = [mock_entity1, mock_entity2]
        mock_entity_objects.filter.return_value = mock_queryset
        
        result = ProcessingResult(title='Test')
        
        integration_key_to_entity = self.synchronizer._get_existing_hass_entities(result)
        
        # Verify filter was called correctly
        mock_entity_objects.filter.assert_called_once_with(
            integration_id=HassMetaData.integration_id
        )
        
        # Verify entities mapped correctly
        self.assertEqual(len(integration_key_to_entity), 2)
        self.assertIn(mock_entity1.integration_key, integration_key_to_entity)
        self.assertIn(mock_entity2.integration_key, integration_key_to_entity)
        self.assertEqual(integration_key_to_entity[mock_entity1.integration_key], mock_entity1)
        self.assertEqual(integration_key_to_entity[mock_entity2.integration_key], mock_entity2)
    
    @patch('hi.services.hass.hass_sync.Entity.objects')
    def test_get_existing_entities_handles_invalid_integration_key(self, mock_entity_objects):
        """Test handling of entities without valid integration keys"""
        # Mock entity without integration key
        mock_entity = Mock(spec=Entity)
        mock_entity.id = 123
        mock_entity.integration_key = None
        mock_entity.__str__ = Mock(return_value='Entity 123')
        
        mock_queryset = [mock_entity]
        mock_entity_objects.filter.return_value = mock_queryset
        
        result = ProcessingResult(title='Test')
        
        integration_key_to_entity = self.synchronizer._get_existing_hass_entities(result)
        
        # Verify error was recorded
        self.assertIn('Entity found without valid HAss Id: Entity 123', result.error_list)
        
        # Verify mock integration key was created
        self.assertEqual(len(integration_key_to_entity), 1)
        
        # Verify mock key uses entity ID + offset
        mock_key = list(integration_key_to_entity.keys())[0]
        self.assertEqual(mock_key.integration_id, HassMetaData.integration_id)
        self.assertEqual(mock_key.integration_name, '1000123')  # 1000000 + entity.id
    
    @patch('hi.services.hass.hass_sync.Entity.objects')
    def test_get_existing_entities_empty_queryset(self, mock_entity_objects):
        """Test handling of empty entity queryset"""
        mock_entity_objects.filter.return_value = []
        
        result = ProcessingResult(title='Test')
        
        integration_key_to_entity = self.synchronizer._get_existing_hass_entities(result)
        
        # Verify empty result
        self.assertEqual(len(integration_key_to_entity), 0)
        self.assertEqual(len(result.error_list), 0)


class TestHassSynchronizerTransactionHandling(TransactionTestCase):
    """Test database transaction handling during sync operations"""
    
    def setUp(self):
        self.synchronizer = HassSynchronizer()
    
    @patch('hi.services.hass.hass_sync.HassConverter.hass_device_to_integration_key')
    @patch('hi.services.hass.hass_sync.HassConverter.hass_states_to_hass_devices')
    @patch.object(HassSynchronizer, '_get_existing_hass_entities')
    @patch.object(HassSynchronizer, 'hass_manager')
    def test_sync_helper_uses_transaction_atomic(self, mock_hass_manager, mock_get_entities,
                                                mock_states_to_devices, mock_device_to_key):
        """Test that sync helper uses atomic transactions"""
        # Setup mocks
        mock_manager = Mock()
        mock_manager.hass_client = Mock()
        mock_manager.fetch_hass_states_from_api.return_value = {}
        mock_hass_manager.return_value = mock_manager
        
        mock_get_entities.return_value = {}
        mock_states_to_devices.return_value = {}
        
        with patch('hi.services.hass.hass_sync.transaction.atomic') as mock_atomic:
            # Mock atomic context manager
            mock_atomic.return_value.__enter__ = Mock()
            mock_atomic.return_value.__exit__ = Mock()
            
            self.synchronizer._sync_helper()
            
            # Verify atomic transaction was used
            mock_atomic.assert_called_once()
    
    @patch('hi.services.hass.hass_sync.HassConverter.hass_device_to_integration_key')
    @patch('hi.services.hass.hass_sync.HassConverter.hass_states_to_hass_devices')
    @patch.object(HassSynchronizer, '_get_existing_hass_entities')
    @patch.object(HassSynchronizer, 'hass_manager')
    def test_entity_operations_within_transaction(self, mock_hass_manager, mock_get_entities,
                                                 mock_states_to_devices, mock_device_to_key):
        """Test that entity create/update/remove operations happen within transaction"""
        # Setup test scenario with entities to create, update, and remove
        mock_manager = Mock()
        mock_manager.hass_client = Mock()
        mock_manager.fetch_hass_states_from_api.return_value = {}
        mock_hass_manager.return_value = mock_manager
        
        # Mock existing entity to be removed
        existing_key = IntegrationKey(integration_id='hass', integration_name='old.entity')
        existing_entity = Mock(spec=Entity)
        mock_get_entities.return_value = {existing_key: existing_entity}
        
        # Mock new device to be created
        new_device = Mock(spec=HassDevice)
        mock_states_to_devices.return_value = {'new_device': new_device}
        
        new_key = IntegrationKey(integration_id='hass', integration_name='new.entity')
        mock_device_to_key.return_value = new_key
        
        with patch.object(self.synchronizer, '_create_entity') as mock_create, \
             patch.object(self.synchronizer, '_remove_entity') as mock_remove, \
             patch('hi.services.hass.hass_sync.transaction.atomic') as mock_atomic:
            
            # Mock atomic context manager
            mock_atomic.return_value.__enter__ = Mock()
            mock_atomic.return_value.__exit__ = Mock()
            
            self.synchronizer._sync_helper()
            
            # Verify operations were called within transaction context
            mock_create.assert_called_once_with(hass_device=new_device, result=mock_atomic.return_value.__enter__.return_value)
            mock_remove.assert_called_once_with(entity=existing_entity, result=mock_atomic.return_value.__enter__.return_value)


class TestHassSynchronizerWithRealData(TestCase):
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
    def test_sync_helper_handles_converter_failure(self, mock_hass_manager, 
                                                  mock_get_entities, mock_states_to_devices):
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
    
    @patch('hi.services.hass.hass_sync.HassManager')
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