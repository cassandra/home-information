import json
import logging
import os
from unittest.mock import Mock, patch, call
from django.test import TestCase

from hi.apps.attribute.enums import AttributeType, AttributeValueType
from hi.apps.entity.models import Entity, EntityAttribute
from hi.apps.event.models import EventDefinition
from hi.apps.sense.models import Sensor

from hi.integrations.entity_operations import EntityIntegrationOperations
from hi.integrations.integration_manager import IntegrationManager
from hi.integrations.sync_result import IntegrationSyncResult
from hi.integrations.transient_models import IntegrationKey

from hi.services.zoneminder.zm_sync import ZoneMinderSynchronizer
from hi.services.zoneminder.zm_metadata import ZmMetaData

logging.disable(logging.CRITICAL)


class TestZoneMinderSynchronizerLockBehavior(TestCase):
    """Test database lock coordination with exception handling"""
    
    def setUp(self):
        self.synchronizer = ZoneMinderSynchronizer()
    
    @patch('hi.integrations.integration_synchronizer.ExclusionLockContext')
    def test_sync_uses_exclusion_lock(self, mock_lock_context):
        """Test sync method uses exclusion lock and returns sync results"""
        # Mock a successful lock context
        mock_lock_context.return_value.__enter__ = Mock()
        mock_lock_context.return_value.__exit__ = Mock(return_value=False)
        
        # Mock zm_manager to simulate disabled client
        mock_manager = Mock()
        mock_manager.zm_client = None
        self.synchronizer._zm_manager = mock_manager
        
        result = self.synchronizer.sync(is_initial_import=True)
        
        # Test lock usage
        mock_lock_context.assert_called_once_with(name='integrations_sync')
        
        # Test actual behavior: should return result with error when client disabled
        self.assertEqual(result.title, 'Import Result')
        self.assertGreater(len(result.error_list), 0)
        self.assertIn('Sync problem. ZM integration disabled?', result.error_list[0])
    
    @patch('hi.integrations.integration_synchronizer.ExclusionLockContext')
    def test_sync_handles_lock_runtime_error(self, mock_lock_context):
        """Test sync method handles RuntimeError from lock context and returns proper error result"""
        lock_error_msg = "Lock acquisition failed"
        mock_lock_context.side_effect = RuntimeError(lock_error_msg)
        
        result = self.synchronizer.sync(is_initial_import=True)
        
        # Test error handling behavior
        self.assertEqual(result.title, 'Import Result')
        self.assertEqual(len(result.error_list), 1)
        self.assertIn(lock_error_msg, result.error_list[0])
        
        # Test that no sync operations were attempted
        self.assertEqual(len(result.info_list), 0)
        
        # Test that result is properly formed for error condition
        self.assertIsNotNone(result.title)
        self.assertIsInstance(result.error_list, list)


class TestZoneMinderSynchronizerSyncHelper(TestCase):
    """Test main sync helper logic and flow control"""
    
    def setUp(self):
        self.synchronizer = ZoneMinderSynchronizer()
        
        # Mock the zm_manager
        self.mock_manager = Mock()
        self.synchronizer._zm_manager = self.mock_manager
    
    def test_sync_impl_client_not_available(self):
        """Test sync helper handles missing ZM client gracefully"""
        self.mock_manager.zm_client = None
        
        result = self.synchronizer._sync_impl(is_initial_import=True)
        
        self.assertEqual(result.title, 'Import Result')
        self.assertIn('Sync problem. ZM integration disabled?', result.error_list[0])
    
    def test_sync_impl_calls_both_sync_methods(self):
        """Test sync helper coordinates state and monitor sync and aggregates their results"""
        self.mock_manager.zm_client = Mock()  # Client available
        
        # Mock the sync methods to simulate successful operations.
        # _sync_monitors now returns the list of imported entities so
        # the caller can assemble the "Monitors" group.
        def mock_sync_states(result):
            result.info_list.append('States synced successfully')
            return result

        def mock_sync_monitors(result):
            result.info_list.append('Monitors synced successfully')
            return []
        
        # Patch the methods to track their execution and simulate behavior
        with patch.object(self.synchronizer, '_sync_states', side_effect=mock_sync_states) as mock_sync_states, \
             patch.object(self.synchronizer, '_sync_monitors', side_effect=mock_sync_monitors) as mock_sync_monitors:
            
            result = self.synchronizer._sync_impl(is_initial_import=True)
            
            # Test coordination: both methods called with same result
            mock_sync_states.assert_called_once()
            mock_sync_monitors.assert_called_once()
            
            # Test result aggregation: messages from both operations
            self.assertEqual(result.title, 'Import Result')
            self.assertIn('States synced successfully', result.info_list)
            self.assertIn('Monitors synced successfully', result.info_list)
            
            # Test that sync_states was called before sync_monitors
            self.assertEqual(mock_sync_states.call_args[1]['result'], result)
            self.assertEqual(mock_sync_monitors.call_args[1]['result'], result)


