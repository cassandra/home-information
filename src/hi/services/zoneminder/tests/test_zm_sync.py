import json
import os
from unittest.mock import Mock, MagicMock, patch, call
from django.test import TestCase
from django.db import transaction

from hi.apps.common.database_lock import ExclusionLockContext
from hi.apps.common.processing_result import ProcessingResult
from hi.apps.entity.enums import EntityType
from hi.apps.entity.models import Entity
from hi.apps.sense.models import Sensor
from hi.apps.model_helper import HiModelHelper

from hi.integrations.transient_models import IntegrationKey

from hi.services.zoneminder.zm_sync import ZoneMinderSynchronizer
from hi.services.zoneminder.zm_metadata import ZmMetaData


class TestZoneMinderSynchronizerLockBehavior(TestCase):
    """Test database lock coordination with exception handling"""
    
    def setUp(self):
        self.synchronizer = ZoneMinderSynchronizer()
    
    @patch('hi.services.zoneminder.zm_sync.ExclusionLockContext')
    @patch.object(ZoneMinderSynchronizer, '_sync_helper')
    def test_sync_uses_exclusion_lock(self, mock_sync_helper, mock_lock_context):
        """Test sync method uses exclusion lock for database coordination"""
        mock_result = ProcessingResult(title='Test Result')
        mock_sync_helper.return_value = mock_result
        
        result = self.synchronizer.sync()
        
        mock_lock_context.assert_called_once_with(name='zm_integration_sync')
        mock_sync_helper.assert_called_once()
        self.assertEqual(result, mock_result)
    
    @patch('hi.services.zoneminder.zm_sync.ExclusionLockContext')
    @patch.object(ZoneMinderSynchronizer, '_sync_helper')
    def test_sync_handles_lock_runtime_error(self, mock_sync_helper, mock_lock_context):
        """Test sync method handles RuntimeError from lock context"""
        mock_lock_context.side_effect = RuntimeError("Lock acquisition failed")
        
        result = self.synchronizer.sync()
        
        self.assertEqual(result.title, 'ZM Sync Result')
        self.assertIn('Lock acquisition failed', result.error_list[0])
        mock_sync_helper.assert_not_called()


