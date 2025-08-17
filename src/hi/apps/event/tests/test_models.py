import logging

from hi.apps.event.models import EventDefinition, EventClause, AlarmAction, ControlAction, EventHistory
from hi.apps.event.enums import EventType
from hi.apps.alert.enums import AlarmLevel
from hi.apps.security.enums import SecurityLevel
from hi.apps.entity.models import Entity, EntityState
from hi.apps.control.models import Controller
from hi.tests.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestEventDefinition(BaseTestCase):

    def test_event_definition_integration_key_inheritance(self):
        """Test EventDefinition integration key inheritance - critical for integration system."""
        event_def = EventDefinition.objects.create(
            name='Test Event',
            event_type_str='SECURITY',
            event_window_secs=60,
            dedupe_window_secs=300,
            integration_id='test_id',
            integration_name='test_integration'
        )
        
        # Should inherit integration key fields from IntegrationDetailsModel
        self.assertEqual(event_def.integration_id, 'test_id')
        self.assertEqual(event_def.integration_name, 'test_integration')
        return

    def test_event_definition_event_type_property_conversion(self):
        """Test event_type property enum conversion - custom business logic."""
        event_def = EventDefinition.objects.create(
            name='Test Event',
            event_type_str='AUTOMATION',
            event_window_secs=60,
            dedupe_window_secs=300,
            integration_id='test_id',
            integration_name='test_integration'
        )
        
        # Test getter converts string to enum
        self.assertEqual(event_def.event_type, EventType.AUTOMATION)
        
        # Test setter converts enum to string
        event_def.event_type = EventType.MAINTENANCE
        self.assertEqual(event_def.event_type_str, 'maintenance')
        return

    def test_event_definition_timing_constraints(self):
        """Test event timing window constraints - critical for event logic."""
        event_def = EventDefinition.objects.create(
            name='Test Event',
            event_type_str='SECURITY',
            event_window_secs=120,  # 2 minutes for all clauses to be satisfied
            dedupe_window_secs=600,  # 10 minutes before next event can be generated
            integration_id='test_id',
            integration_name='test_integration'
        )
        
        # Should store timing constraints correctly
        self.assertEqual(event_def.event_window_secs, 120)
        self.assertEqual(event_def.dedupe_window_secs, 600)
        
        # Should allow reasonable timing values
        self.assertGreater(event_def.dedupe_window_secs, event_def.event_window_secs)
        return

    def test_event_definition_enabled_default(self):
        """Test EventDefinition enabled default - important for system behavior."""
        event_def = EventDefinition.objects.create(
            name='Test Event',
            event_type_str='SECURITY',
            event_window_secs=60,
            dedupe_window_secs=300,
            integration_id='test_id',
            integration_name='test_integration'
        )
        
        # Should default to enabled
        self.assertTrue(event_def.enabled)
        return


class TestEventClause(BaseTestCase):

    def test_event_clause_cascade_deletion_from_event_definition(self):
        """Test cascade deletion from event definition - critical for data integrity."""
        event_def = EventDefinition.objects.create(
            name='Test Event',
            event_type_str='SECURITY',
            event_window_secs=60,
            dedupe_window_secs=300,
            integration_id='test_id',
            integration_name='test_integration'
        )
        
        entity = Entity.objects.create(
            name='Test Entity',
            entity_type_str='CAMERA'
        )
        entity_state = EntityState.objects.create(
            entity=entity,
            entity_state_type_str='ON_OFF'
        )
        
        event_clause = EventClause.objects.create(
            event_definition=event_def,
            entity_state=entity_state,
            value='on'
        )
        
        clause_id = event_clause.id
        
        # Delete event definition should cascade to clauses
        event_def.delete()
        
        self.assertFalse(EventClause.objects.filter(id=clause_id).exists())
        return

    def test_event_clause_cascade_deletion_from_entity_state(self):
        """Test cascade deletion from entity state - critical for data integrity."""
        event_def = EventDefinition.objects.create(
            name='Test Event',
            event_type_str='SECURITY',
            event_window_secs=60,
            dedupe_window_secs=300,
            integration_id='test_id',
            integration_name='test_integration'
        )
        
        entity = Entity.objects.create(
            name='Test Entity',
            entity_type_str='CAMERA'
        )
        entity_state = EntityState.objects.create(
            entity=entity,
            entity_state_type_str='ON_OFF'
        )
        
        event_clause = EventClause.objects.create(
            event_definition=event_def,
            entity_state=entity_state,
            value='on'
        )
        
        clause_id = event_clause.id
        
        # Delete entity state should cascade to clauses
        entity_state.delete()
        
        self.assertFalse(EventClause.objects.filter(id=clause_id).exists())
        return