class TestZoneMinderSynchronizerStateSync(TestCase):
    """Test state synchronization and value range updates"""
    
    def setUp(self):
        self.synchronizer = ZoneMinderSynchronizer()
        
        # Mock the zm_manager
        self.mock_manager = Mock()
        self.mock_manager._zm_integration_key.return_value = IntegrationKey(
            integration_id=ZmMetaData.integration_id,
            integration_name='system'
        )
        self.mock_manager._zm_run_state_integration_key.return_value = IntegrationKey(
            integration_id=ZmMetaData.integration_id,
            integration_name='run.state'
        )
        self.synchronizer._zm_manager = self.mock_manager
    
    @patch('hi.services.zoneminder.zm_sync.Entity.objects.filter_by_integration_key')
    @patch('hi.services.zoneminder.zm_sync.Sensor.objects.filter_by_integration_key')
    @patch.object(ZoneMinderSynchronizer, '_create_zm_entity')
    def test_sync_states_creates_zm_entity_when_missing(self, mock_create_entity, mock_sensor_filter, mock_entity_filter):
        """Test _sync_states creates ZM entity when it doesn't exist and verifies entity creation parameters"""
        # Mock ZM states
        mock_state1 = Mock()
        mock_state1.name.return_value = 'start'
        mock_state2 = Mock()
        mock_state2.name.return_value = 'stop'
        self.mock_manager.get_zm_states.return_value = [mock_state1, mock_state2]
        
        # No existing entity
        mock_entity_filter.return_value.first.return_value = None
        
        # Mock created entity to test return behavior
        mock_created_entity = Mock()
        mock_created_entity.name = 'ZoneMinder'
        mock_created_entity.id = 123
        
        # Simulate the actual behavior of _create_zm_entity
        def mock_create_behavior(run_state_name_label_dict, result):
            result.info_list.append(f'Created ZM entity: {mock_created_entity}')
            return mock_created_entity
        
        mock_create_entity.side_effect = mock_create_behavior
        
        # Mock sensor exists
        mock_sensor = Mock()
        mock_entity_state = Mock()
        mock_entity_state.value_range_dict = {'start': 'start', 'stop': 'stop'}
        mock_sensor.entity_state = mock_entity_state
        mock_sensor_filter.return_value.select_related.return_value.first.return_value = mock_sensor
        
        result = IntegrationSyncResult(title='Test')
        self.synchronizer._sync_states(result)
        
        # Verify entity creation was called with correct parameters
        expected_dict = {'start': 'start', 'stop': 'stop'}
        mock_create_entity.assert_called_once()
        call_args = mock_create_entity.call_args
        self.assertEqual(call_args[1]['run_state_name_label_dict'], expected_dict)
        
        # Verify result contains creation information
        self.assertGreater(len(result.info_list), 0)
        # Test behavior: should not have errors when successful
        self.assertEqual(len(result.error_list), 0)
    
    @patch('hi.services.zoneminder.zm_sync.Entity.objects.filter_by_integration_key')
    @patch('hi.services.zoneminder.zm_sync.Sensor.objects.filter_by_integration_key')
    def test_sync_states_missing_sensor_error(self, mock_sensor_filter, mock_entity_filter):
        """Test _sync_states handles missing run state sensor and stops processing gracefully"""
        # Mock states
        mock_state = Mock()
        mock_state.name.return_value = 'start'
        self.mock_manager.get_zm_states.return_value = [mock_state]
        
        # Entity exists
        mock_entity = Mock()
        mock_entity.name = 'ZoneMinder'
        mock_entity_filter.return_value.first.return_value = mock_entity
        
        # No sensor found
        mock_sensor_filter.return_value.select_related.return_value.first.return_value = None
        
        result = IntegrationSyncResult(title='Test')
        returned_result = self.synchronizer._sync_states(result)
        
        # Test behavior: function should handle error gracefully
        self.assertEqual(len(result.error_list), 1)
        self.assertIn('Missing ZoneMinder sensor for ZM state.', result.error_list[0])
        # Should return early without processing further
        self.assertIsNone(returned_result)
        # Should not have created any entities since sensor missing
        self.assertEqual(len(result.info_list), 0)
    
    @patch('hi.services.zoneminder.zm_sync.Entity.objects.filter_by_integration_key')
    @patch('hi.services.zoneminder.zm_sync.Sensor.objects.filter_by_integration_key')
    def test_sync_states_updates_value_range_when_changed(self, mock_sensor_filter, mock_entity_filter):
        """Test _sync_states updates value range when states change and persists changes"""
        # Mock new states
        mock_state1 = Mock()
        mock_state1.name.return_value = 'start'
        mock_state2 = Mock()
        mock_state2.name.return_value = 'pause'  # New state
        self.mock_manager.get_zm_states.return_value = [mock_state1, mock_state2]
        
        # Entity exists
        mock_entity = Mock()
        mock_entity.name = 'ZoneMinder'
        mock_entity_filter.return_value.first.return_value = mock_entity
        
        # Mock sensor with existing state
        mock_sensor = Mock()
        mock_entity_state = Mock()
        mock_entity_state.value_range_dict = {'start': 'start', 'stop': 'stop'}  # Old states
        mock_entity_state.save = Mock()
        mock_sensor.entity_state = mock_entity_state
        mock_sensor.name = 'ZM Run State'
        mock_sensor_filter.return_value.select_related.return_value.first.return_value = mock_sensor
        
        result = IntegrationSyncResult(title='Test')
        self.synchronizer._sync_states(result)
        
        # Test actual state transformation
        expected_new_dict = {'start': 'start', 'pause': 'pause'}
        self.assertEqual(mock_entity_state.value_range_dict, expected_new_dict)
        
        # Test persistence behavior
        mock_entity_state.save.assert_called_once()
        
        # Test that old values are completely replaced, not merged
        self.assertNotIn('stop', mock_entity_state.value_range_dict)
        
        # Test successful processing behavior
        self.assertEqual(len(result.error_list), 0)
        self.assertGreater(len(result.info_list), 0)
        # Verify the state dict is included in the message for debugging
        message = result.info_list[0]
        self.assertIn('Updated ZM state values to:', message)
        self.assertIn('start', message)
        self.assertIn('pause', message)
    
    @patch('hi.services.zoneminder.zm_sync.Entity.objects.filter_by_integration_key')
    @patch('hi.services.zoneminder.zm_sync.Sensor.objects.filter_by_integration_key')
    def test_sync_states_no_update_when_unchanged(self, mock_sensor_filter, mock_entity_filter):
        """Test _sync_states doesn't update when state values unchanged and preserves existing state"""
        # Mock states - identical to existing
        mock_state1 = Mock()
        mock_state1.name.return_value = 'start'
        mock_state2 = Mock()
        mock_state2.name.return_value = 'stop'
        self.mock_manager.get_zm_states.return_value = [mock_state1, mock_state2]
        
        # Entity exists
        mock_entity = Mock()
        mock_entity.name = 'ZoneMinder'
        mock_entity_filter.return_value.first.return_value = mock_entity
        
        # Mock sensor with same existing states
        mock_sensor = Mock()
        mock_entity_state = Mock()
        original_state_dict = {'start': 'start', 'stop': 'stop'}
        mock_entity_state.value_range_dict = original_state_dict.copy()  # Same states
        mock_entity_state.save = Mock()
        mock_sensor.entity_state = mock_entity_state
        mock_sensor.name = 'ZM Run State'
        mock_sensor_filter.return_value.select_related.return_value.first.return_value = mock_sensor
        
        result = IntegrationSyncResult(title='Test')
        self.synchronizer._sync_states(result)
        
        # Test no persistence when no changes
        mock_entity_state.save.assert_not_called()
        
        # Test state preservation - should be exactly the same
        self.assertEqual(mock_entity_state.value_range_dict, original_state_dict)
        
        # Test no error conditions
        self.assertEqual(len(result.error_list), 0)
        
        # Test no update messages generated
        update_messages = [msg for msg in result.info_list if 'Updated ZM state values' in msg]
        self.assertEqual(len(update_messages), 0)