class TestZoneMinderSynchronizerSyncHelper(TestCase):
    """Test main sync helper logic and flow control"""
    
    def setUp(self):
        self.synchronizer = ZoneMinderSynchronizer()
        
        # Mock the zm_manager
        self.mock_manager = Mock()
        self.synchronizer._zm_manager = self.mock_manager
    
    def test_sync_helper_client_not_available(self):
        """Test sync helper handles missing ZM client gracefully"""
        self.mock_manager.zm_client = None
        
        result = self.synchronizer._sync_helper()
        
        self.assertEqual(result.title, 'ZM Sync Result')
        self.assertIn('Sync problem. ZM integration disabled?', result.error_list[0])
    
    @patch.object(ZoneMinderSynchronizer, '_sync_states')
    @patch.object(ZoneMinderSynchronizer, '_sync_monitors')
    def test_sync_helper_calls_both_sync_methods(self, mock_sync_monitors, mock_sync_states):
        """Test sync helper calls both state and monitor sync methods"""
        self.mock_manager.zm_client = Mock()  # Client available
        
        result = self.synchronizer._sync_helper()
        
        mock_sync_states.assert_called_once_with(result=result)
        mock_sync_monitors.assert_called_once_with(result=result)
        self.assertEqual(result.title, 'ZM Sync Result')


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
    
    @patch.object(Entity.objects, 'filter_by_integration_key')
    @patch.object(Sensor.objects, 'filter_by_integration_key')
    @patch.object(ZoneMinderSynchronizer, '_create_zm_entity')
    def test_sync_states_creates_zm_entity_when_missing(self, mock_create_entity, mock_sensor_filter, mock_entity_filter):
        """Test _sync_states creates ZM entity when it doesn't exist"""
        # Mock ZM states
        mock_state1 = Mock()
        mock_state1.name.return_value = 'start'
        mock_state2 = Mock()
        mock_state2.name.return_value = 'stop'
        self.mock_manager.get_zm_states.return_value = [mock_state1, mock_state2]
        
        # No existing entity
        mock_entity_filter.return_value.first.return_value = None
        
        # Mock sensor exists
        mock_sensor = Mock()
        mock_entity_state = Mock()
        mock_entity_state.value_range_dict = {'start': 'start', 'stop': 'stop'}
        mock_sensor.entity_state = mock_entity_state
        mock_sensor_filter.return_value.select_related.return_value.first.return_value = mock_sensor
        
        result = ProcessingResult(title='Test')
        self.synchronizer._sync_states(result)
        
        # Should create entity with correct state dictionary
        expected_dict = {'start': 'start', 'stop': 'stop'}
        mock_create_entity.assert_called_once()
        call_args = mock_create_entity.call_args
        self.assertEqual(call_args[1]['run_state_name_label_dict'], expected_dict)
    
    @patch.object(Entity.objects, 'filter_by_integration_key')
    @patch.object(Sensor.objects, 'filter_by_integration_key')
    def test_sync_states_missing_sensor_error(self, mock_sensor_filter, mock_entity_filter):
        """Test _sync_states handles missing run state sensor"""
        # Mock states
        mock_state = Mock()
        mock_state.name.return_value = 'start'
        self.mock_manager.get_zm_states.return_value = [mock_state]
        
        # Entity exists
        mock_entity_filter.return_value.first.return_value = Mock()
        
        # No sensor found
        mock_sensor_filter.return_value.select_related.return_value.first.return_value = None
        
        result = ProcessingResult(title='Test')
        self.synchronizer._sync_states(result)
        
        self.assertIn('Missing ZoneMinder sensor for ZM state.', result.error_list)
    
    @patch.object(Entity.objects, 'filter_by_integration_key')
    @patch.object(Sensor.objects, 'filter_by_integration_key')
    def test_sync_states_updates_value_range_when_changed(self, mock_sensor_filter, mock_entity_filter):
        """Test _sync_states updates value range when states change"""
        # Mock new states
        mock_state1 = Mock()
        mock_state1.name.return_value = 'start'
        mock_state2 = Mock()
        mock_state2.name.return_value = 'pause'  # New state
        self.mock_manager.get_zm_states.return_value = [mock_state1, mock_state2]
        
        # Entity exists
        mock_entity_filter.return_value.first.return_value = Mock()
        
        # Mock sensor with existing state
        mock_sensor = Mock()
        mock_entity_state = Mock()
        mock_entity_state.value_range_dict = {'start': 'start', 'stop': 'stop'}  # Old states
        mock_entity_state.save = Mock()
        mock_sensor.entity_state = mock_entity_state
        mock_sensor_filter.return_value.select_related.return_value.first.return_value = mock_sensor
        
        result = ProcessingResult(title='Test')
        self.synchronizer._sync_states(result)
        
        # Should update to new state values
        expected_new_dict = {'start': 'start', 'pause': 'pause'}
        self.assertEqual(mock_entity_state.value_range_dict, expected_new_dict)
        mock_entity_state.save.assert_called_once()
        self.assertIn('Updated ZM state values to:', result.message_list[0])
    
    @patch.object(Entity.objects, 'filter_by_integration_key')
    @patch.object(Sensor.objects, 'filter_by_integration_key')
    def test_sync_states_no_update_when_unchanged(self, mock_sensor_filter, mock_entity_filter):
        """Test _sync_states doesn't update when state values unchanged"""
        # Mock states
        mock_state1 = Mock()
        mock_state1.name.return_value = 'start'
        mock_state2 = Mock()
        mock_state2.name.return_value = 'stop'
        self.mock_manager.get_zm_states.return_value = [mock_state1, mock_state2]
        
        # Entity exists
        mock_entity_filter.return_value.first.return_value = Mock()
        
        # Mock sensor with same existing states
        mock_sensor = Mock()
        mock_entity_state = Mock()
        mock_entity_state.value_range_dict = {'start': 'start', 'stop': 'stop'}  # Same states
        mock_entity_state.save = Mock()
        mock_sensor.entity_state = mock_entity_state
        mock_sensor_filter.return_value.select_related.return_value.first.return_value = mock_sensor
        
        result = ProcessingResult(title='Test')
        self.synchronizer._sync_states(result)
        
        # Should not save or update
        mock_entity_state.save.assert_not_called()
        self.assertNotIn('Updated ZM state values', str(result.message_list))


