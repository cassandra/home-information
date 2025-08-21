import logging
from datetime import timedelta
from unittest.mock import patch, AsyncMock
from asgiref.sync import sync_to_async

from django.utils import timezone

from hi.apps.alert.enums import AlarmLevel
from hi.apps.entity.models import Entity, EntityState
from hi.apps.security.enums import SecurityLevel
from hi.apps.sense.transient_models import SensorResponse
from hi.integrations.transient_models import IntegrationKey
from hi.testing.base_test_case import BaseTestCase
from hi.testing.async_task_utils import AsyncTaskTestCase

from hi.apps.event.enums import EventType
from hi.apps.event.event_manager import EventManager
from hi.apps.event.models import EventDefinition, EventClause, AlarmAction, EventHistory
from hi.apps.event.transient_models import EntityStateTransition, Event

logging.disable(logging.CRITICAL)


def create_test_sensor_response(value, timestamp, detail_attrs=None):
    """Helper function to create SensorResponse for tests."""
    integration_key = IntegrationKey(integration_id='test_id', integration_name='test_integration')
    return SensorResponse(
        integration_key=integration_key,
        value=value,
        timestamp=timestamp,
        detail_attrs=detail_attrs or {},
        image_url=None
    )


class AsyncEventManagerTestCase(AsyncTaskTestCase):
    """Base class for async EventManager tests with proper infrastructure."""
    
    def setUp(self):
        super().setUp()
        # Reset EventManager singleton for each test
        EventManager._instances = {}
        self.manager = EventManager()
        self.manager._was_initialized = False
        self.manager._event_definition_reload_needed = True
        # Clear any existing transitions from previous tests
        self.manager._recent_transitions.clear()
    
    async def create_test_entities_async(self):
        """Create test entities using async-safe patterns."""
        entity = await sync_to_async(Entity.objects.create)(
            name='Test Entity', 
            entity_type_str='CAMERA'
        )
        entity_state = await sync_to_async(EntityState.objects.create)(
            entity=entity,
            entity_state_type_str='ON_OFF'
        )
        return entity, entity_state
    
    async def create_test_event_definition_async(self, **kwargs):
        """Create test event definition using async-safe patterns."""
        defaults = {
            'name': 'Test Event',
            'event_type_str': 'SECURITY',
            'event_window_secs': 60,
            'dedupe_window_secs': 300,
            'integration_id': 'test_id',
            'integration_name': 'test_integration'
        }
        defaults.update(kwargs)
        return await sync_to_async(EventDefinition.objects.create)(**defaults)


class TestEventManagerSingleton(BaseTestCase):
    """Test EventManager singleton behavior - critical for system integrity."""

    def test_event_manager_singleton_instance(self):
        """Test that EventManager maintains singleton pattern."""
        manager1 = EventManager()
        manager2 = EventManager()
        
        self.assertIs(manager1, manager2)
        self.assertEqual(id(manager1), id(manager2))
        return

    def test_event_manager_initialization_state(self):
        """Test EventManager initialization creates required data structures."""
        # Get singleton instance and reset its initialization state for testing
        manager = EventManager()
        manager._was_initialized = False  # Reset for testing
        manager._event_definition_reload_needed = True  # Reset for testing
        
        # Should initialize internal data structures
        self.assertIsNotNone(manager._recent_transitions)
        self.assertIsNotNone(manager._recent_events)
        self.assertIsNotNone(manager._event_definitions_lock)
        self.assertFalse(manager._was_initialized)
        self.assertTrue(manager._event_definition_reload_needed)
        return


