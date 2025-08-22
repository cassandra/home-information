from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from django.test import TestCase
import pytz

from hi.apps.entity.enums import EntityStateValue

from hi.services.zoneminder.monitors import ZoneMinderMonitor  
from hi.services.zoneminder.zm_models import ZmEvent, AggregatedMonitorState


class TestZoneMinderMonitorEventAggregation(TestCase):
    """
    Test the core event aggregation logic that fixes the bug where multiple
    events per monitor would overwrite each other in sensor responses.
    
    Tests all permutations of event combinations:
    - Open events: none, one, multiple
    - Closed events: none, one, multiple  
    - Cross product: 9 total scenarios
    """
    
    def setUp(self):
        self.monitor = ZoneMinderMonitor()
        
        # Create mock events with realistic data
        self.base_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=pytz.UTC)
        
        # Mock ZM API events for creating ZmEvent instances
        self.mock_open_event_1 = self._create_mock_zm_api_event(
            event_id='101', monitor_id=1, 
            start_time='2023-01-01T12:00:00', end_time=None
        )
        self.mock_open_event_2 = self._create_mock_zm_api_event(
            event_id='102', monitor_id=1,
            start_time='2023-01-01T12:05:00', end_time=None  
        )
        self.mock_closed_event_1 = self._create_mock_zm_api_event(
            event_id='201', monitor_id=1,
            start_time='2023-01-01T11:50:00', end_time='2023-01-01T11:55:00'
        )
        self.mock_closed_event_2 = self._create_mock_zm_api_event(
            event_id='202', monitor_id=1,
            start_time='2023-01-01T11:40:00', end_time='2023-01-01T11:45:00'
        )
        
        # Multi-monitor events for different monitors
        self.mock_monitor_2_open = self._create_mock_zm_api_event(
            event_id='301', monitor_id=2,
            start_time='2023-01-01T12:10:00', end_time=None
        )
        self.mock_monitor_2_closed = self._create_mock_zm_api_event(
            event_id='302', monitor_id=2, 
            start_time='2023-01-01T12:00:00', end_time='2023-01-01T12:05:00'
        )
    
    def _create_mock_zm_api_event(self, event_id, monitor_id, start_time, end_time):
        """Create mock ZM API event for creating ZmEvent instances."""
        mock_api_event = Mock()
        mock_api_event.id.return_value = event_id
        mock_api_event.monitor_id.return_value = monitor_id
        mock_api_event.get.return_value = {
            'StartTime': start_time,
            'EndTime': end_time,
            'MaxScoreFrameId': 1
        }
        mock_api_event.cause.return_value = 'Motion'
        mock_api_event.duration.return_value = 60
        mock_api_event.total_frames.return_value = 30
        mock_api_event.alarmed_frames.return_value = 15
        mock_api_event.score.return_value = 85
        mock_api_event.notes.return_value = 'Test event'
        return mock_api_event
    
    def _create_zm_event(self, mock_api_event):
        """Helper to create ZmEvent from mock API event."""
        return ZmEvent(zm_api_event=mock_api_event, zm_tzname='UTC')

    # Test Cases: All permutations of (open_count x closed_count)
    # where count ∈ {none, one, multiple} = 9 scenarios
    
    def test_no_open_no_closed_events(self):
        """Scenario: No events for monitor - should have no aggregated state."""
        open_events = []
        closed_events = []
        
        aggregated_states = self.monitor._aggregate_monitor_states(open_events, closed_events)
        
        # Behavior: No states should be generated
        self.assertEqual(len(aggregated_states), 0)
    
    def test_no_open_one_closed_event(self):
        """Scenario: One closed event - monitor should be IDLE."""
        open_events = []
        closed_events = [self._create_zm_event(self.mock_closed_event_1)]
        
        aggregated_states = self.monitor._aggregate_monitor_states(open_events, closed_events)
        
        # Behavior: Single IDLE state with closed event timestamp
        self.assertEqual(len(aggregated_states), 1)
        self.assertIn(1, aggregated_states)
        
        state = aggregated_states[1]
        self.assertEqual(state.monitor_id, 1)
        self.assertEqual(state.current_state, EntityStateValue.IDLE)
        self.assertEqual(state.effective_timestamp, closed_events[0].end_datetime)
        self.assertEqual(state.canonical_event, closed_events[0])
        self.assertEqual(state.all_events, closed_events)
        self.assertTrue(state.is_idle)
        self.assertFalse(state.is_active)
    
    def test_no_open_multiple_closed_events(self):
        """Scenario: Multiple closed events - monitor should be IDLE with latest end time."""
        open_events = []
        closed_events = [
            self._create_zm_event(self.mock_closed_event_1),  # ends at 11:55
            self._create_zm_event(self.mock_closed_event_2),  # ends at 11:45
        ]
        
        aggregated_states = self.monitor._aggregate_monitor_states(open_events, closed_events)
        
        # Behavior: IDLE state with latest closed event's end time
        self.assertEqual(len(aggregated_states), 1)
        state = aggregated_states[1]
        
        self.assertEqual(state.current_state, EntityStateValue.IDLE)
        # Should use latest end time (11:55, not 11:45)
        latest_end_time = max(event.end_datetime for event in closed_events)
        self.assertEqual(state.effective_timestamp, latest_end_time)
        # Canonical event should be the one with latest end time  
        latest_event = max(closed_events, key=lambda e: e.end_datetime)
        self.assertEqual(state.canonical_event, latest_event)
        self.assertEqual(len(state.all_events), 2)
    
    def test_one_open_no_closed_events(self):
        """Scenario: One open event - monitor should be ACTIVE."""
        open_events = [self._create_zm_event(self.mock_open_event_1)]
        closed_events = []
        
        aggregated_states = self.monitor._aggregate_monitor_states(open_events, closed_events)
        
        # Behavior: Single ACTIVE state with open event start timestamp
        self.assertEqual(len(aggregated_states), 1)
        state = aggregated_states[1]
        
        self.assertEqual(state.current_state, EntityStateValue.ACTIVE)
        self.assertEqual(state.effective_timestamp, open_events[0].start_datetime)
        self.assertEqual(state.canonical_event, open_events[0])
        self.assertEqual(state.all_events, open_events)
        self.assertTrue(state.is_active)
        self.assertFalse(state.is_idle)
    
    def test_one_open_one_closed_event(self):
        """Scenario: One open + one closed event - monitor should be ACTIVE (open takes precedence)."""
        open_events = [self._create_zm_event(self.mock_open_event_1)]
        closed_events = [self._create_zm_event(self.mock_closed_event_1)]
        
        aggregated_states = self.monitor._aggregate_monitor_states(open_events, closed_events)
        
        # Behavior: ACTIVE state because any open event means active
        self.assertEqual(len(aggregated_states), 1)  
        state = aggregated_states[1]
        
        self.assertEqual(state.current_state, EntityStateValue.ACTIVE)
        self.assertEqual(state.effective_timestamp, open_events[0].start_datetime)
        self.assertEqual(state.canonical_event, open_events[0])
        # All events should be included
        self.assertEqual(len(state.all_events), 2)
        self.assertIn(open_events[0], state.all_events)
        self.assertIn(closed_events[0], state.all_events)
    
    def test_one_open_multiple_closed_events(self):
        """Scenario: One open + multiple closed events - monitor should be ACTIVE."""
        open_events = [self._create_zm_event(self.mock_open_event_1)]
        closed_events = [
            self._create_zm_event(self.mock_closed_event_1),
            self._create_zm_event(self.mock_closed_event_2),
        ]
        
        aggregated_states = self.monitor._aggregate_monitor_states(open_events, closed_events)
        
        # Behavior: ACTIVE state with open event timestamp
        state = aggregated_states[1]
        self.assertEqual(state.current_state, EntityStateValue.ACTIVE)
        self.assertEqual(state.effective_timestamp, open_events[0].start_datetime)
        self.assertEqual(state.canonical_event, open_events[0])
        self.assertEqual(len(state.all_events), 3)  # 1 open + 2 closed
    
    def test_multiple_open_no_closed_events(self):
        """Scenario: Multiple open events - monitor should be ACTIVE with earliest start time."""
        open_events = [
            self._create_zm_event(self.mock_open_event_1),  # starts at 12:00
            self._create_zm_event(self.mock_open_event_2),  # starts at 12:05
        ]
        closed_events = []
        
        aggregated_states = self.monitor._aggregate_monitor_states(open_events, closed_events)
        
        # Behavior: ACTIVE state with earliest open event start time
        state = aggregated_states[1]
        self.assertEqual(state.current_state, EntityStateValue.ACTIVE)
        # Should use earliest start time (12:00, not 12:05)
        earliest_start_time = min(event.start_datetime for event in open_events)
        self.assertEqual(state.effective_timestamp, earliest_start_time)
        # Canonical event should be the earliest one
        earliest_event = min(open_events, key=lambda e: e.start_datetime)
        self.assertEqual(state.canonical_event, earliest_event)
        self.assertEqual(len(state.all_events), 2)
    
    def test_multiple_open_one_closed_event(self):
        """Scenario: Multiple open + one closed event - monitor should be ACTIVE."""
        open_events = [
            self._create_zm_event(self.mock_open_event_1),
            self._create_zm_event(self.mock_open_event_2),
        ]
        closed_events = [self._create_zm_event(self.mock_closed_event_1)]
        
        aggregated_states = self.monitor._aggregate_monitor_states(open_events, closed_events)
        
        # Behavior: ACTIVE state with earliest open event timestamp
        state = aggregated_states[1]
        self.assertEqual(state.current_state, EntityStateValue.ACTIVE)
        earliest_open_time = min(event.start_datetime for event in open_events)
        self.assertEqual(state.effective_timestamp, earliest_open_time)
        self.assertEqual(len(state.all_events), 3)  # 2 open + 1 closed
    
    def test_multiple_open_multiple_closed_events(self):
        """Scenario: Multiple open + multiple closed events - monitor should be ACTIVE."""
        open_events = [
            self._create_zm_event(self.mock_open_event_1),
            self._create_zm_event(self.mock_open_event_2),
        ]
        closed_events = [
            self._create_zm_event(self.mock_closed_event_1),
            self._create_zm_event(self.mock_closed_event_2),
        ]
        
        aggregated_states = self.monitor._aggregate_monitor_states(open_events, closed_events)
        
        # Behavior: ACTIVE state with earliest open event timestamp
        state = aggregated_states[1]
        self.assertEqual(state.current_state, EntityStateValue.ACTIVE)
        earliest_open_time = min(event.start_datetime for event in open_events)
        self.assertEqual(state.effective_timestamp, earliest_open_time)
        self.assertEqual(len(state.all_events), 4)  # 2 open + 2 closed

    def test_multiple_monitors_with_different_states(self):
        """Scenario: Multiple monitors with different event combinations."""
        # Monitor 1: ACTIVE (has open event)
        monitor_1_open = [self._create_zm_event(self.mock_open_event_1)]
        monitor_1_closed = [self._create_zm_event(self.mock_closed_event_1)]
        
        # Monitor 2: IDLE (only closed event)  
        monitor_2_open = []
        monitor_2_closed = [self._create_zm_event(self.mock_monitor_2_closed)]
        
        all_open_events = monitor_1_open + monitor_2_open
        all_closed_events = monitor_1_closed + monitor_2_closed
        
        aggregated_states = self.monitor._aggregate_monitor_states(all_open_events, all_closed_events)
        
        # Behavior: Two separate monitor states
        self.assertEqual(len(aggregated_states), 2)
        self.assertIn(1, aggregated_states)
        self.assertIn(2, aggregated_states)
        
        # Monitor 1 should be ACTIVE
        monitor_1_state = aggregated_states[1]
        self.assertEqual(monitor_1_state.current_state, EntityStateValue.ACTIVE)
        self.assertTrue(monitor_1_state.is_active)
        
        # Monitor 2 should be IDLE
        monitor_2_state = aggregated_states[2]
        self.assertEqual(monitor_2_state.current_state, EntityStateValue.IDLE)
        self.assertTrue(monitor_2_state.is_idle)

    def test_events_are_sorted_chronologically(self):
        """Test that all_events are sorted chronologically within each monitor."""
        # Create events with mixed timestamps
        open_events = [self._create_zm_event(self.mock_open_event_2)]  # 12:05
        closed_events = [
            self._create_zm_event(self.mock_closed_event_2),  # 11:40-11:45 (earlier)
            self._create_zm_event(self.mock_closed_event_1),  # 11:50-11:55 (later)  
        ]
        
        aggregated_states = self.monitor._aggregate_monitor_states(open_events, closed_events)
        
        # Behavior: all_events should be sorted by start_datetime
        state = aggregated_states[1]
        all_events = state.all_events
        
        # Expected chronological order: 202 (11:40), 201 (11:50), 102 (12:05)
        expected_event_ids = ['202', '201', '102']
        
        self.assertEqual(len(all_events), 3)
        for i, expected_id in enumerate(expected_event_ids):
            self.assertEqual(all_events[i].event_id, expected_id,
                             f"Event at position {i} should be {expected_id}, got {all_events[i].event_id}")