class TestZoneMinderSynchronizerMonitorSync(TestCase):
    """Test monitor synchronization and entity lifecycle management"""
    
    def setUp(self):
        self.synchronizer = ZoneMinderSynchronizer()
        
        # Mock the zm_manager
        self.mock_manager = Mock()
        self.mock_manager.ZM_MONITOR_INTEGRATION_NAME_PREFIX = 'monitor'
        self.mock_manager._to_integration_key = Mock()
        self.synchronizer._zm_manager = self.mock_manager
    
    @patch.object(ZoneMinderSynchronizer, '_fetch_zm_monitors')
    @patch.object(ZoneMinderSynchronizer, '_get_existing_zm_monitor_entities')
    @patch.object(ZoneMinderSynchronizer, '_create_monitor_entity')
    @patch.object(ZoneMinderSynchronizer, '_update_entity')
    @patch.object(ZoneMinderSynchronizer, '_remove_entity')
    def test_sync_monitors_creates_new_entities(self, mock_remove, mock_update, mock_create, mock_get_existing, mock_fetch):
        """Test _sync_monitors creates entities for new monitors"""
        # Mock monitors from ZM
        mock_monitor = Mock()
        integration_key = IntegrationKey(integration_id='zm', integration_name='monitor.123')
        mock_fetch.return_value = {integration_key: mock_monitor}
        
        # No existing entities
        mock_get_existing.return_value = {}
        
        result = ProcessingResult(title='Test')
        self.synchronizer._sync_monitors(result)
        
        mock_create.assert_called_once_with(zm_monitor=mock_monitor, result=result)
        mock_update.assert_not_called()
        mock_remove.assert_not_called()
    
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
        
        result = ProcessingResult(title='Test')
        self.synchronizer._sync_monitors(result)
        
        mock_update.assert_called_once_with(entity=mock_entity, zm_monitor=mock_monitor, result=result)
        mock_create.assert_not_called()
        mock_remove.assert_not_called()
    
    @patch.object(ZoneMinderSynchronizer, '_fetch_zm_monitors')
    @patch.object(ZoneMinderSynchronizer, '_get_existing_zm_monitor_entities')
    @patch.object(ZoneMinderSynchronizer, '_create_monitor_entity')
    @patch.object(ZoneMinderSynchronizer, '_update_entity')
    @patch.object(ZoneMinderSynchronizer, '_remove_entity')
    def test_sync_monitors_removes_stale_entities(self, mock_remove, mock_update, mock_create, mock_get_existing, mock_fetch):
        """Test _sync_monitors removes entities for deleted monitors"""
        # No current monitors
        mock_fetch.return_value = {}
        
        # Existing entity that should be removed
        mock_entity = Mock()
        integration_key = IntegrationKey(integration_id='zm', integration_name='monitor.123')
        mock_get_existing.return_value = {integration_key: mock_entity}
        
        result = ProcessingResult(title='Test')
        self.synchronizer._sync_monitors(result)
        
        mock_remove.assert_called_once_with(entity=mock_entity, result=result)
        mock_create.assert_not_called()
        mock_update.assert_not_called()


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
        
        result = ProcessingResult(title='Test')
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
        
        result = ProcessingResult(title='Test')
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
    
    @patch.object(Entity.objects, 'filter')
    def test_get_existing_zm_monitor_entities_filters_by_integration_id(self, mock_filter):
        """Test _get_existing_zm_monitor_entities filters by correct integration ID"""
        mock_filter.return_value = []
        
        result = ProcessingResult(title='Test')
        self.synchronizer._get_existing_zm_monitor_entities(result)
        
        mock_filter.assert_called_once_with(integration_id=ZmMetaData.integration_id)
    
    @patch.object(Entity.objects, 'filter')
    def test_get_existing_zm_monitor_entities_handles_missing_integration_key(self, mock_filter):
        """Test entity retrieval handles entities without integration keys"""
        # Mock entity without integration key
        mock_entity = Mock()
        mock_entity.id = 999
        mock_entity.integration_key = None
        mock_filter.return_value = [mock_entity]
        
        result = ProcessingResult(title='Test')
        result_dict = self.synchronizer._get_existing_zm_monitor_entities(result)
        
        # Should add error message
        self.assertIn('ZM entity found without integration name', result.error_list[0])
        
        # Should create mock integration key
        self.assertEqual(len(result_dict), 1)
        mock_key = list(result_dict.keys())[0]
        self.assertEqual(mock_key.integration_name, '1000999')  # 1000000 + entity.id
    
    @patch.object(Entity.objects, 'filter')
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
        
        result = ProcessingResult(title='Test')
        result_dict = self.synchronizer._get_existing_zm_monitor_entities(result)
        
        # Should only include monitor entity
        self.assertEqual(len(result_dict), 1)
        self.assertIn(monitor_key, result_dict)
        self.assertNotIn(other_key, result_dict)