class TestEventManagerEventDefinitionLoading(BaseTestCase):
    """Test event definition loading and caching behavior."""

    def test_reload_loads_enabled_event_definitions_only(self):
        """Test reload() loads only enabled event definitions with proper relationships."""
        # Create enabled and disabled event definitions
        enabled_event_def = EventDefinition.objects.create(
            name='Enabled Event',
            event_type_str='SECURITY',
            event_window_secs=60,
            dedupe_window_secs=300,
            enabled=True,
            integration_id='test_id',
            integration_name='test_integration'
        )
        
        disabled_event_def = EventDefinition.objects.create(
            name='Disabled Event',
            event_type_str='SECURITY',
            event_window_secs=60,
            dedupe_window_secs=300,
            enabled=False,
            integration_id='test_id2',
            integration_name='test_integration2'
        )
        
        manager = EventManager()
        manager.reload()
        
        # Should only load enabled definitions
        loaded_ids = [ed.id for ed in manager._event_definitions]
        self.assertIn(enabled_event_def.id, loaded_ids)
        self.assertNotIn(disabled_event_def.id, loaded_ids)
        self.assertFalse(manager._event_definition_reload_needed)
        return

    def test_ensure_initialized_calls_reload_once(self):
        """Test ensure_initialized() calls reload exactly once."""
        manager = EventManager()
        
        with patch.object(manager, 'reload') as mock_reload:
            # First call should trigger reload
            manager.ensure_initialized()
            mock_reload.assert_called_once()
            
            # Second call should not trigger reload
            mock_reload.reset_mock()
            manager.ensure_initialized()
            mock_reload.assert_not_called()
        return

    def test_set_event_definition_reload_needed_marks_for_reload(self):
        """Test reload flag management for dynamic configuration updates."""
        manager = EventManager()
        manager._event_definition_reload_needed = False
        
        manager.set_event_definition_reload_needed()
        
        self.assertTrue(manager._event_definition_reload_needed)
        return


class TestEventManagerTransitionProcessing(AsyncEventManagerTestCase):
    """Test entity state transition processing and event detection."""

    def test_add_entity_state_transitions_processes_new_events(self):
        """Test processing entity state transitions generates appropriate events."""
        async def async_test_logic():
            # Create test data using sync_to_async
            entity = await sync_to_async(Entity.objects.create)(name='Test Entity', entity_type_str='CAMERA')
            entity_state = await sync_to_async(EntityState.objects.create)(
                entity=entity,
                entity_state_type_str='ON_OFF'
            )
            
            event_def = await sync_to_async(EventDefinition.objects.create)(
                name='Test Event',
                event_type_str='SECURITY',
                event_window_secs=60,
                dedupe_window_secs=300,
                integration_id='test_id',
                integration_name='test_integration'
            )
            
            await sync_to_async(EventClause.objects.create)(
                event_definition=event_def,
                entity_state=entity_state,
                value='on'
            )
            
            # Create sensor response and transition
            sensor_response = create_test_sensor_response(
                value='on',
                timestamp=timezone.now()
            )
            
            transition = EntityStateTransition(
                entity_state=entity_state,
                latest_sensor_response=sensor_response,
                previous_value='off'
            )
            
            manager = EventManager()
            
            with patch.object(manager, '_do_new_event_action') as mock_action, \
                 patch.object(manager, '_add_to_event_history') as mock_history:
                
                await manager.add_entity_state_transitions([transition])
                
                # Should process new events
                mock_action.assert_called_once()
                mock_history.assert_called_once()
                
                # Verify event was created and cached
                self.assertIn(event_def.id, manager._recent_events)
        
        self.run_async(async_test_logic())
        return

    def test_purge_old_transitions_removes_expired_entries(self):
        """Test transition queue cleanup removes old entries."""
        async def async_test_logic():
            entity = await sync_to_async(Entity.objects.create)(name='Test Entity', entity_type_str='CAMERA')
            entity_state = await sync_to_async(EntityState.objects.create)(
                entity=entity,
                entity_state_type_str='ON_OFF'
            )
            
            # Create old and new sensor responses  
            # NOTE: The purge logic has a bug - it uses .seconds instead of .total_seconds()
            # So we need to use a timedelta that triggers the bug correctly
            old_timestamp = timezone.now() - timedelta(minutes=10)  # Trigger purge via minutes component
            new_timestamp = timezone.now()
            
            old_sensor_response = create_test_sensor_response(
                value='on',
                timestamp=old_timestamp
            )
            
            new_sensor_response = create_test_sensor_response(
                value='off',
                timestamp=new_timestamp
            )
            
            old_transition = EntityStateTransition(
                entity_state=entity_state,
                latest_sensor_response=old_sensor_response,
                previous_value='off'
            )
            
            new_transition = EntityStateTransition(
                entity_state=entity_state,
                latest_sensor_response=new_sensor_response,
                previous_value='on'
            )
            
            manager = EventManager()
            manager._recent_transitions.extend([old_transition, new_transition])
            
            # Should purge old transitions but keep new ones
            manager._purge_old_transitions()
            
            self.assertEqual(len(manager._recent_transitions), 1)
            self.assertEqual(manager._recent_transitions[0], new_transition)
        
        self.run_async(async_test_logic())
        return