class TestZoneMinderSynchronizerMonitorSync(TestCase):
    """Test monitor synchronization and entity lifecycle management"""
    
    def setUp(self):
        self.synchronizer = ZoneMinderSynchronizer()
        
        # Mock the zm_manager
        self.mock_manager = Mock()
        self.mock_manager.ZM_MONITOR_INTEGRATION_NAME_PREFIX = 'monitor'
        self.mock_manager._to_integration_key = Mock()
        self.synchronizer._zm_manager = self.mock_manager
    
    def test_sync_monitors_creates_new_entities(self):
        """Test _sync_monitors creates entities for new monitors and tracks sync results"""
        # Mock monitors from ZM
        mock_monitor = Mock()
        mock_monitor.id.return_value = 123
        mock_monitor.name.return_value = 'Test Camera'
        integration_key = IntegrationKey(integration_id='zm', integration_name='monitor.123')
        
        # Mock the individual sync methods to test coordination
        def mock_fetch_monitors(result):
            result.info_list.append('Fetched 1 monitor from ZM')
            return {integration_key: mock_monitor}
            
        def mock_get_existing(result):
            result.info_list.append('Found 0 existing items')
            return {}
            
        def mock_create_entity(zm_monitor, result):
            result.info_list.append(f'Created entity for monitor {zm_monitor.name.return_value}')
            return Mock()
        
        with patch.object(self.synchronizer, '_fetch_zm_monitors', side_effect=mock_fetch_monitors), \
             patch.object(self.synchronizer, '_get_existing_zm_monitor_entities', side_effect=mock_get_existing), \
             patch.object(self.synchronizer, '_create_monitor_entity', side_effect=mock_create_entity) as mock_create, \
             patch.object(self.synchronizer, '_update_entity') as mock_update, \
             patch.object(self.synchronizer, '_remove_entity') as mock_remove:
            
            result = IntegrationSyncResult(title='Test')
            self.synchronizer._sync_monitors(result)
            
            # Test creation path was taken
            mock_create.assert_called_once_with(zm_monitor=mock_monitor, result=result)
            mock_update.assert_not_called()
            mock_remove.assert_not_called()
            
            # Test result aggregation from all sync phases
            self.assertIn('Fetched 1 monitor from ZM', result.info_list)
            self.assertIn('Found 0 existing items', result.info_list)
            self.assertIn('Created entity for monitor Test Camera', result.info_list)
            
            # Test no errors in successful creation scenario
            self.assertEqual(len(result.error_list), 0)
    
    @patch.object(ZoneMinderSynchronizer, '_fetch_zm_monitors')
    @patch.object(ZoneMinderSynchronizer, '_get_existing_zm_monitor_entities')
    @patch.object(ZoneMinderSynchronizer, '_create_monitor_entity')
    @patch.object(ZoneMinderSynchronizer, '_update_entity')
    @patch.object(ZoneMinderSynchronizer, '_remove_entity')
    def test_sync_monitors_updates_existing_entities(self, mock_remove, mock_update, mock_create, mock_get_existing, mock_fetch):
        """Test _sync_monitors updates existing entities"""
        # Mock monitors and entities with same key
        mock_monitor = Mock()
        mock_entity = Mock()
        integration_key = IntegrationKey(integration_id='zm', integration_name='monitor.123')
        mock_fetch.return_value = {integration_key: mock_monitor}
        mock_get_existing.return_value = {integration_key: mock_entity}
        
        result = IntegrationSyncResult(title='Test')
        self.synchronizer._sync_monitors(result)
        
        mock_update.assert_called_once_with(entity=mock_entity, zm_monitor=mock_monitor, result=result)
        mock_create.assert_not_called()
        mock_remove.assert_not_called()
    
    def test_sync_monitors_removes_stale_entities(self):
        """Test _sync_monitors removes entities for deleted monitors and handles cleanup properly"""
        # Existing entity that should be removed
        mock_entity = Mock()
        mock_entity.name = 'Deleted Camera'
        mock_entity.id = 456
        integration_key = IntegrationKey(integration_id='zm', integration_name='monitor.123')
        
        # Mock the individual sync methods to test coordination
        def mock_fetch_monitors(result):
            result.info_list.append('Fetched 0 monitors from ZM')
            return {}  # No current monitors
            
        def mock_get_existing(result):
            result.info_list.append('Found 1 existing item')
            return {integration_key: mock_entity}
            
        def mock_remove_entity(entity, result):
            result.info_list.append(f'Removed stale entity {entity.name}')
        
        with patch.object(self.synchronizer, '_fetch_zm_monitors', side_effect=mock_fetch_monitors), \
             patch.object(self.synchronizer, '_get_existing_zm_monitor_entities', side_effect=mock_get_existing), \
             patch.object(self.synchronizer, '_create_monitor_entity') as mock_create, \
             patch.object(self.synchronizer, '_update_entity') as mock_update, \
             patch.object(self.synchronizer, '_remove_entity', side_effect=mock_remove_entity) as mock_remove:
            
            result = IntegrationSyncResult(title='Test')
            self.synchronizer._sync_monitors(result)
            
            # Test removal path was taken
            mock_remove.assert_called_once_with(entity=mock_entity, result=result)
            mock_create.assert_not_called()
            mock_update.assert_not_called()
            
            # Test result tracking for cleanup scenario
            self.assertIn('Fetched 0 monitors from ZM', result.info_list)
            self.assertIn('Found 1 existing item', result.info_list)
            self.assertIn('Removed stale entity Deleted Camera', result.info_list)
            
            # Test no errors in successful removal scenario
            self.assertEqual(len(result.error_list), 0)


class TestZoneMinderSynchronizerFetchMonitors(TestCase):
    """Test ZM monitor fetching and integration key generation"""
    
    def setUp(self):
        self.synchronizer = ZoneMinderSynchronizer()
        
        # Mock the zm_manager
        self.mock_manager = Mock()
        self.mock_manager.ZM_MONITOR_INTEGRATION_NAME_PREFIX = 'monitor'
        self.synchronizer._zm_manager = self.mock_manager
    
    def test_fetch_zm_monitors_creates_integration_keys(self):
        """Test _fetch_zm_monitors creates correct integration keys for each monitor"""
        # Mock monitors
        mock_monitor1 = Mock()
        mock_monitor1.id.return_value = 123
        mock_monitor2 = Mock()
        mock_monitor2.id.return_value = 456
        
        self.mock_manager.get_zm_monitors.return_value = [mock_monitor1, mock_monitor2]
        
        # Mock integration key generation
        key1 = IntegrationKey(integration_id='zm', integration_name='monitor.123')
        key2 = IntegrationKey(integration_id='zm', integration_name='monitor.456')
        self.mock_manager._to_integration_key.side_effect = [key1, key2]
        
        result = IntegrationSyncResult(title='Test')
        result_dict = self.synchronizer._fetch_zm_monitors(result)
        
        # Should call integration key generation for each monitor
        expected_calls = [
            call(prefix='monitor', zm_monitor_id=123),
            call(prefix='monitor', zm_monitor_id=456)
        ]
        self.mock_manager._to_integration_key.assert_has_calls(expected_calls)
        
        # Should return dictionary mapping keys to monitors
        self.assertEqual(len(result_dict), 2)
        self.assertEqual(result_dict[key1], mock_monitor1)
        self.assertEqual(result_dict[key2], mock_monitor2)
    
    def test_fetch_zm_monitors_forces_reload(self):
        """Test _fetch_zm_monitors forces reload of monitor data"""
        self.mock_manager.get_zm_monitors.return_value = []
        
        result = IntegrationSyncResult(title='Test')
        self.synchronizer._fetch_zm_monitors(result)
        
        self.mock_manager.get_zm_monitors.assert_called_once_with(force_load=True)


