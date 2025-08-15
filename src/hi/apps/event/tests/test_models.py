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
        
        # Should inherit integration key fields from IntegrationDataModel
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