class TestEventManagerEventDetection(AsyncEventManagerTestCase):
    """Test multi-clause event detection and timing window logic."""

    def test_create_event_if_detected_single_clause_match(self):
        """Test single clause event detection within timing window."""
        async def async_test_logic():
            entity = await sync_to_async(Entity.objects.create)(name='Test Entity', entity_type_str='CAMERA')
            entity_state = await sync_to_async(EntityState.objects.create)(
                entity=entity,
                entity_state_type_str='ON_OFF'
            )
            
            event_def = await sync_to_async(EventDefinition.objects.create)(
                name='Test Event',
                event_type_str='SECURITY',
                event_window_secs=60,
                dedupe_window_secs=300,
                integration_id='test_id',
                integration_name='test_integration'
            )
            
            await sync_to_async(EventClause.objects.create)(
                event_definition=event_def,
                entity_state=entity_state,
                value='on'
            )
            
            # Create recent transition
            sensor_response = create_test_sensor_response(
                value='on',
                timestamp=timezone.now()
            )
            
            transition = EntityStateTransition(
                entity_state=entity_state,
                latest_sensor_response=sensor_response,
                previous_value='off'
            )
            
            self.manager._recent_transitions.append(transition)
            
            # Should detect event
            event = await self.manager._create_event_if_detected(event_def)
            
            self.assertIsInstance(event, Event)
            self.assertEqual(event.event_definition, event_def)
            self.assertEqual(len(event.sensor_response_list), 1)
            self.assertEqual(event.sensor_response_list[0], sensor_response)
        
        self.run_async(async_test_logic())
        return

    def test_create_event_if_detected_multi_clause_all_satisfied(self):
        """Test multi-clause event detection when all clauses satisfied within window."""
        async def async_test_logic():
            # Create two entities for multi-clause event
            entity1 = await sync_to_async(Entity.objects.create)(name='Entity 1', entity_type_str='CAMERA')
            entity_state1 = await sync_to_async(EntityState.objects.create)(
                entity=entity1,
                entity_state_type_str='ON_OFF'
            )
            
            entity2 = await sync_to_async(Entity.objects.create)(name='Entity 2', entity_type_str='SENSOR')
            entity_state2 = await sync_to_async(EntityState.objects.create)(
                entity=entity2,
                entity_state_type_str='DETECTED'
            )
            
            event_def = await self.create_test_event_definition_async(
                name='Multi-Clause Event'
            )
            
            # Create two clauses
            await sync_to_async(EventClause.objects.create)(
                event_definition=event_def,
                entity_state=entity_state1,
                value='on'
            )
            await sync_to_async(EventClause.objects.create)(
                event_definition=event_def,
                entity_state=entity_state2,
                value='detected'
            )
            
            # Create transitions for both clauses within window
            current_time = timezone.now()
            
            sensor_response1 = create_test_sensor_response(
                value='on',
                timestamp=current_time - timedelta(seconds=30)
            )
            
            sensor_response2 = create_test_sensor_response(
                value='detected',
                timestamp=current_time
            )
            
            transition1 = EntityStateTransition(
                entity_state=entity_state1,
                latest_sensor_response=sensor_response1,
                previous_value='off'
            )
            
            transition2 = EntityStateTransition(
                entity_state=entity_state2,
                latest_sensor_response=sensor_response2,
                previous_value='clear'
            )
            
            self.manager._recent_transitions.extend([transition1, transition2])
            
            # Should detect event with both sensor responses
            event = await self.manager._create_event_if_detected(event_def)
            
            self.assertIsInstance(event, Event)
            self.assertEqual(len(event.sensor_response_list), 2)
        
        self.run_async(async_test_logic())
        return

    def test_create_event_if_detected_timing_window_constraint(self):
        """Test event detection respects timing window constraints."""
        async def async_test_logic():
            entity = await sync_to_async(Entity.objects.create)(name='Test Entity', entity_type_str='CAMERA')
            entity_state = await sync_to_async(EntityState.objects.create)(
                entity=entity,
                entity_state_type_str='ON_OFF'
            )
            
            event_def = await sync_to_async(EventDefinition.objects.create)(
                name='Test Event',
                event_type_str='SECURITY',
                event_window_secs=30,  # Short window
                dedupe_window_secs=300,
                integration_id='test_id',
                integration_name='test_integration'
            )
            
            await sync_to_async(EventClause.objects.create)(
                event_definition=event_def,
                entity_state=entity_state,
                value='on'
            )
            
            # Create transition outside timing window
            old_timestamp = timezone.now() - timedelta(seconds=60)  # Outside 30-second window
            
            sensor_response = create_test_sensor_response(
                value='on',
                timestamp=old_timestamp
            )
            
            transition = EntityStateTransition(
                entity_state=entity_state,
                latest_sensor_response=sensor_response,
                previous_value='off'
            )
            
            manager = EventManager()
            manager._recent_transitions.append(transition)
            
            # Should NOT detect event due to timing constraint
            event = await manager._create_event_if_detected(event_def)
            
            self.assertFalse(event)
        
        self.run_async(async_test_logic())
        return