class TestAlarmAction(BaseTestCase):

    def test_alarm_action_enum_property_conversions(self):
        """Test AlarmAction enum property conversions - custom business logic."""
        event_def = EventDefinition.objects.create(
            name='Test Event',
            event_type_str='SECURITY',
            event_window_secs=60,
            dedupe_window_secs=300,
            integration_id='test_id',
            integration_name='test_integration'
        )
        
        alarm_action = AlarmAction.objects.create(
            event_definition=event_def,
            security_level_str='HIGH',
            alarm_level_str='CRITICAL',
            alarm_lifetime_secs=3600
        )
        
        # Test getter converts string to enum
        self.assertEqual(alarm_action.security_level, SecurityLevel.HIGH)
        self.assertEqual(alarm_action.alarm_level, AlarmLevel.CRITICAL)
        
        # Test setter converts enum to string
        alarm_action.security_level = SecurityLevel.LOW
        alarm_action.alarm_level = AlarmLevel.WARNING
        self.assertEqual(alarm_action.security_level_str, 'low')
        self.assertEqual(alarm_action.alarm_level_str, 'warning')
        return

    def test_alarm_action_lifetime_configuration(self):
        """Test alarm lifetime configuration - critical for alarm management."""
        event_def = EventDefinition.objects.create(
            name='Test Event',
            event_type_str='SECURITY',
            event_window_secs=60,
            dedupe_window_secs=300,
            integration_id='test_id',
            integration_name='test_integration'
        )
        
        # Test zero lifetime (manual acknowledgment only)
        manual_alarm = AlarmAction.objects.create(
            event_definition=event_def,
            security_level_str='HIGH',
            alarm_level_str='CRITICAL',
            alarm_lifetime_secs=0
        )
        self.assertEqual(manual_alarm.alarm_lifetime_secs, 0)
        
        # Test timed lifetime
        timed_alarm = AlarmAction.objects.create(
            event_definition=event_def,
            security_level_str='MEDIUM',
            alarm_level_str='WARNING',
            alarm_lifetime_secs=1800  # 30 minutes
        )
        self.assertEqual(timed_alarm.alarm_lifetime_secs, 1800)
        return

    def test_alarm_action_cascade_deletion_from_event_definition(self):
        """Test cascade deletion from event definition - critical for data integrity."""
        event_def = EventDefinition.objects.create(
            name='Test Event',
            event_type_str='SECURITY',
            event_window_secs=60,
            dedupe_window_secs=300,
            integration_id='test_id',
            integration_name='test_integration'
        )
        
        alarm_action = AlarmAction.objects.create(
            event_definition=event_def,
            security_level_str='HIGH',
            alarm_level_str='CRITICAL',
            alarm_lifetime_secs=3600
        )
        
        action_id = alarm_action.id
        
        # Delete event definition should cascade to alarm actions
        event_def.delete()
        
        self.assertFalse(AlarmAction.objects.filter(id=action_id).exists())
        return


class TestControlAction(BaseTestCase):

    def test_control_action_cascade_deletion_from_event_definition(self):
        """Test cascade deletion from event definition - critical for data integrity."""
        event_def = EventDefinition.objects.create(
            name='Test Event',
            event_type_str='AUTOMATION',
            event_window_secs=60,
            dedupe_window_secs=300,
            integration_id='test_id',
            integration_name='test_integration'
        )
        
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
            integration_id='ctrl_id',
            integration_name='ctrl_integration'
        )
        
        control_action = ControlAction.objects.create(
            event_definition=event_def,
            controller=controller,
            value='on'
        )
        
        action_id = control_action.id
        
        # Delete event definition should cascade to control actions
        event_def.delete()
        
        self.assertFalse(ControlAction.objects.filter(id=action_id).exists())
        return

    def test_control_action_cascade_deletion_from_controller(self):
        """Test cascade deletion from controller - critical for data integrity."""
        event_def = EventDefinition.objects.create(
            name='Test Event',
            event_type_str='AUTOMATION',
            event_window_secs=60,
            dedupe_window_secs=300,
            integration_id='test_id',
            integration_name='test_integration'
        )
        
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
            integration_id='ctrl_id',
            integration_name='ctrl_integration'
        )
        
        control_action = ControlAction.objects.create(
            event_definition=event_def,
            controller=controller,
            value='on'
        )
        
        action_id = control_action.id
        
        # Delete controller should cascade to control actions
        controller.delete()
        
        self.assertFalse(ControlAction.objects.filter(id=action_id).exists())
        return


