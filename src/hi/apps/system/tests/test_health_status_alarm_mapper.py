"""
Unit tests for HealthStatusAlarmMapper. Pure-policy tests — no Django DB,
no AlertManager interaction.
"""
import logging
from datetime import datetime

from django.test import SimpleTestCase

from hi.apps.alert.enums import AlarmLevel, AlarmSource
from hi.apps.security.enums import SecurityLevel
from hi.apps.system.enums import HealthStatusType
from hi.apps.system.health_status_alarm_mapper import HealthStatusAlarmMapper
from hi.apps.system.health_status_transition import HealthStatusTransition
from hi.apps.system.provider_info import ProviderInfo

logging.disable(logging.CRITICAL)


def _provider() -> ProviderInfo:
    return ProviderInfo(
        provider_id='test.provider',
        provider_name='Test Provider',
        description='',
    )


def _transition( prev: HealthStatusType, curr: HealthStatusType ) -> HealthStatusTransition:
    return HealthStatusTransition(
        provider_info=_provider(),
        previous_status=prev,
        current_status=curr,
        last_message='upstream unreachable',
        error_count=1,
        timestamp=datetime(2026, 4, 28, 12, 0, 0),
    )


class HealthStatusAlarmMapperTest(SimpleTestCase):

    def setUp(self):
        self.mapper = HealthStatusAlarmMapper()

    # --- should_create_alarm gating ---

    def test_unknown_on_either_side_suppresses_alarm(self):
        # Initialization edge: no settled baseline.
        for prev, curr in [
            (HealthStatusType.UNKNOWN, HealthStatusType.ERROR),
            (HealthStatusType.UNKNOWN, HealthStatusType.HEALTHY),
            (HealthStatusType.UNKNOWN, HealthStatusType.WARNING),
        ]:
            t = _transition(prev, curr)
            self.assertFalse(
                self.mapper.should_create_alarm(t),
                f'{prev} -> {curr} should be suppressed',
            )

    def test_disabled_on_either_side_suppresses_alarm(self):
        # Operator-initiated edge: entering or leaving DISABLED is an
        # explicit user action; the operator already knows.
        for prev, curr in [
            (HealthStatusType.HEALTHY, HealthStatusType.DISABLED),
            (HealthStatusType.ERROR, HealthStatusType.DISABLED),
            (HealthStatusType.DISABLED, HealthStatusType.HEALTHY),
            (HealthStatusType.DISABLED, HealthStatusType.ERROR),
        ]:
            t = _transition(prev, curr)
            self.assertFalse(
                self.mapper.should_create_alarm(t),
                f'{prev} -> {curr} should be suppressed',
            )

    def test_warning_target_alarms(self):
        # WARNING in monitor context means a real probe failure
        # (categorized at warning rather than error) — alarm-worthy.
        t = _transition(HealthStatusType.HEALTHY, HealthStatusType.WARNING)
        self.assertTrue(self.mapper.should_create_alarm(t))

    def test_healthy_to_error_alarms(self):
        t = _transition(HealthStatusType.HEALTHY, HealthStatusType.ERROR)
        self.assertTrue(self.mapper.should_create_alarm(t))

    def test_error_to_healthy_recovery_alarms(self):
        t = _transition(HealthStatusType.ERROR, HealthStatusType.HEALTHY)
        self.assertTrue(self.mapper.should_create_alarm(t))

    def test_warning_to_healthy_recovery_alarms(self):
        t = _transition(HealthStatusType.WARNING, HealthStatusType.HEALTHY)
        self.assertTrue(self.mapper.should_create_alarm(t))

    # --- get_alarm_level: natural levels and ceiling clamp ---

    def test_error_natural_level_is_critical(self):
        t = _transition(HealthStatusType.HEALTHY, HealthStatusType.ERROR)
        self.assertEqual(
            self.mapper.get_alarm_level(t, max_level=AlarmLevel.CRITICAL),
            AlarmLevel.CRITICAL,
        )

    def test_warning_natural_level_is_warning(self):
        t = _transition(HealthStatusType.HEALTHY, HealthStatusType.WARNING)
        self.assertEqual(
            self.mapper.get_alarm_level(t, max_level=AlarmLevel.CRITICAL),
            AlarmLevel.WARNING,
        )

    def test_recovery_natural_level_is_info(self):
        t = _transition(HealthStatusType.ERROR, HealthStatusType.HEALTHY)
        self.assertEqual(
            self.mapper.get_alarm_level(t, max_level=AlarmLevel.CRITICAL),
            AlarmLevel.INFO,
        )

    def test_error_clamped_down_when_provider_caps_at_info(self):
        t = _transition(HealthStatusType.HEALTHY, HealthStatusType.ERROR)
        self.assertEqual(
            self.mapper.get_alarm_level(t, max_level=AlarmLevel.INFO),
            AlarmLevel.INFO,
        )

    def test_error_clamped_down_when_provider_caps_at_warning(self):
        t = _transition(HealthStatusType.HEALTHY, HealthStatusType.ERROR)
        self.assertEqual(
            self.mapper.get_alarm_level(t, max_level=AlarmLevel.WARNING),
            AlarmLevel.WARNING,
        )

    def test_suppressed_edge_returns_no_level(self):
        for prev, curr in [
            (HealthStatusType.UNKNOWN, HealthStatusType.ERROR),
            (HealthStatusType.HEALTHY, HealthStatusType.DISABLED),
            (HealthStatusType.DISABLED, HealthStatusType.HEALTHY),
        ]:
            t = _transition(prev, curr)
            self.assertIsNone(
                self.mapper.get_alarm_level(t, max_level=AlarmLevel.CRITICAL),
                f'{prev} -> {curr} should produce no alarm level',
            )

    # --- alarm types: signature stability ---

    def test_error_and_recovery_have_distinct_types(self):
        t_err = _transition(HealthStatusType.HEALTHY, HealthStatusType.ERROR)
        t_rec = _transition(HealthStatusType.ERROR, HealthStatusType.HEALTHY)
        self.assertNotEqual(
            self.mapper.get_alarm_type(t_err),
            self.mapper.get_alarm_type(t_rec),
        )
        self.assertIn('error', self.mapper.get_alarm_type(t_err))
        self.assertIn('recovered', self.mapper.get_alarm_type(t_rec))
        # Provider id is part of the type so different providers don't
        # collapse into the same alarm.
        self.assertIn('test.provider', self.mapper.get_alarm_type(t_err))

    # --- create_alarm end-to-end ---

    def test_create_alarm_full_shape_for_error(self):
        t = _transition(HealthStatusType.HEALTHY, HealthStatusType.ERROR)
        alarm = self.mapper.create_alarm(t, max_level=AlarmLevel.CRITICAL)
        self.assertIsNotNone(alarm)
        self.assertEqual(alarm.alarm_source, AlarmSource.HEALTH_STATUS)
        self.assertEqual(alarm.alarm_level, AlarmLevel.CRITICAL)
        self.assertEqual(alarm.security_level, SecurityLevel.OFF)
        self.assertIn('Test Provider', alarm.title)
        self.assertEqual(len(alarm.sensor_response_list), 1)
        sr = alarm.sensor_response_list[0]
        self.assertEqual(sr.detail_attrs['Status'], HealthStatusType.ERROR.label)
        self.assertEqual(sr.detail_attrs['Message'], 'upstream unreachable')

    def test_create_alarm_full_shape_for_recovery(self):
        t = _transition(HealthStatusType.ERROR, HealthStatusType.HEALTHY)
        alarm = self.mapper.create_alarm(t, max_level=AlarmLevel.CRITICAL)
        self.assertIsNotNone(alarm)
        self.assertEqual(alarm.alarm_level, AlarmLevel.INFO)
        self.assertIn('recovered', alarm.title.lower())

    def test_create_alarm_returns_none_for_suppressed_edges(self):
        for prev, curr in [
            (HealthStatusType.UNKNOWN, HealthStatusType.ERROR),
            (HealthStatusType.HEALTHY, HealthStatusType.DISABLED),
            (HealthStatusType.DISABLED, HealthStatusType.HEALTHY),
        ]:
            t = _transition(prev, curr)
            self.assertIsNone(
                self.mapper.create_alarm(t, max_level=AlarmLevel.CRITICAL),
                f'{prev} -> {curr} should produce no alarm',
            )

    def test_error_and_recovery_share_lifetime(self):
        # Recovery must not expire before the error it's resolving —
        # otherwise the user sees a bare error alert with no recovery
        # context for the rest of the error's lifetime, suggesting the
        # integration is still broken.
        t_err = _transition(HealthStatusType.HEALTHY, HealthStatusType.ERROR)
        t_rec = _transition(HealthStatusType.ERROR, HealthStatusType.HEALTHY)
        self.assertEqual(
            self.mapper.get_alarm_lifetime_secs(t_err),
            self.mapper.get_alarm_lifetime_secs(t_rec),
        )