class TestZoneMinderSynchronizerExistingEntities(TestCase):
    """Test existing entity retrieval and error handling"""
    
    def setUp(self):
        self.synchronizer = ZoneMinderSynchronizer()
        
        # Mock the zm_manager
        self.mock_manager = Mock()
        self.mock_manager.ZM_MONITOR_INTEGRATION_NAME_PREFIX = 'monitor'
        self.synchronizer._zm_manager = self.mock_manager
    
    @patch('hi.services.zoneminder.zm_sync.Entity.objects.filter')
    def test_get_existing_zm_monitor_entities_filters_by_integration_id(self, mock_filter):
        """Test _get_existing_zm_monitor_entities filters by correct integration ID"""
        mock_filter.return_value = []
        
        result = IntegrationSyncResult(title='Test')
        self.synchronizer._get_existing_zm_monitor_entities(result)
        
        mock_filter.assert_called_once_with(integration_id=ZmMetaData.integration_id)
    
    @patch('hi.services.zoneminder.zm_sync.Entity.objects.filter')
    def test_get_existing_zm_monitor_entities_handles_missing_integration_key(self, mock_filter):
        """Test entity retrieval handles entities without integration keys"""
        # Mock entity without integration key
        mock_entity = Mock()
        mock_entity.id = 999
        mock_entity.integration_key = None
        mock_filter.return_value = [mock_entity]
        
        result = IntegrationSyncResult(title='Test')
        result_dict = self.synchronizer._get_existing_zm_monitor_entities(result)
        
        # Should add error message
        self.assertIn('ZM item found without integration name', result.error_list[0])
        
        # Should NOT include entity in result (mock key doesn't start with 'monitor' prefix)
        self.assertEqual(len(result_dict), 0)
    
    @patch('hi.services.zoneminder.zm_sync.Entity.objects.filter')
    def test_get_existing_zm_monitor_entities_filters_monitor_entities(self, mock_filter):
        """Test entity retrieval only includes monitor entities"""
        # Mock entities - one monitor, one non-monitor
        mock_monitor_entity = Mock()
        monitor_key = IntegrationKey(integration_id='zm', integration_name='monitor.123')
        mock_monitor_entity.integration_key = monitor_key
        
        mock_other_entity = Mock()
        other_key = IntegrationKey(integration_id='zm', integration_name='system.state')
        mock_other_entity.integration_key = other_key
        
        mock_filter.return_value = [mock_monitor_entity, mock_other_entity]
        
        result = IntegrationSyncResult(title='Test')
        result_dict = self.synchronizer._get_existing_zm_monitor_entities(result)
        
        # Should only include monitor entity
        self.assertEqual(len(result_dict), 1)
        self.assertIn(monitor_key, result_dict)
        self.assertNotIn(other_key, result_dict)


class TestZoneMinderSynchronizerEntityUpdate(TestCase):
    """Test entity update logic"""
    
    def setUp(self):
        self.synchronizer = ZoneMinderSynchronizer()
    
    def test_update_entity_changes_name_when_different(self):
        """Test _update_entity updates name when monitor name changed and preserves other attributes"""
        mock_entity = Mock()
        mock_entity.name = 'Old Name'
        mock_entity.id = 123
        mock_entity.entity_type_str = 'CAMERA'
        mock_entity.can_user_delete = True
        original_integration_key = Mock()
        mock_entity.integration_key = original_integration_key
        mock_entity.save = Mock()
        
        mock_monitor = Mock()
        mock_monitor.name.return_value = 'New Name'
        mock_monitor.id.return_value = 456
        
        result = IntegrationSyncResult(title='Test')
        self.synchronizer._update_entity(mock_entity, mock_monitor, result)
        
        # Test name update behavior
        self.assertEqual(mock_entity.name, 'New Name')
        mock_entity.save.assert_called_once()
        
        # Test preservation of other critical attributes
        self.assertEqual(mock_entity.id, 123)  # Entity ID unchanged
        self.assertEqual(mock_entity.entity_type_str, 'CAMERA')  # Type unchanged
        self.assertEqual(mock_entity.can_user_delete, True)  # User delete flag unchanged
        self.assertEqual(mock_entity.integration_key, original_integration_key)  # Integration key unchanged
        
        # Rename surfaces the old → new transition in updated_list
        # (operator can see both names at a glance).
        self.assertEqual(len(result.error_list), 0)
        self.assertEqual(result.updated_list, ['Old Name → New Name'])

    def test_update_entity_no_change_when_name_same(self):
        """Test _update_entity doesn't save when name unchanged and preserves all entity state"""
        mock_entity = Mock()
        mock_entity.name = 'Same Name'
        mock_entity.id = 789
        mock_entity.entity_type_str = 'CAMERA'
        mock_entity.save = Mock()

        mock_monitor = Mock()
        mock_monitor.name.return_value = 'Same Name'
        mock_monitor.id.return_value = 999

        result = IntegrationSyncResult(title='Test')
        self.synchronizer._update_entity(mock_entity, mock_monitor, result)

        # Test no persistence when no changes.
        mock_entity.save.assert_not_called()

        # No-change path appends nothing and surfaces nothing.
        self.assertEqual(len(result.error_list), 0)
        self.assertEqual(result.updated_list, [])
        self.assertEqual(result.info_list, [])


class TestZoneMinderSynchronizerEntityRemoval(TestCase):
    """Test intelligent entity deletion"""
    
    def setUp(self):
        self.synchronizer = ZoneMinderSynchronizer()
    
    @patch.object(ZoneMinderSynchronizer, '_remove_entity_intelligently')
    def test_remove_entity_calls_intelligent_deletion(self, mock_intelligent_removal):
        """Test _remove_entity calls intelligent deletion with correct parameters"""
        mock_entity = Mock()
        result = IntegrationSyncResult(title='Test')
        
        self.synchronizer._remove_entity(mock_entity, result)
        
        mock_intelligent_removal.assert_called_once_with(mock_entity, result)


class TestZoneMinderSynchronizerFunctionConstants(TestCase):
    """Test monitor function name constants"""
    
    def test_monitor_function_name_label_dict_completeness(self):
        """Test MONITOR_FUNCTION_NAME_LABEL_DICT contains expected ZM functions"""
        expected_functions = ['None', 'Monitor', 'Modect', 'Record', 'Mocord', 'Nodect']
        
        for function in expected_functions:
            self.assertIn(function, ZoneMinderSynchronizer.MONITOR_FUNCTION_NAME_LABEL_DICT)
            # Labels should match function names
            self.assertEqual(
                ZoneMinderSynchronizer.MONITOR_FUNCTION_NAME_LABEL_DICT[function],
                function
            )