class TestEventHistory(BaseTestCase):

    def test_event_history_ordering_by_event_datetime(self):
        """Test EventHistory ordering - critical for history display."""
        event_def = EventDefinition.objects.create(
            name='Test Event',
            event_type_str='SECURITY',
            event_window_secs=60,
            dedupe_window_secs=300,
            integration_id='test_id',
            integration_name='test_integration'
        )
        
        from django.utils import timezone
        
        # Create history entries with different timestamps
        history1 = EventHistory.objects.create(
            event_definition=event_def,
            event_datetime=timezone.now() - timezone.timedelta(hours=2)
        )
        history2 = EventHistory.objects.create(
            event_definition=event_def,
            event_datetime=timezone.now() - timezone.timedelta(hours=1)
        )
        history3 = EventHistory.objects.create(
            event_definition=event_def,
            event_datetime=timezone.now()
        )
        
        # Should be ordered by newest first
        history_list = list(EventHistory.objects.filter(event_definition=event_def))
        self.assertEqual(history_list[0], history3)  # Most recent
        self.assertEqual(history_list[1], history2)
        self.assertEqual(history_list[2], history1)  # Oldest
        return

    def test_event_history_datetime_indexing(self):
        """Test event_datetime field indexing - critical for query performance."""
        event_def = EventDefinition.objects.create(
            name='Test Event',
            event_type_str='SECURITY',
            event_window_secs=60,
            dedupe_window_secs=300,
            integration_id='test_id',
            integration_name='test_integration'
        )
        
        from django.utils import timezone
        
        history = EventHistory.objects.create(
            event_definition=event_def,
            event_datetime=timezone.now()
        )
        
        # Test that datetime queries work efficiently
        # (The actual index performance isn't testable in unit tests,
        # but we can verify the field is accessible and queryable)
        recent_history = EventHistory.objects.filter(
            event_datetime__gte=history.event_datetime
        )
        self.assertIn(history, recent_history)
        return

    def test_event_history_cascade_deletion_from_event_definition(self):
        """Test cascade deletion from event definition - critical for data integrity."""
        event_def = EventDefinition.objects.create(
            name='Test Event',
            event_type_str='SECURITY',
            event_window_secs=60,
            dedupe_window_secs=300,
            integration_id='test_id',
            integration_name='test_integration'
        )
        
        from django.utils import timezone
        
        history = EventHistory.objects.create(
            event_definition=event_def,
            event_datetime=timezone.now()
        )
        
        history_id = history.id
        
        # Delete event definition should cascade to history
        event_def.delete()
        
        self.assertFalse(EventHistory.objects.filter(id=history_id).exists())
        return