class TestZoneMinderSynchronizerEntityCreation(TestCase):
    """Test entity creation with database transactions"""
    
    def setUp(self):
        self.synchronizer = ZoneMinderSynchronizer()
        
        # Mock the zm_manager
        self.mock_manager = Mock()
        self.mock_manager.ZM_ENTITY_NAME = 'ZoneMinder'
        self.mock_manager.ZM_MONITOR_INTEGRATION_NAME_PREFIX = 'monitor'
        self.mock_manager.VIDEO_STREAM_SENSOR_PREFIX = 'monitor.video_stream'
        self.mock_manager.MOVEMENT_SENSOR_PREFIX = 'monitor.motion'
        self.mock_manager.MONITOR_FUNCTION_SENSOR_PREFIX = 'monitor.function'
        self.mock_manager.MOVEMENT_EVENT_PREFIX = 'monitor.motion'
        self.mock_manager.should_add_alarm_events = True
        self.synchronizer._zm_manager = self.mock_manager
    
    @patch('hi.services.zoneminder.zm_sync.transaction.atomic')
    @patch('hi.services.zoneminder.zm_sync.HiModelHelper.create_discrete_controller')
    @patch.object(Entity, 'save')
    def test_create_zm_entity_uses_transaction(self, mock_save, mock_create_controller, mock_atomic):
        """Test _create_zm_entity uses database transaction"""
        run_state_dict = {'start': 'start', 'stop': 'stop'}
        
        mock_integration_key = IntegrationKey(integration_id='zm', integration_name='system')
        self.mock_manager._zm_integration_key.return_value = mock_integration_key
        self.mock_manager._zm_run_state_integration_key.return_value = IntegrationKey(
            integration_id='zm', integration_name='run.state'
        )
        
        result = ProcessingResult(title='Test')
        self.synchronizer._create_zm_entity(run_state_dict, result)
        
        mock_atomic.assert_called_once()
        mock_save.assert_called_once()
        mock_create_controller.assert_called_once()
    
    @patch('hi.services.zoneminder.zm_sync.transaction.atomic')
    @patch('hi.services.zoneminder.zm_sync.HiModelHelper.create_video_stream_sensor')
    @patch('hi.services.zoneminder.zm_sync.HiModelHelper.create_movement_sensor')
    @patch('hi.services.zoneminder.zm_sync.HiModelHelper.create_discrete_controller')
    @patch('hi.services.zoneminder.zm_sync.HiModelHelper.create_movement_event_definition')
    @patch.object(Entity, 'save')
    def test_create_monitor_entity_creates_all_components(self, mock_save, mock_create_event, 
                                                         mock_create_controller, mock_create_movement,
                                                         mock_create_video, mock_atomic):
        """Test _create_monitor_entity creates all required sensors and controllers"""
        # Mock monitor
        mock_monitor = Mock()
        mock_monitor.id.return_value = 123
        mock_monitor.name.return_value = 'Front Door'
        
        # Mock integration key generation
        entity_key = IntegrationKey(integration_id='zm', integration_name='monitor.123')
        video_key = IntegrationKey(integration_id='zm', integration_name='monitor.video_stream.123')
        movement_key = IntegrationKey(integration_id='zm', integration_name='monitor.motion.123')
        function_key = IntegrationKey(integration_id='zm', integration_name='monitor.function.123')
        event_key = IntegrationKey(integration_id='zm', integration_name='monitor.motion.123')
        
        self.mock_manager._to_integration_key.side_effect = [
            entity_key, video_key, movement_key, function_key, event_key
        ]
        
        # Mock movement sensor for event creation
        mock_movement_sensor = Mock()
        mock_movement_sensor.name = 'Front Door Motion'
        mock_movement_sensor.entity_state = Mock()
        mock_create_movement.return_value = mock_movement_sensor
        
        result = ProcessingResult(title='Test')
        self.synchronizer._create_monitor_entity(mock_monitor, result)
        
        # Should create all components
        mock_create_video.assert_called_once()
        mock_create_movement.assert_called_once()
        mock_create_controller.assert_called_once()
        mock_create_event.assert_called_once()
        
        # Should use transaction
        mock_atomic.assert_called_once()
        mock_save.assert_called_once()
    
    @patch('hi.services.zoneminder.zm_sync.transaction.atomic')
    @patch('hi.services.zoneminder.zm_sync.HiModelHelper.create_video_stream_sensor')
    @patch('hi.services.zoneminder.zm_sync.HiModelHelper.create_movement_sensor')
    @patch('hi.services.zoneminder.zm_sync.HiModelHelper.create_discrete_controller')
    @patch('hi.services.zoneminder.zm_sync.HiModelHelper.create_movement_event_definition')
    @patch.object(Entity, 'save')
    def test_create_monitor_entity_skips_events_when_disabled(self, mock_save, mock_create_event,
                                                            mock_create_controller, mock_create_movement,
                                                            mock_create_video, mock_atomic):
        """Test _create_monitor_entity skips event creation when alarm events disabled"""
        self.mock_manager.should_add_alarm_events = False
        
        mock_monitor = Mock()
        mock_monitor.id.return_value = 123
        mock_monitor.name.return_value = 'Front Door'
        
        # Mock integration key generation
        self.mock_manager._to_integration_key.side_effect = [
            Mock(), Mock(), Mock(), Mock()  # entity, video, movement, function keys
        ]
        
        mock_movement_sensor = Mock()
        mock_create_movement.return_value = mock_movement_sensor
        
        result = ProcessingResult(title='Test')
        self.synchronizer._create_monitor_entity(mock_monitor, result)
        
        # Should not create event
        mock_create_event.assert_not_called()
        
        # Should still create other components
        mock_create_video.assert_called_once()
        mock_create_movement.assert_called_once()
        mock_create_controller.assert_called_once()