class TestZoneMinderMonitorSensorResponseGeneration(TestCase):
    """
    Test sensor response generation from aggregated monitor states.
    This tests the integration between aggregation and sensor response creation.
    """
    
    def setUp(self):
        self.monitor = ZoneMinderMonitor()
        
        # Mock the ZM manager and sensor response creation methods
        self.mock_zm_manager = Mock()
        self.monitor._zm_manager = self.mock_zm_manager
        
        # Mock the _create_movement_*_sensor_response methods
        self.mock_active_response = Mock()
        self.mock_active_response.integration_key = 'test.monitor.1.movement'
        self.mock_active_response.timestamp = datetime(2023, 1, 1, 12, 0, 0, tzinfo=pytz.UTC)
        
        self.mock_idle_response = Mock() 
        self.mock_idle_response.integration_key = 'test.monitor.2.movement'
        self.mock_idle_response.timestamp = datetime(2023, 1, 1, 12, 5, 0, tzinfo=pytz.UTC)
        
        self.monitor._create_movement_active_sensor_response = Mock(return_value=self.mock_active_response)
        self.monitor._create_movement_idle_sensor_response = Mock(return_value=self.mock_idle_response)
        
        # Create test aggregated states
        self.test_event = Mock()
        self.test_event.event_id = '123'
        self.test_event.is_open = True
        
        self.active_state = AggregatedMonitorState(
            monitor_id=1,
            current_state=EntityStateValue.ACTIVE,
            effective_timestamp=datetime(2023, 1, 1, 12, 0, 0, tzinfo=pytz.UTC),
            canonical_event=self.test_event,
            all_events=[self.test_event]
        )
        
        self.idle_state = AggregatedMonitorState(
            monitor_id=2,
            current_state=EntityStateValue.IDLE,
            effective_timestamp=datetime(2023, 1, 1, 12, 5, 0, tzinfo=pytz.UTC),
            canonical_event=self.test_event,
            all_events=[self.test_event]
        )
    
    def test_active_state_generates_active_sensor_response(self):
        """Test that ACTIVE monitor state generates active sensor response."""
        aggregated_states = {1: self.active_state}
        
        sensor_responses = self.monitor._generate_sensor_responses_from_states(aggregated_states)
        
        # Behavior: Should create active sensor response
        self.monitor._create_movement_active_sensor_response.assert_called_once_with(self.test_event)
        self.monitor._create_movement_idle_sensor_response.assert_not_called()
        
        # Should have one sensor response with overridden timestamp
        self.assertEqual(len(sensor_responses), 1)
        response = sensor_responses['test.monitor.1.movement']
        self.assertEqual(response.timestamp, self.active_state.effective_timestamp)
    
    def test_idle_state_generates_idle_sensor_response(self):
        """Test that IDLE monitor state generates idle sensor response.""" 
        aggregated_states = {2: self.idle_state}
        
        sensor_responses = self.monitor._generate_sensor_responses_from_states(aggregated_states)
        
        # Behavior: Should create idle sensor response
        self.monitor._create_movement_idle_sensor_response.assert_called_once_with(self.test_event)
        self.monitor._create_movement_active_sensor_response.assert_not_called()
        
        # Should have one sensor response with overridden timestamp
        self.assertEqual(len(sensor_responses), 1)
        response = sensor_responses['test.monitor.2.movement']
        self.assertEqual(response.timestamp, self.idle_state.effective_timestamp)
    
    def test_multiple_states_generate_multiple_responses(self):
        """Test that multiple monitor states generate separate sensor responses."""
        aggregated_states = {
            1: self.active_state,
            2: self.idle_state
        }
        
        sensor_responses = self.monitor._generate_sensor_responses_from_states(aggregated_states)
        
        # Behavior: Should create both types of responses
        self.monitor._create_movement_active_sensor_response.assert_called_once()
        self.monitor._create_movement_idle_sensor_response.assert_called_once()
        
        # Should have two sensor responses (one per monitor)
        self.assertEqual(len(sensor_responses), 2)
    
    def test_event_cache_updates_for_all_events(self):
        """Test that event processing caches are updated for all events in aggregated state."""
        # Create state with multiple events (open and closed)
        open_event = Mock()
        open_event.event_id = '101'
        open_event.is_open = True
        
        closed_event = Mock()
        closed_event.event_id = '201'  
        closed_event.is_open = False
        
        state_with_multiple_events = AggregatedMonitorState(
            monitor_id=1,
            current_state=EntityStateValue.ACTIVE,
            effective_timestamp=datetime(2023, 1, 1, 12, 0, 0, tzinfo=pytz.UTC),
            canonical_event=open_event,
            all_events=[open_event, closed_event]
        )
        
        aggregated_states = {1: state_with_multiple_events}
        
        # Initialize empty caches
        self.monitor._start_processed_event_ids = {}
        self.monitor._fully_processed_event_ids = {}
        
        self.monitor._generate_sensor_responses_from_states(aggregated_states)
        
        # Behavior: Verify cache updates
        # Open event should be in start_processed only
        self.assertIn('101', self.monitor._start_processed_event_ids)
        self.assertNotIn('101', self.monitor._fully_processed_event_ids)
        
        # Closed event should be in both caches
        self.assertIn('201', self.monitor._start_processed_event_ids)
        self.assertIn('201', self.monitor._fully_processed_event_ids)