class TestZoneMinderSynchronizerWithRealData(TestCase):
    """Test synchronizer with real ZoneMinder API response data"""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Load real ZM API response data
        test_data_dir = os.path.join(os.path.dirname(__file__), 'data')
        
        with open(os.path.join(test_data_dir, 'zm_states.json'), 'r') as f:
            cls.real_states_data = json.load(f)
            
        with open(os.path.join(test_data_dir, 'zm_monitors.json'), 'r') as f:
            cls.real_monitors_data = json.load(f)
    
    def setUp(self):
        self.synchronizer = ZoneMinderSynchronizer()
        
        # Mock the zm_manager
        self.mock_manager = Mock()
        self.mock_manager.ZM_MONITOR_INTEGRATION_NAME_PREFIX = 'monitor'
        self.mock_manager._to_integration_key = Mock()
        self.synchronizer._zm_manager = self.mock_manager
    
    def create_mock_states_from_real_data(self):
        """Create mock PyZM State objects from real API data"""
        mock_states = []
        for state_data in self.real_states_data['states']:
            state_info = state_data['State']
            mock_state = Mock()
            mock_state.name.return_value = state_info['Name']
            mock_state.id.return_value = int(state_info['Id'])
            mock_state.is_active.return_value = state_info['IsActive'] == '1'
            mock_states.append(mock_state)
        return mock_states
    
    def create_mock_monitors_from_real_data(self):
        """Create mock PyZM Monitor objects from real API data"""
        mock_monitors = []
        for monitor_data in self.real_monitors_data['monitors']:
            monitor_info = monitor_data['Monitor']
            mock_monitor = Mock()
            mock_monitor.id.return_value = int(monitor_info['Id'])
            mock_monitor.name.return_value = monitor_info['Name']
            mock_monitor.function.return_value = monitor_info['Function']
            mock_monitor.enabled.return_value = monitor_info['Enabled'] == '1'
            mock_monitors.append(mock_monitor)
        return mock_monitors
    
    @patch('hi.services.zoneminder.zm_sync.Entity.objects.filter_by_integration_key')
    @patch('hi.services.zoneminder.zm_sync.Sensor.objects.filter_by_integration_key')
    def test_sync_states_with_real_zm_state_names(self, mock_sensor_filter, mock_entity_filter):
        """Test state sync handles real ZM state names: default, Away, HomeDay, Disabled"""
        # Use real state data
        mock_states = self.create_mock_states_from_real_data()
        self.mock_manager.get_zm_states.return_value = mock_states
        
        # Mock existing entity and sensor
        mock_entity_filter.return_value.first.return_value = Mock()
        
        mock_sensor = Mock()
        mock_entity_state = Mock()
        mock_entity_state.value_range_dict = {'old_state': 'old_state'}  # Different from real data
        mock_entity_state.save = Mock()
        mock_sensor.entity_state = mock_entity_state
        mock_sensor_filter.return_value.select_related.return_value.first.return_value = mock_sensor
        
        # Mock integration keys
        self.mock_manager._zm_integration_key.return_value = IntegrationKey(
            integration_id='zm', integration_name='system'
        )
        self.mock_manager._zm_run_state_integration_key.return_value = IntegrationKey(
            integration_id='zm', integration_name='run.state'
        )
        
        result = IntegrationSyncResult(title='Test')
        self.synchronizer._sync_states(result)
        
        # Should update to real state names
        expected_states = {'default': 'default', 'Away': 'Away', 'HomeDay': 'HomeDay', 'Disabled': 'Disabled'}
        self.assertEqual(mock_entity_state.value_range_dict, expected_states)
        mock_entity_state.save.assert_called_once()
        self.assertIn('Updated ZM state values to:', result.info_list[0])
    
    @patch.object(ZoneMinderSynchronizer, '_fetch_zm_monitors')
    @patch.object(ZoneMinderSynchronizer, '_get_existing_zm_monitor_entities')
    @patch.object(ZoneMinderSynchronizer, '_create_monitor_entity')
    def test_sync_monitors_with_real_monitor_configurations(self, mock_create, mock_get_existing, mock_fetch):
        """Test monitor sync with real monitor configurations and diverse setups"""
        # Use real monitor data to create integration keys and monitors
        mock_monitors = self.create_mock_monitors_from_real_data()
        
        integration_key_to_monitor = {}
        for i, mock_monitor in enumerate(mock_monitors):
            # Use real monitor IDs from the data
            monitor_id = [1, 3, 6, 9][i]  # IDs from our test data
            integration_key = IntegrationKey(
                integration_id='zm', 
                integration_name=f'monitor.{monitor_id}'
            )
            integration_key_to_monitor[integration_key] = mock_monitor
        
        mock_fetch.return_value = integration_key_to_monitor
        mock_get_existing.return_value = {}  # No existing entities
        
        result = IntegrationSyncResult(title='Test')
        self.synchronizer._sync_monitors(result)
        
        # Should create entities for all real monitors
        self.assertEqual(mock_create.call_count, 4)
        
        # Verify created with real monitor names
        created_monitors = [call.kwargs['zm_monitor'] for call in mock_create.call_args_list]
        created_names = [monitor.name.return_value for monitor in created_monitors]
        expected_names = ['HighCamera', 'FrontCamera', 'DriveCamera', 'GarageCamera']
        self.assertEqual(created_names, expected_names)
    
    def test_real_monitor_data_diversity_validation(self):
        """Test that our real monitor data covers diverse configurations"""
        monitors = self.real_monitors_data['monitors']
        
        # Test we have monitors with different resolutions
        resolutions = set()
        orientations = set()
        zone_counts = set()
        
        for monitor_data in monitors:
            monitor = monitor_data['Monitor']
            resolution = f"{monitor['Width']}x{monitor['Height']}"
            resolutions.add(resolution)
            orientations.add(monitor['Orientation'])
            zone_counts.add(int(monitor['ZoneCount']))
        
        # Verify diversity in our test data
        self.assertGreaterEqual(len(resolutions), 2, "Should have multiple resolutions")
        self.assertGreaterEqual(len(orientations), 2, "Should have multiple orientations") 
        self.assertGreaterEqual(len(zone_counts), 3, "Should have varying zone counts")
        
        # Verify we have the expected variety
        self.assertIn('640x480', resolutions)
        self.assertIn('1920x1080', resolutions)
        self.assertIn('ROTATE_0', orientations)
        self.assertIn('ROTATE_270', orientations)
    
    def test_update_entity_with_real_monitor_name_changes(self):
        """Test entity updates with realistic monitor name scenarios"""
        # Create scenario where monitor name changed from generic to real name
        mock_entity = Mock()
        mock_entity.name = 'Camera_001'  # Generic name
        
        # Use real monitor data
        real_monitor = self.create_mock_monitors_from_real_data()[0]  # HighCamera
        
        result = IntegrationSyncResult(title='Test')
        self.synchronizer._update_entity(mock_entity, real_monitor, result)
        
        # Should update to real name from ZM API
        self.assertEqual(mock_entity.name, 'HighCamera')
        mock_entity.save.assert_called_once()
        self.assertEqual(result.updated_list, ['Camera_001 → HighCamera'])
    
    @patch('hi.services.zoneminder.zm_sync.Entity.objects.filter')
    def test_get_existing_entities_with_real_monitor_id_patterns(self, mock_filter):
        """Test existing entity retrieval with realistic monitor ID patterns"""
        # Create mock entities with integration keys matching real monitor IDs
        mock_entities = []
        real_monitor_ids = ['1', '3', '6', '9']  # From our real data
        
        for monitor_id in real_monitor_ids:
            mock_entity = Mock()
            mock_entity.id = int(monitor_id) + 100  # Offset for entity IDs
            mock_entity.integration_key = IntegrationKey(
                integration_id='zm',
                integration_name=f'monitor.{monitor_id}'
            )
            mock_entities.append(mock_entity)
        
        # Add one entity with missing integration key to test error handling
        mock_broken_entity = Mock()
        mock_broken_entity.id = 999
        mock_broken_entity.integration_key = None
        mock_entities.append(mock_broken_entity)
        
        mock_filter.return_value = mock_entities
        
        result = IntegrationSyncResult(title='Test')
        result_dict = self.synchronizer._get_existing_zm_monitor_entities(result)
        
        # Should find 4 valid monitor entities (broken entity is filtered out)
        self.assertEqual(len(result_dict), 4)
        
        # Should have error message for broken entity
        self.assertIn('ZM item found without integration name', result.error_list[0])
        
        # Should include all real monitor integration keys
        integration_names = [key.integration_name for key in result_dict.keys()]
        for monitor_id in real_monitor_ids:
            self.assertIn(f'monitor.{monitor_id}', integration_names)
    
    def test_real_state_data_validation(self):
        """Test that our real state data contains expected ZM states"""
        states = self.real_states_data['states']
        
        # Extract state names
        state_names = [state['State']['Name'] for state in states]
        
        # Verify we have typical ZM states
        expected_states = ['default', 'Away', 'HomeDay', 'Disabled']
        for expected_state in expected_states:
            self.assertIn(expected_state, state_names)
        
        # Verify state structure
        for state_data in states:
            state = state_data['State']
            self.assertIn('Id', state)
            self.assertIn('Name', state)
            self.assertIn('Definition', state)
            self.assertIn('IsActive', state)
            
            # Verify IsActive is boolean-like string
            self.assertIn(state['IsActive'], ['0', '1'])
    
    @patch('hi.services.zoneminder.zm_sync.HiModelHelper.create_movement_sensor')
    @patch('hi.services.zoneminder.zm_sync.HiModelHelper.create_discrete_controller')
    @patch('hi.services.zoneminder.zm_sync.HiModelHelper.create_movement_event_definition')
    @patch('hi.services.zoneminder.zm_sync.transaction.atomic')
    @patch.object(Entity, 'save')
    def test_create_monitor_entity_with_real_monitor_variations(self, mock_save, mock_atomic,
                                                                mock_create_event, mock_create_controller,
                                                                mock_create_movement):
        """Test monitor entity creation with real monitor data variations"""
        # Test each real monitor configuration
        real_monitors = self.create_mock_monitors_from_real_data()
        
        # Mock integration key generation for each component
        def mock_integration_key_side_effect(prefix, zm_monitor_id):
            return IntegrationKey(
                integration_id='zm',
                integration_name=f'{prefix}.{zm_monitor_id}'
            )
        
        self.mock_manager._to_integration_key.side_effect = mock_integration_key_side_effect
        self.mock_manager.should_add_alarm_events = True
        
        # Mock movement sensor for event creation
        mock_movement_sensor = Mock()
        mock_movement_sensor.entity_state = Mock()
        mock_create_movement.return_value = mock_movement_sensor
        
        for monitor in real_monitors:
            with self.subTest(monitor_name=monitor.name.return_value):
                mock_save.reset_mock()
                mock_create_movement.reset_mock()
                mock_create_controller.reset_mock()
                mock_create_event.reset_mock()
                
                result = IntegrationSyncResult(title='Test')
                self.synchronizer._create_monitor_entity(monitor, result)
                
                # Should create all components for each monitor
                mock_create_movement.assert_called_once() 
                mock_create_controller.assert_called_once()
                mock_create_event.assert_called_once()
                
                # Should save entity
                mock_save.assert_called_once()
                
                # Should use transaction
                mock_atomic.assert_called()
                
                # Creation records the entity name in created_list.
                self.assertEqual(len(result.created_list), 1)