class TestZoneMinderSynchronizerEntityUpdate(TestCase):
    """Test entity update logic"""
    
    def setUp(self):
        self.synchronizer = ZoneMinderSynchronizer()
    
    def test_update_entity_changes_name_when_different(self):
        """Test _update_entity updates name when monitor name changed"""
        mock_entity = Mock()
        mock_entity.name = 'Old Name'
        mock_entity.save = Mock()
        
        mock_monitor = Mock()
        mock_monitor.name.return_value = 'New Name'
        
        result = ProcessingResult(title='Test')
        self.synchronizer._update_entity(mock_entity, mock_monitor, result)
        
        self.assertEqual(mock_entity.name, 'New Name')
        mock_entity.save.assert_called_once()
        self.assertIn('Name changed for', result.message_list[0])
    
    def test_update_entity_no_change_when_name_same(self):
        """Test _update_entity doesn't save when name unchanged"""
        mock_entity = Mock()
        mock_entity.name = 'Same Name'
        mock_entity.save = Mock()
        
        mock_monitor = Mock()
        mock_monitor.name.return_value = 'Same Name'
        
        result = ProcessingResult(title='Test')
        self.synchronizer._update_entity(mock_entity, mock_monitor, result)
        
        mock_entity.save.assert_not_called()
        self.assertIn('No changes found for', result.message_list[0])