class TestZoneMinderMonitorIntegrationScenarios(TestCase):
    """
    Test complete integration scenarios that simulate the real bug conditions.
    These test the fix for the original issue where multiple events per monitor
    would create chronological disorders and stuck ACTIVE states.
    """
    
    def setUp(self):
        self.monitor = ZoneMinderMonitor()
        self.monitor._start_processed_event_ids = {}
        self.monitor._fully_processed_event_ids = {}
        
        # Mock external dependencies
        with patch.object(self.monitor, 'zm_manager') as mock_zm_manager:
            mock_zm_manager.return_value._to_integration_key.side_effect = lambda prefix, monitor_id: f'{prefix}.{monitor_id}'
            
            self.monitor._create_movement_active_sensor_response = Mock(
                side_effect=self._create_mock_active_response
            )
            self.monitor._create_movement_idle_sensor_response = Mock(
                side_effect=self._create_mock_idle_response
            )
    
    def _create_mock_active_response(self, zm_event):
        response = Mock()
        response.integration_key = f'movement.{zm_event.monitor_id}'
        response.timestamp = zm_event.start_datetime
        return response
    
    def _create_mock_idle_response(self, zm_event):
        response = Mock()
        response.integration_key = f'movement.{zm_event.monitor_id}'
        response.timestamp = zm_event.end_datetime
        return response
    
    def _create_test_zm_event(self, event_id, monitor_id, start_time, end_time=None):
        """Helper to create ZmEvent with minimal mocking."""
        event = Mock()
        event.event_id = event_id
        event.monitor_id = monitor_id
        event.start_datetime = start_time
        event.end_datetime = end_time
        event.is_open = end_time is None
        return event
    
    def test_original_bug_scenario_multiple_events_same_monitor(self):
        """
        Test the original bug scenario: multiple events for same monitor in one poll.
        This should now produce single sensor response instead of overwrites.
        """
        base_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=pytz.UTC)
        
        # Scenario: Monitor 1 has Event A (closed) and Event B (open) in same poll  
        event_a_closed = self._create_test_zm_event(
            'A', 1, base_time, base_time + timedelta(minutes=5)
        )
        event_b_open = self._create_test_zm_event(
            'B', 1, base_time + timedelta(minutes=10), None
        )
        
        open_events = [event_b_open]
        closed_events = [event_a_closed]
        
        # Use the new two-phase processing
        aggregated_states = self.monitor._aggregate_monitor_states(open_events, closed_events)
        sensor_responses = self.monitor._generate_sensor_responses_from_states(aggregated_states)
        
        # Behavior: Should produce exactly ONE sensor response for monitor 1
        self.assertEqual(len(sensor_responses), 1)
        response = sensor_responses['movement.1']
        
        # Should be ACTIVE (because event B is open) with correct timestamp
        self.assertEqual(response.timestamp, event_b_open.start_datetime)
        
        # Verify both events are processed in caches
        self.assertIn('A', self.monitor._start_processed_event_ids)
        self.assertIn('A', self.monitor._fully_processed_event_ids)
        self.assertIn('B', self.monitor._start_processed_event_ids)
        self.assertNotIn('B', self.monitor._fully_processed_event_ids)  # Open event not fully processed
    
    def test_chronological_ordering_preserved(self):
        """
        Test that the new implementation preserves chronological ordering.
        Previously, processing open events first then closed events could create
        backwards timestamps.
        """
        base_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=pytz.UTC)
        
        # Event A: 12:00 - 12:05 (closed, earlier)
        # Event B: 12:10 - still open (open, later)
        event_a_closed = self._create_test_zm_event(
            'A', 1, base_time, base_time + timedelta(minutes=5)
        )
        event_b_open = self._create_test_zm_event(
            'B', 1, base_time + timedelta(minutes=10), None
        )
        
        open_events = [event_b_open]
        closed_events = [event_a_closed]
        
        aggregated_states = self.monitor._aggregate_monitor_states(open_events, closed_events)
        
        # Behavior: Chronological ordering should be preserved in all_events
        state = aggregated_states[1]
        all_events = state.all_events
        
        # Events should be ordered by start time: A (12:00), then B (12:10)
        self.assertEqual(len(all_events), 2)
        self.assertEqual(all_events[0].event_id, 'A')  # Earlier event first
        self.assertEqual(all_events[1].event_id, 'B')  # Later event second
        
        # Since monitor is ACTIVE, timestamp should be from earliest OPEN event (B)
        self.assertEqual(state.effective_timestamp, event_b_open.start_datetime)
    
    def test_no_stuck_active_states(self):
        """
        Test that the fix prevents stuck ACTIVE states.
        Original bug: if closed event overwrote open event response,
        monitor would appear IDLE when it should be ACTIVE.
        """
        base_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=pytz.UTC)
        
        # Scenario: Monitor has both open and closed events
        # Previously: closed event would overwrite open event → stuck IDLE
        # Now: aggregation should correctly show ACTIVE
        open_event = self._create_test_zm_event(
            'open_123', 1, base_time, None
        )
        closed_event = self._create_test_zm_event(
            'closed_456', 1, base_time - timedelta(minutes=10),
            base_time - timedelta(minutes=5)
        )
        
        open_events = [open_event]
        closed_events = [closed_event]
        
        aggregated_states = self.monitor._aggregate_monitor_states(open_events, closed_events)
        sensor_responses = self.monitor._generate_sensor_responses_from_states(aggregated_states)
        
        # Behavior: Monitor should be ACTIVE, not stuck in IDLE
        self.assertEqual(len(aggregated_states), 1)
        state = aggregated_states[1]
        self.assertEqual(state.current_state, EntityStateValue.ACTIVE)
        self.assertTrue(state.is_active)
        
        # Sensor response should reflect ACTIVE state
        response = sensor_responses['movement.1']
        # Mock active response uses start_datetime
        self.assertEqual(response.timestamp, open_event.start_datetime)
    
    def test_edge_case_simultaneous_events(self):
        """
        Test edge case where events have same timestamps.
        Should handle gracefully without errors.
        """
        same_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=pytz.UTC)
        
        # Two events with identical start times
        event_1 = self._create_test_zm_event('1', 1, same_time, None)
        event_2 = self._create_test_zm_event('2', 1, same_time, None)
        
        open_events = [event_1, event_2]
        closed_events = []
        
        aggregated_states = self.monitor._aggregate_monitor_states(open_events, closed_events)
        
        # Behavior: Should handle gracefully, produce ACTIVE state
        self.assertEqual(len(aggregated_states), 1)
        state = aggregated_states[1]
        self.assertEqual(state.current_state, EntityStateValue.ACTIVE)
        self.assertEqual(len(state.all_events), 2)
        # Should use one of the simultaneous events as canonical
        self.assertIn(state.canonical_event, [event_1, event_2])