class TestZoneMinderSynchronizerSyncResultGrouping(TestCase):
    """Phase 2 grouping behavior: every imported monitor entity goes
    into a single 'Monitors' group on the IntegrationSyncResult.

    The single-group choice reflects the typical ZM UX — operators
    place all cameras into the same view — while the placement
    modal's drill-down still allows per-monitor placement when needed."""

    def setUp(self):
        self.synchronizer = ZoneMinderSynchronizer()
        self.mock_manager = Mock()
        self.mock_manager.zm_client = Mock()
        self.synchronizer._zm_manager = self.mock_manager

    def _imported_entity(self, name, integration_name):
        entity = Mock()
        entity.name = name
        entity.integration_key = IntegrationKey(
            integration_id='zm',
            integration_name=integration_name,
        )
        entity.id = 0
        return entity

    def test_sync_impl_emits_single_monitors_group(self):
        entity_a = self._imported_entity('Front Door', 'monitor.1')
        entity_b = self._imported_entity('Driveway', 'monitor.2')
        with patch.object(self.synchronizer, '_sync_states'), \
             patch.object(self.synchronizer, '_sync_monitors',
                          return_value=[entity_a, entity_b]):
            result = self.synchronizer._sync_impl(is_initial_import=True)

        self.assertIsNotNone(result.placement_input)
        self.assertEqual(result.placement_input.ungrouped_items, [])
        self.assertEqual(len(result.placement_input.groups), 1)
        group = result.placement_input.groups[0]
        self.assertEqual(group.label, 'Monitors')
        self.assertEqual([item.entity for item in group.items], [entity_a, entity_b])
        # Stable per-item key built from the integration_key.
        self.assertEqual(group.items[0].key, 'zm:monitor.1')
        self.assertEqual(group.items[1].key, 'zm:monitor.2')

    def test_sync_impl_emits_no_placement_input_when_no_monitors_imported(self):
        with patch.object(self.synchronizer, '_sync_states'), \
             patch.object(self.synchronizer, '_sync_monitors', return_value=[]):
            result = self.synchronizer._sync_impl(is_initial_import=True)

        # No newly-created entities → no placement input → placement
        # modal is not shown.
        self.assertIsNone(result.placement_input)