class TestZoneMinderSynchronizerEntityRemoval(TestCase):
    """Test intelligent entity deletion"""
    
    def setUp(self):
        self.synchronizer = ZoneMinderSynchronizer()
    
    @patch.object(ZoneMinderSynchronizer, '_remove_entity_intelligently')
    def test_remove_entity_calls_intelligent_deletion(self, mock_intelligent_removal):
        """Test _remove_entity calls intelligent deletion with correct parameters"""
        mock_entity = Mock()
        result = ProcessingResult(title='Test')
        
        self.synchronizer._remove_entity(mock_entity, result)
        
        mock_intelligent_removal.assert_called_once_with(mock_entity, result, 'ZoneMinder')


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
    
    @patch.object(Entity.objects, 'filter_by_integration_key')
    @patch.object(Sensor.objects, 'filter_by_integration_key')
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
        
        result = ProcessingResult(title='Test')
        self.synchronizer._sync_states(result)
        
        # Should update to real state names
        expected_states = {'default': 'default', 'Away': 'Away', 'HomeDay': 'HomeDay', 'Disabled': 'Disabled'}
        self.assertEqual(mock_entity_state.value_range_dict, expected_states)
        mock_entity_state.save.assert_called_once()
        self.assertIn('Updated ZM state values to:', result.message_list[0])
    
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
        
        result = ProcessingResult(title='Test')
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
    
    @patch.object(ZoneMinderSynchronizer, '_update_entity')
    def test_update_entity_with_real_monitor_name_changes(self, mock_update):
        """Test entity updates with realistic monitor name scenarios"""
        # Create scenario where monitor name changed from generic to real name
        mock_entity = Mock()
        mock_entity.name = 'Camera_001'  # Generic name
        
        # Use real monitor data
        real_monitor = self.create_mock_monitors_from_real_data()[0]  # HighCamera
        
        result = ProcessingResult(title='Test')
        self.synchronizer._update_entity(mock_entity, real_monitor, result)
        
        # Should update to real name from ZM API
        self.assertEqual(mock_entity.name, 'HighCamera')
        mock_entity.save.assert_called_once()
        self.assertIn('Name changed for', result.message_list[0])
    
    @patch.object(Entity.objects, 'filter')
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
        
        result = ProcessingResult(title='Test')
        result_dict = self.synchronizer._get_existing_zm_monitor_entities(result)
        
        # Should find 4 valid monitor entities + 1 with generated key for broken entity
        self.assertEqual(len(result_dict), 5)
        
        # Should have error message for broken entity
        self.assertIn('ZM entity found without integration name', result.error_list[0])
        
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
    
    @patch('hi.services.zoneminder.zm_sync.HiModelHelper.create_video_stream_sensor')
    @patch('hi.services.zoneminder.zm_sync.HiModelHelper.create_movement_sensor')
    @patch('hi.services.zoneminder.zm_sync.HiModelHelper.create_discrete_controller')
    @patch('hi.services.zoneminder.zm_sync.HiModelHelper.create_movement_event_definition')
    @patch('hi.services.zoneminder.zm_sync.transaction.atomic')
    @patch.object(Entity, 'save')
    def test_create_monitor_entity_with_real_monitor_variations(self, mock_save, mock_atomic,
                                                               mock_create_event, mock_create_controller,
                                                               mock_create_movement, mock_create_video):
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
                mock_create_video.reset_mock()
                mock_create_movement.reset_mock()
                mock_create_controller.reset_mock()
                mock_create_event.reset_mock()
                
                result = ProcessingResult(title='Test')
                self.synchronizer._create_monitor_entity(monitor, result)
                
                # Should create all components for each monitor
                mock_create_video.assert_called_once()
                mock_create_movement.assert_called_once() 
                mock_create_controller.assert_called_once()
                mock_create_event.assert_called_once()
                
                # Should save entity
                mock_save.assert_called_once()
                
                # Should use transaction
                mock_atomic.assert_called()
                
                # Should log creation
                self.assertIn('Create new camera entity:', result.message_list[0])