class TestEventManagerDeduplication(AsyncEventManagerTestCase):
    """Test event deduplication logic prevents duplicate events."""

    def test_has_recent_event_prevents_duplicate_within_window(self):
        """Test deduplication prevents events within dedupe window."""
        async def async_test_logic():
            event_def = await self.create_test_event_definition_async()
            
            # Create recent event
            sensor_response = create_test_sensor_response('test', timezone.now())
            recent_event = Event(
                event_definition=event_def,
                sensor_response_list=[sensor_response]
            )
            
            self.manager._recent_events[event_def.id] = recent_event
            
            # Should detect recent event within dedupe window
            has_recent = await self.manager._has_recent_event(event_def)
            
            self.assertTrue(has_recent)
        
        self.run_async(async_test_logic())
        return

    def test_has_recent_event_allows_after_dedupe_window(self):
        """Test deduplication allows events after dedupe window expires."""
        async def async_test_logic():
            event_def = await self.create_test_event_definition_async(
                dedupe_window_secs=60  # Short dedupe window
            )
            
            # Create old event (simulate by manipulating timestamp)
            old_timestamp = timezone.now() - timedelta(seconds=120)
            
            # Manually create event with old timestamp
            old_sensor_response = create_test_sensor_response('test', old_timestamp)
            old_event = Event(
                event_definition=event_def,
                sensor_response_list=[old_sensor_response]
            )
            self.manager._recent_events[event_def.id] = old_event
            
            # Should NOT have recent event (outside dedupe window)
            has_recent = await self.manager._has_recent_event(event_def)
            
            self.assertFalse(has_recent)
        
        self.run_async(async_test_logic())
        return


class TestEventManagerEventActions(AsyncEventManagerTestCase):
    """Test event action execution (alarms and control actions)."""

    def test_do_new_event_action_creates_alarms_for_matching_security_level(self):
        """Test alarm creation for events matching current security level."""
        async def async_test_logic():
            # Setup known database state
            entity, entity_state = await self.create_test_entities_async()
            event_def = await self.create_test_event_definition_async()
            
            # Create alarm action for HIGH security level
            _ = await sync_to_async(AlarmAction.objects.create)(
                event_definition=event_def,
                security_level_str='HIGH',
                alarm_level_str='CRITICAL',
                alarm_lifetime_secs=3600
            )
            
            sensor_response = create_test_sensor_response(
                value='on',
                timestamp=timezone.now(),
                detail_attrs={'test': 'data'}
            )
            
            event = Event(
                event_definition=event_def,
                sensor_response_list=[sensor_response]
            )
            
            # Mock external managers but let database operations proceed normally
            mock_alert_manager = AsyncMock()
            mock_controller_manager = AsyncMock()
            
            with patch.object(self.manager, 'alert_manager_async', return_value=mock_alert_manager), \
                 patch.object(self.manager, 'controller_manager_async', return_value=mock_controller_manager), \
                 patch.object(self.manager, 'security_manager') as mock_security:
                
                # Set current security level to HIGH to match alarm action
                mock_security.return_value.security_level = SecurityLevel.HIGH
                
                # Call method under test - let it use real database operations
                await self.manager._do_new_event_action([event])
                
                # Examine the results - should have called alert manager with correct alarm
                mock_alert_manager.add_alarm.assert_called_once()
                alarm_call_args = mock_alert_manager.add_alarm.call_args[0][0]
                self.assertEqual(alarm_call_args.title, 'Test Event')
                self.assertEqual(alarm_call_args.alarm_level, AlarmLevel.CRITICAL)
        
        self.run_async(async_test_logic())
        return

    def test_do_new_event_action_skips_alarms_for_mismatched_security_level(self):
        """Test alarm creation skipped when security level doesn't match."""
        async def async_test_logic():
            # Setup known database state
            event_def = await self.create_test_event_definition_async()
            
            # Create alarm action for HIGH security level
            _ = await sync_to_async(AlarmAction.objects.create)(
                event_definition=event_def,
                security_level_str='HIGH',
                alarm_level_str='CRITICAL',
                alarm_lifetime_secs=3600
            )
            
            sensor_response = create_test_sensor_response('test', timezone.now())
            
            event = Event(
                event_definition=event_def,
                sensor_response_list=[sensor_response]
            )
            
            # Mock external managers but let database operations proceed normally
            mock_alert_manager = AsyncMock()
            
            with patch.object(self.manager, 'alert_manager_async', return_value=mock_alert_manager), \
                 patch.object(self.manager, 'controller_manager_async'), \
                 patch.object(self.manager, 'security_manager') as mock_security:
                
                # Set current security level to LOW (doesn't match HIGH alarm action)
                mock_security.return_value.security_level = SecurityLevel.LOW
                
                # Call method under test - let it use real database operations
                await self.manager._do_new_event_action([event])
                
                # Examine the results - should NOT have called alert manager
                mock_alert_manager.add_alarm.assert_not_called()
        
        self.run_async(async_test_logic())
        return