class CreateMonitorEntityCreateNewContractTests(TestCase):
    """
    Pre-refactor safety net for ``ZoneMinderSynchronizer._create_monitor_entity``.

    Phase 3 of Issue #281 will refactor this method to accept an
    optional existing Entity (for the auto-reconnect path). These
    tests pin the current "create a new Entity from upstream
    monitor" contract — real DB persistence, not mocks — so the
    refactor cannot silently regress entity / sensor / controller
    creation.
    """

    def setUp(self):
        # IntegrationManager is a process-wide singleton; reset its
        # in-memory state so prior tests in the suite cannot pollute
        # ours (and ours cannot pollute theirs).
        IntegrationManager().reset_for_testing()

        self.synchronizer = ZoneMinderSynchronizer()

        self.mock_manager = Mock()
        self.mock_manager.ZM_MONITOR_INTEGRATION_NAME_PREFIX = 'monitor'
        self.mock_manager.MOVEMENT_SENSOR_PREFIX = 'monitor.motion'
        self.mock_manager.MONITOR_FUNCTION_SENSOR_PREFIX = 'monitor.function'
        self.mock_manager.MOVEMENT_EVENT_PREFIX = 'monitor.motion'
        # Skip alarm event creation to keep this safety net narrow —
        # event-definition creation is exercised elsewhere.
        self.mock_manager.should_add_alarm_events = False

        def make_key(prefix, zm_monitor_id):
            return IntegrationKey(
                integration_id=ZmMetaData.integration_id,
                integration_name=f'{prefix}.{zm_monitor_id}',
            )
        self.mock_manager._to_integration_key.side_effect = make_key

        self.synchronizer._zm_manager = self.mock_manager

    def _mock_monitor(self, monitor_id=42, name='Driveway'):
        monitor = Mock()
        monitor.id.return_value = monitor_id
        monitor.name.return_value = name
        return monitor

    def test_creates_entity_with_camera_type_and_correct_integration_key(self):
        result = IntegrationSyncResult(title='Test')
        monitor = self._mock_monitor(monitor_id=42, name='Driveway')

        entity = self.synchronizer._create_monitor_entity(
            zm_monitor=monitor,
            result=result,
        )

        from hi.apps.entity.enums import EntityType
        self.assertIsInstance(entity, Entity)
        self.assertEqual(entity.name, 'Driveway')
        self.assertEqual(entity.entity_type, EntityType.CAMERA)
        self.assertEqual(entity.integration_id, ZmMetaData.integration_id)
        self.assertEqual(entity.integration_name, 'monitor.42')
        self.assertTrue(entity.has_video_stream)

    def test_creates_movement_sensor_and_function_controller_for_monitor(self):
        result = IntegrationSyncResult(title='Test')
        monitor = self._mock_monitor(monitor_id=43, name='Front Door')

        entity = self.synchronizer._create_monitor_entity(
            zm_monitor=monitor,
            result=result,
        )

        # The monitor's movement sensor should exist on a per-entity basis.
        self.assertGreaterEqual(Sensor.objects.filter(entity_state__entity=entity).count(), 1)


class CreateMonitorEntityReconnectContractTests(TestCase):
    """
    Pin the reconnect contract added in Issue #281 Phase 3:
    when ``entity`` is provided, ``_create_monitor_entity`` populates
    that entity's integration-owned components without creating a new
    Entity row and without overwriting the entity's name.
    """

    def setUp(self):
        IntegrationManager().reset_for_testing()
        self.synchronizer = ZoneMinderSynchronizer()
        self.mock_manager = Mock()
        self.mock_manager.ZM_MONITOR_INTEGRATION_NAME_PREFIX = 'monitor'
        self.mock_manager.MOVEMENT_SENSOR_PREFIX = 'monitor.motion'
        self.mock_manager.MONITOR_FUNCTION_SENSOR_PREFIX = 'monitor.function'
        self.mock_manager.MOVEMENT_EVENT_PREFIX = 'monitor.motion'
        self.mock_manager.should_add_alarm_events = False
        self.mock_manager._to_integration_key.side_effect = lambda prefix, zm_monitor_id: IntegrationKey(
            integration_id=ZmMetaData.integration_id,
            integration_name=f'{prefix}.{zm_monitor_id}',
        )
        self.synchronizer._zm_manager = self.mock_manager

    def _mock_monitor(self, monitor_id=99, name='Driveway'):
        monitor = Mock()
        monitor.id.return_value = monitor_id
        monitor.name.return_value = name
        return monitor

    def test_with_existing_entity_does_not_create_new_entity(self):
        existing = Entity.objects.create(
            name='User Renamed Camera',
            entity_type_str='CAMERA',
        )
        baseline_count = Entity.objects.count()
        result = IntegrationSyncResult(title='Test')

        returned = self.synchronizer._create_monitor_entity(
            zm_monitor=self._mock_monitor(monitor_id=99, name='Upstream Driveway'),
            result=result,
            entity=existing,
        )

        self.assertEqual(Entity.objects.count(), baseline_count)
        self.assertEqual(returned.id, existing.id)

    def test_with_existing_entity_preserves_entity_name(self):
        existing = Entity.objects.create(
            name='User Renamed Camera',
            entity_type_str='CAMERA',
        )
        result = IntegrationSyncResult(title='Test')

        self.synchronizer._create_monitor_entity(
            zm_monitor=self._mock_monitor(monitor_id=100, name='Upstream Camera'),
            result=result,
            entity=existing,
        )

        existing.refresh_from_db()
        self.assertEqual(existing.name, 'User Renamed Camera')

    def test_with_existing_entity_sets_integration_key_and_video_flag(self):
        existing = Entity.objects.create(
            name='User Renamed Camera',
            entity_type_str='CAMERA',
        )
        result = IntegrationSyncResult(title='Test')

        self.synchronizer._create_monitor_entity(
            zm_monitor=self._mock_monitor(monitor_id=101, name='Upstream Camera'),
            result=result,
            entity=existing,
        )

        existing.refresh_from_db()
        self.assertEqual(existing.integration_id, ZmMetaData.integration_id)
        self.assertEqual(existing.integration_name, 'monitor.101')
        self.assertTrue(existing.has_video_stream)