class TestEventDefinitionAdvanced(BaseTestCase):
    """Advanced EventDefinition tests for edge cases and business logic."""

    def test_event_definition_timing_window_constraints_validation(self):
        """Test invalid timing window combinations and edge cases."""
        # Test zero event window (should be valid for immediate events)
        event_def = EventDefinition.objects.create(
            name='Immediate Event',
            event_type_str='AUTOMATION',
            event_window_secs=0,
            dedupe_window_secs=60,
            integration_id='test_id',
            integration_name='test_integration'
        )
        self.assertEqual(event_def.event_window_secs, 0)
        
        # Test zero dedupe window (should be valid for non-deduplicated events)
        event_def2 = EventDefinition.objects.create(
            name='No Dedupe Event',
            event_type_str='INFORMATION',
            event_window_secs=30,
            dedupe_window_secs=0,
            integration_id='test_id2',
            integration_name='test_integration2'
        )
        self.assertEqual(event_def2.dedupe_window_secs, 0)
        return

    def test_event_definition_enum_conversion_edge_cases(self):
        """Test enum conversion with invalid and edge case values."""
        event_def = EventDefinition.objects.create(
            name='Test Event',
            event_type_str='INVALID_TYPE',  # Invalid enum value
            event_window_secs=60,
            dedupe_window_secs=300,
            integration_id='test_id',
            integration_name='test_integration'
        )
        
        # Should handle invalid enum gracefully
        event_type = event_def.event_type
        self.assertEqual(event_type, EventType.SECURITY)  # from_name_safe returns default for invalid
        return

    def test_event_definition_multiple_clause_relationships(self):
        """Test EventDefinition with multiple clauses - critical for complex events."""
        entity1 = Entity.objects.create(name='Entity 1', entity_type_str='CAMERA')
        entity_state1 = EntityState.objects.create(
            entity=entity1,
            entity_state_type_str='ON_OFF'
        )
        
        entity2 = Entity.objects.create(name='Entity 2', entity_type_str='SENSOR')
        entity_state2 = EntityState.objects.create(
            entity=entity2,
            entity_state_type_str='DETECTED'
        )
        
        event_def = EventDefinition.objects.create(
            name='Multi-Clause Event',
            event_type_str='SECURITY',
            event_window_secs=120,
            dedupe_window_secs=600,
            integration_id='test_id',
            integration_name='test_integration'
        )
        
        # Create multiple clauses
        clause1 = EventClause.objects.create(
            event_definition=event_def,
            entity_state=entity_state1,
            value='on'
        )
        clause2 = EventClause.objects.create(
            event_definition=event_def,
            entity_state=entity_state2,
            value='detected'
        )
        
        # Should have multiple clauses accessible via relationship
        clauses = event_def.event_clauses.all()
        self.assertEqual(clauses.count(), 2)
        self.assertIn(clause1, clauses)
        self.assertIn(clause2, clauses)
        return

    def test_event_definition_multiple_action_types(self):
        """Test EventDefinition with both alarm and control actions."""
        entity = Entity.objects.create(name='Test Entity', entity_type_str='CAMERA')
        entity_state = EntityState.objects.create(
            entity=entity,
            entity_state_type_str='ON_OFF'
        )
        
        controller = Controller.objects.create(
            name='Test Controller',
            entity_state=entity_state,
            controller_type_str='DEFAULT',
            integration_id='ctrl_id',
            integration_name='ctrl_integration'
        )
        
        event_def = EventDefinition.objects.create(
            name='Mixed Actions Event',
            event_type_str='AUTOMATION',
            event_window_secs=60,
            dedupe_window_secs=300,
            integration_id='test_id',
            integration_name='test_integration'
        )
        
        # Create alarm action
        alarm_action = AlarmAction.objects.create(
            event_definition=event_def,
            security_level_str='HIGH',
            alarm_level_str='WARNING',
            alarm_lifetime_secs=1800
        )
        
        # Create control action
        control_action = ControlAction.objects.create(
            event_definition=event_def,
            controller=controller,
            value='on'
        )
        
        # Should have both action types
        self.assertEqual(event_def.alarm_actions.count(), 1)
        self.assertEqual(event_def.control_actions.count(), 1)
        self.assertEqual(event_def.alarm_actions.first(), alarm_action)
        self.assertEqual(event_def.control_actions.first(), control_action)
        return


class TestAlarmActionAdvanced(BaseTestCase):
    """Advanced AlarmAction tests for business logic and edge cases."""

    def test_alarm_action_enum_conversion_invalid_values(self):
        """Test enum conversion with invalid security and alarm levels."""
        event_def = EventDefinition.objects.create(
            name='Test Event',
            event_type_str='SECURITY',
            event_window_secs=60,
            dedupe_window_secs=300,
            integration_id='test_id',
            integration_name='test_integration'
        )
        
        # Create alarm action with invalid enum values
        alarm_action = AlarmAction.objects.create(
            event_definition=event_def,
            security_level_str='INVALID_SECURITY',
            alarm_level_str='INVALID_ALARM',
            alarm_lifetime_secs=3600
        )
        
        # Should handle invalid enums gracefully  
        self.assertEqual(alarm_action.security_level, SecurityLevel.HIGH)  # from_name_safe returns default (first enum)
        self.assertEqual(alarm_action.alarm_level, AlarmLevel.NONE)  # from_name_safe returns default (first enum)
        return

    def test_alarm_action_zero_lifetime_manual_acknowledgment(self):
        """Test alarm action with zero lifetime for manual acknowledgment only."""
        event_def = EventDefinition.objects.create(
            name='Manual Alarm Event',
            event_type_str='SECURITY',
            event_window_secs=60,
            dedupe_window_secs=300,
            integration_id='test_id',
            integration_name='test_integration'
        )
        
        alarm_action = AlarmAction.objects.create(
            event_definition=event_def,
            security_level_str='CRITICAL',
            alarm_level_str='CRITICAL',
            alarm_lifetime_secs=0  # Manual acknowledgment only
        )
        
        # Zero lifetime should indicate manual acknowledgment requirement
        self.assertEqual(alarm_action.alarm_lifetime_secs, 0)
        return

    def test_alarm_action_multiple_per_event_definition(self):
        """Test multiple alarm actions for different security levels."""
        event_def = EventDefinition.objects.create(
            name='Multi-Level Alarm Event',
            event_type_str='SECURITY',
            event_window_secs=60,
            dedupe_window_secs=300,
            integration_id='test_id',
            integration_name='test_integration'
        )
        
        # Create alarm actions for different security levels
        _ = AlarmAction.objects.create(
            event_definition=event_def,
            security_level_str='HIGH',
            alarm_level_str='CRITICAL',
            alarm_lifetime_secs=7200
        )
        
        _ = AlarmAction.objects.create(
            event_definition=event_def,
            security_level_str='LOW',
            alarm_level_str='INFO',
            alarm_lifetime_secs=1800
        )
        
        # Should have multiple alarm actions with different configurations
        alarm_actions = event_def.alarm_actions.all()
        self.assertEqual(alarm_actions.count(), 2)
        
        security_levels = [action.security_level for action in alarm_actions]
        self.assertIn(SecurityLevel.HIGH, security_levels)
        self.assertIn(SecurityLevel.LOW, security_levels)
        return


