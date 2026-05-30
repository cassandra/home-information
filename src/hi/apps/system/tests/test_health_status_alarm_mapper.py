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

    def test_recovery_transitions_do_not_create_alarm(self):
        """Recovery transitions are handled by the clear-target path
        (``get_recovery_target_signature`` + ``AlertManager.clear_alarms``),
        not the create-alarm path. ``should_create_alarm`` must return
        False so the caller doesn't double-handle the transition."""
        for prev in (HealthStatusType.ERROR, HealthStatusType.WARNING):
            t = _transition(prev, HealthStatusType.HEALTHY)
            self.assertFalse(
                self.mapper.should_create_alarm(t),
                f'recovery from {prev} should NOT create an alarm',
            )

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

    def test_recovery_returns_no_alarm_level(self):
        """Recovery transitions don't fire alarms (cleared via
        ``clear_alarms`` instead); their ``get_alarm_level`` returns
        ``None``."""
        t = _transition(HealthStatusType.ERROR, HealthStatusType.HEALTHY)
        self.assertIsNone(
            self.mapper.get_alarm_level(t, max_level=AlarmLevel.CRITICAL)
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

    def test_error_alarm_type_includes_provider_id(self):
        """The error alarm type embeds the provider id so signatures
        from distinct providers don't collapse together. ``get_alarm_type``
        is only called from ``create_alarm`` (degrade path); recovery
        is handled by ``get_recovery_target_signature``."""
        t_err = _transition(HealthStatusType.HEALTHY, HealthStatusType.ERROR)
        alarm_type = self.mapper.get_alarm_type(t_err)
        self.assertIn('error', alarm_type)
        self.assertIn('test.provider', alarm_type)

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

    def test_create_alarm_returns_none_for_recovery(self):
        """Recovery transitions no longer fire their own alarm. The
        caller invokes ``get_recovery_target_signature`` and
        ``AlertManager.clear_alarms`` instead."""
        for prev in (HealthStatusType.ERROR, HealthStatusType.WARNING):
            t = _transition(prev, HealthStatusType.HEALTHY)
            self.assertIsNone(
                self.mapper.create_alarm(t, max_level=AlarmLevel.CRITICAL),
                f'recovery from {prev} should produce no alarm',
            )

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

    # --- get_recovery_target_signature ---

    def test_recovery_target_signature_error_to_healthy(self):
        """Recovery from ERROR clears the CRITICAL-level error alarm
        the prior degrade transition would have queued."""
        t = _transition(HealthStatusType.ERROR, HealthStatusType.HEALTHY)
        signature = self.mapper.get_recovery_target_signature(
            transition=t, max_level=AlarmLevel.CRITICAL,
        )
        self.assertIsNotNone(signature)
        self.assertEqual(signature.alarm_source, AlarmSource.HEALTH_STATUS)
        self.assertIn('test.provider', signature.alarm_type)
        self.assertIn('error', signature.alarm_type)
        self.assertEqual(signature.alarm_level, AlarmLevel.CRITICAL)

    def test_recovery_target_signature_warning_to_healthy(self):
        """Recovery from WARNING clears the WARNING-level alarm. Each
        bad-state level produces its own signature so the clear must
        target the correct one."""
        t = _transition(HealthStatusType.WARNING, HealthStatusType.HEALTHY)
        signature = self.mapper.get_recovery_target_signature(
            transition=t, max_level=AlarmLevel.CRITICAL,
        )
        self.assertIsNotNone(signature)
        self.assertEqual(signature.alarm_level, AlarmLevel.WARNING)

    def test_recovery_target_signature_uses_clamped_level(self):
        """The clear-target's level must reflect the SAME ceiling-clamp
        applied when the original degrade alarm was queued, otherwise
        the produced signature won't match what's actually in the
        queue."""
        t = _transition(HealthStatusType.ERROR, HealthStatusType.HEALTHY)
        signature = self.mapper.get_recovery_target_signature(
            transition=t, max_level=AlarmLevel.INFO,
        )
        self.assertIsNotNone(signature)
        # ERROR would naturally fire CRITICAL but is clamped down to
        # the provider's INFO ceiling. Recovery target must apply the
        # same clamp so the signatures match.
        self.assertEqual(signature.alarm_level, AlarmLevel.INFO)

    def test_recovery_target_signature_none_for_non_recovery(self):
        """Forward (degrade) transitions have nothing to clear."""
        for prev, curr in [
            (HealthStatusType.HEALTHY, HealthStatusType.ERROR),
            (HealthStatusType.HEALTHY, HealthStatusType.WARNING),
            (HealthStatusType.WARNING, HealthStatusType.ERROR),
        ]:
            t = _transition(prev, curr)
            self.assertIsNone(
                self.mapper.get_recovery_target_signature(
                    transition=t, max_level=AlarmLevel.CRITICAL,
                ),
                f'{prev} -> {curr} is not a recovery; signature should be None',
            )

    def test_recovery_target_signature_none_for_suppressed_previous(self):
        """A recovery from a suppressed state (UNKNOWN/DISABLED) had no
        prior alarm queued, so there's nothing to clear."""
        for prev in (HealthStatusType.UNKNOWN, HealthStatusType.DISABLED):
            t = _transition(prev, HealthStatusType.HEALTHY)
            self.assertIsNone(
                self.mapper.get_recovery_target_signature(
                    transition=t, max_level=AlarmLevel.CRITICAL,
                ),
                f'recovery from suppressed {prev} should produce no signature',
            )

    def test_recovery_target_signature_matches_prior_degrade_signature(self):
        """End-to-end contract: the signature a recovery produces equals
        the signature ``create_alarm`` on the prior degrade transition
        would have queued. If these ever drift, ``clear_alarms`` would
        silently miss its target."""
        max_level = AlarmLevel.CRITICAL
        t_degrade = _transition(HealthStatusType.HEALTHY, HealthStatusType.ERROR)
        degrade_alarm = self.mapper.create_alarm(t_degrade, max_level=max_level)
        self.assertIsNotNone(degrade_alarm)

        t_recover = _transition(HealthStatusType.ERROR, HealthStatusType.HEALTHY)
        signature = self.mapper.get_recovery_target_signature(
            transition=t_recover, max_level=max_level,
        )
        self.assertIsNotNone(signature)
        self.assertEqual(signature, degrade_alarm.signature)