class EventDefinitionLifecycleCycleTests(TestCase):
    """
    Issue #288 Phase 3: end-to-end EventDefinition lifecycle across
    disable/re-enable cycles. Verifies that integration-owned
    EventDefinitions return to a stable count (one per monitor) instead
    of accumulating across cycles, on both the hard-delete path and
    the preserve-and-reconnect path.
    """

    MONITOR_ID = 77

    def setUp(self):
        # IntegrationManager is a process-wide singleton; reset its
        # in-memory state so prior tests in the suite cannot pollute
        # ours (and ours cannot pollute theirs).
        IntegrationManager().reset_for_testing()

        self.synchronizer = ZoneMinderSynchronizer()

        self.mock_manager = Mock()
        self.mock_manager.ZM_MONITOR_INTEGRATION_NAME_PREFIX = 'monitor'
        self.mock_manager.MOVEMENT_SENSOR_PREFIX = 'monitor.motion'
        self.mock_manager.MONITOR_FUNCTION_SENSOR_PREFIX = 'monitor.function'
        self.mock_manager.MOVEMENT_EVENT_PREFIX = 'monitor.motion'
        # Alarm event creation must be on for this test class — that's
        # what we're exercising.
        self.mock_manager.should_add_alarm_events = True

        def make_key(prefix, zm_monitor_id):
            return IntegrationKey(
                integration_id=ZmMetaData.integration_id,
                integration_name=f'{prefix}.{zm_monitor_id}',
            )
        self.mock_manager._to_integration_key.side_effect = make_key

        self.synchronizer._zm_manager = self.mock_manager

    def _mock_monitor(self, monitor_id=None, name='Driveway'):
        monitor = Mock()
        monitor.id.return_value = monitor_id if monitor_id is not None else self.MONITOR_ID
        monitor.name.return_value = name
        return monitor

    def _create_monitor(self, name='Driveway'):
        result = IntegrationSyncResult(title='Create')
        return self.synchronizer._create_monitor_entity(
            zm_monitor=self._mock_monitor(name=name),
            result=result,
        )

    def _zm_event_def_count(self):
        return EventDefinition.objects.filter(
            integration_id=ZmMetaData.integration_id,
        ).count()

    def test_hard_delete_then_recreate_cycle_baseline_count(self):
        # Cycle: create, hard-delete, recreate. Without Phase 2 cleanup
        # the EventDefinition would accumulate; with it, count returns
        # to exactly one.
        self._create_monitor()
        self.assertEqual(self._zm_event_def_count(), 1)

        # Take the hard-delete branch (no user data on the entity).
        EntityIntegrationOperations.remove_entities_with_closure(
            seed_entity_ids=[
                Entity.objects.get(integration_id=ZmMetaData.integration_id).id,
            ],
            integration_name=ZmMetaData.integration_id,
            preserve_user_data=False,
        )
        self.assertEqual(self._zm_event_def_count(), 0)

        # Recreate (next sync sees the monitor as new).
        self._create_monitor()
        self.assertEqual(self._zm_event_def_count(), 1)

        # One more cycle to be sure we're not just clean-on-first-loop.
        EntityIntegrationOperations.remove_entities_with_closure(
            seed_entity_ids=[
                Entity.objects.get(integration_id=ZmMetaData.integration_id).id,
            ],
            integration_name=ZmMetaData.integration_id,
            preserve_user_data=False,
        )
        self._create_monitor()
        self.assertEqual(self._zm_event_def_count(), 1)

    def test_preserve_then_reconnect_cycle_baseline_count(self):
        # Cycle: create, preserve-disconnect (user data forces SAFE
        # branch), reconnect via _rebuild_integration_components.
        # End state: exactly one integration-owned EventDefinition.
        entity = self._create_monitor()
        EntityAttribute.objects.create(
            entity=entity,
            name='User Note',
            value='retain me',
            value_type_str=str(AttributeValueType.TEXT),
            attribute_type_str=str(AttributeType.CUSTOM),
        )
        self.assertEqual(self._zm_event_def_count(), 1)

        # SAFE path: preserve_with_user_data should remove the
        # integration EventDefinition.
        EntityIntegrationOperations.preserve_with_user_data(
            entity=entity,
            integration_name=ZmMetaData.integration_id,
        )
        self.assertEqual(self._zm_event_def_count(), 0)

        # Reconnect path uses the same converter as fresh-create with
        # entity=existing. Should recreate exactly one EventDefinition.
        entity.refresh_from_db()
        result = IntegrationSyncResult(title='Reconnect')
        self.synchronizer._rebuild_integration_components(
            entity=entity,
            upstream=self._mock_monitor(),
            result=result,
        )
        self.assertEqual(self._zm_event_def_count(), 1)


from hi.testing.async_task_utils import AsyncTaskTestCase


class TestZoneMinderSynchronizerCheckNeedsSync(AsyncTaskTestCase):
    """Issue #283 — sync-check probe shape for ZoneMinder.

    Pins that upstream keys are built using the same prefix scheme
    as the live sync (``MONITOR.<id>``) and that the HI side filter
    excludes non-monitor entities (the ZM service entity, run-state
    sensors). Uses real Entity rows so the
    ``integration_name__startswith=prefix`` query is exercised — the
    "exclude service entity" claim that lives only in code is the
    load-bearing piece this test class pins.
    """

    def _zm_key(self, name: str):
        return IntegrationKey(
            integration_id=ZmMetaData.integration_id,
            integration_name=name,
        )

    def _make_zm_monitor_entities(self, monitor_ids):
        for monitor_id in monitor_ids:
            Entity.objects.create(
                name=f'Camera {monitor_id}',
                entity_type_str='CAMERA',
                integration_id=ZmMetaData.integration_id,
                integration_name=f'monitor.{monitor_id}',
            )

    def _make_zm_service_entity(self):
        # The ZM service entity is integration_id='zm' but does NOT
        # carry the 'monitor.' prefix — the probe must exclude it
        # from the comparison.
        Entity.objects.create(
            name='ZoneMinder Service',
            entity_type_str='SERVICE',
            integration_id=ZmMetaData.integration_id,
            integration_name='zoneminder.service',
        )

    def _run_check(self, monitor_ids):
        synchronizer = ZoneMinderSynchronizer()
        manager = Mock()
        manager.ZM_MONITOR_INTEGRATION_NAME_PREFIX = 'monitor'

        # Mirror the production zm_manager._to_integration_key
        # builder so the test's upstream side passes through the
        # same IntegrationKey construction the production code uses.
        def to_integration_key(prefix, zm_monitor_id):
            return IntegrationKey(
                integration_id=ZmMetaData.integration_id,
                integration_name=f'{prefix}.{zm_monitor_id}',
            )
        manager._to_integration_key = to_integration_key

        async def get_monitors(force_load=False):
            return [
                Mock(**{'id.return_value': monitor_id})
                for monitor_id in monitor_ids
            ]

        manager.get_zm_monitors_async = get_monitors

        async def get_manager():
            return manager

        with patch.object(synchronizer, 'zm_manager_async', side_effect=get_manager):
            return self.run_async(synchronizer.check_needs_sync())

    def test_in_sync_when_upstream_monitors_match_hi(self):
        self._make_zm_monitor_entities([1, 2, 3])
        delta = self._run_check(monitor_ids=[1, 2, 3])
        self.assertFalse(delta.needs_sync)

    def test_upstream_added_appears_in_delta(self):
        self._make_zm_monitor_entities([1, 2, 3])
        delta = self._run_check(monitor_ids=[1, 2, 3, 4])
        self.assertEqual(delta.added, {self._zm_key('monitor.4')})
        self.assertEqual(delta.removed, set())

    def test_upstream_removed_appears_in_delta(self):
        self._make_zm_monitor_entities([1, 2])
        delta = self._run_check(monitor_ids=[1])
        self.assertEqual(delta.added, set())
        self.assertEqual(delta.removed, {self._zm_key('monitor.2')})

    def test_zm_service_entity_is_excluded_from_comparison(self):
        # The ZM service entity has integration_id='zm' but no
        # 'monitor.' prefix on integration_name. The probe must
        # exclude it from the HI side, otherwise it would always
        # show up as "removed" (no upstream monitor matches).
        self._make_zm_monitor_entities([1, 2])
        self._make_zm_service_entity()
        delta = self._run_check(monitor_ids=[1, 2])
        self.assertFalse(delta.needs_sync)

    def test_returns_none_when_manager_not_ready(self):
        synchronizer = ZoneMinderSynchronizer()

        async def get_manager():
            return None

        with patch.object(synchronizer, 'zm_manager_async', side_effect=get_manager):
            result = self.run_async(synchronizer.check_needs_sync())

        self.assertIsNone(result)