class TestEventHistoryAdvanced(BaseTestCase):
    """Advanced EventHistory tests for performance and data integrity."""

    def test_event_history_bulk_insertion_performance(self):
        """Test bulk creation of event history records for performance."""
        event_def = EventDefinition.objects.create(
            name='High Volume Event',
            event_type_str='INFORMATION',
            event_window_secs=60,
            dedupe_window_secs=300,
            integration_id='test_id',
            integration_name='test_integration'
        )
        
        from django.utils import timezone
        
        # Create multiple history records
        history_records = []
        base_time = timezone.now()
        
        for i in range(100):
            history_records.append(EventHistory(
                event_definition=event_def,
                event_datetime=base_time - timezone.timedelta(seconds=i)
            ))
        
        # Bulk create should handle large numbers efficiently
        EventHistory.objects.bulk_create(history_records)
        
        # Verify all records were created
        created_count = EventHistory.objects.filter(event_definition=event_def).count()
        self.assertEqual(created_count, 100)
        return

    def test_event_history_datetime_range_queries(self):
        """Test datetime range queries use database indexing efficiently."""
        event_def = EventDefinition.objects.create(
            name='Time Range Event',
            event_type_str='AUTOMATION',
            event_window_secs=60,
            dedupe_window_secs=300,
            integration_id='test_id',
            integration_name='test_integration'
        )
        
        from django.utils import timezone
        
        # Create history records across different time ranges
        now = timezone.now()
        
        # Recent (last hour)
        recent_history = EventHistory.objects.create(
            event_definition=event_def,
            event_datetime=now - timezone.timedelta(minutes=30)
        )
        
        # Old (last week)
        old_history = EventHistory.objects.create(
            event_definition=event_def,
            event_datetime=now - timezone.timedelta(days=7)
        )
        
        # Test range queries that should use datetime index
        last_day = EventHistory.objects.filter(
            event_datetime__gte=now - timezone.timedelta(days=1)
        )
        self.assertIn(recent_history, last_day)
        self.assertNotIn(old_history, last_day)
        
        last_week = EventHistory.objects.filter(
            event_datetime__gte=now - timezone.timedelta(days=8)
        )
        self.assertIn(recent_history, last_week)
        self.assertIn(old_history, last_week)
        return

    def test_event_history_ordering_with_identical_timestamps(self):
        """Test ordering behavior with identical event timestamps."""
        event_def = EventDefinition.objects.create(
            name='Simultaneous Events',
            event_type_str='SECURITY',
            event_window_secs=60,
            dedupe_window_secs=300,
            integration_id='test_id',
            integration_name='test_integration'
        )
        
        from django.utils import timezone
        
        # Create multiple events with same timestamp
        same_timestamp = timezone.now()
        
        _ = EventHistory.objects.create(
            event_definition=event_def,
            event_datetime=same_timestamp
        )
        _ = EventHistory.objects.create(
            event_definition=event_def,
            event_datetime=same_timestamp
        )
        _ = EventHistory.objects.create(
            event_definition=event_def,
            event_datetime=same_timestamp
        )
        
        # Should handle identical timestamps gracefully
        # Ordering should be consistent (by ID when timestamps are equal)
        all_history = list(EventHistory.objects.filter(event_definition=event_def))
        self.assertEqual(len(all_history), 3)
        
        # All should have the same timestamp
        timestamps = [h.event_datetime for h in all_history]
        self.assertTrue(all(t == same_timestamp for t in timestamps))
        return