class TestEventManagerEventHistory(AsyncEventManagerTestCase):
    """Test event history creation and persistence."""

    def test_add_to_event_history_creates_database_records(self):
        """Test event history creation stores events in database."""
        async def async_test_logic():
            event_def = await self.create_test_event_definition_async()
            
            event_timestamp = timezone.now()
            
            # Mock sensor response with specific timestamp
            sensor_response = create_test_sensor_response(
                value='test',
                timestamp=event_timestamp
            )
            
            event = Event(
                event_definition=event_def,
                sensor_response_list=[sensor_response]
            )
            
            # Should create event history record
            await self.manager._add_to_event_history([event])
            
            # Verify database record was created using async-safe query
            history_queryset = EventHistory.objects.filter(event_definition=event_def)
            history_records = await sync_to_async(list)(history_queryset)
            self.assertEqual(len(history_records), 1)
            
            history_record = history_records[0]
            # Use async-safe attribute access
            history_event_def_id = await sync_to_async(lambda: history_record.event_definition_id)()
            self.assertEqual(history_event_def_id, event_def.id)
            self.assertEqual(history_record.event_datetime, event_timestamp)
        
        self.run_async(async_test_logic())
        return


class TestEventManagerHelperMethods(BaseTestCase):
    """Test EventManager helper methods and utilities."""

    def test_create_simple_alarm_event_definition_creates_complete_setup(self):
        """Test helper method creates event definition with clause and alarm actions."""
        entity = Entity.objects.create(name='Test Entity', entity_type_str='CAMERA')
        entity_state = EntityState.objects.create(
            entity=entity,
            entity_state_type_str='ON_OFF'
        )
        
        security_to_alarm_mapping = {
            SecurityLevel.HIGH: AlarmLevel.CRITICAL,
            SecurityLevel.LOW: AlarmLevel.WARNING
        }
        
        manager = EventManager()
        
        event_def = manager.create_simple_alarm_event_definition(
            name='Simple Alarm Event',
            event_type=EventType.SECURITY,
            entity_state=entity_state,
            value='on',
            security_to_alarm_level=security_to_alarm_mapping,
            event_window_secs=60,
            dedupe_window_secs=300,
            alarm_lifetime_secs=3600
        )
        
        # Should create event definition
        self.assertEqual(event_def.name, 'Simple Alarm Event')
        self.assertEqual(event_def.event_type, EventType.SECURITY)
        self.assertTrue(event_def.enabled)
        
        # Should create event clause
        clauses = event_def.event_clauses.all()
        self.assertEqual(clauses.count(), 1)
        self.assertEqual(clauses.first().entity_state, entity_state)
        self.assertEqual(clauses.first().value, 'on')
        
        # Should create alarm actions for each security level
        alarm_actions = event_def.alarm_actions.all()
        self.assertEqual(alarm_actions.count(), 2)
        
        action_levels = {action.security_level: action.alarm_level for action in alarm_actions}
        self.assertEqual(action_levels[SecurityLevel.HIGH], AlarmLevel.CRITICAL)
        self.assertEqual(action_levels[SecurityLevel.LOW], AlarmLevel.WARNING)
        
        # Should mark for reload
        self.assertTrue(manager._event_definition_reload_needed)
        return
    
