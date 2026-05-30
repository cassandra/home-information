"""
Tests for the transition-dispatch behavior added to HealthStatusProvider.

We don't go through AlertManager — we patch _dispatch_transition_alarm to
record invocations and verify it's only called on real transitions and
only with the right inputs.
"""
import logging
from unittest.mock import patch

from django.test import SimpleTestCase

from hi.apps.alert.enums import AlarmLevel
from hi.apps.system.enums import HealthStatusType
from hi.apps.system.health_status_provider import HealthStatusProvider
from hi.apps.system.provider_info import ProviderInfo

logging.disable(logging.CRITICAL)


class _OptedOutProvider(HealthStatusProvider):
    @classmethod
    def get_provider_info(cls):
        return ProviderInfo(
            provider_id='test.opted_out',
            provider_name='Opted Out',
            description='',
        )


class _OptedInProvider(HealthStatusProvider):
    @classmethod
    def get_provider_info(cls):
        return ProviderInfo(
            provider_id='test.opted_in',
            provider_name='Opted In',
            description='',
        )

    def alarm_ceiling(self):
        return AlarmLevel.CRITICAL


class HealthStatusProviderTransitionDispatchTest(SimpleTestCase):

    def test_no_dispatch_on_no_op_status_set(self):
        """Setting the same status repeatedly must not fire transitions."""
        provider = _OptedInProvider()
        # Force a known starting status (UNKNOWN by default).
        provider.update_health_status(HealthStatusType.HEALTHY, 'init')

        with patch.object(_OptedInProvider, '_dispatch_transition_alarm') as mock_dispatch:
            provider.update_health_status(HealthStatusType.HEALTHY, 'still healthy')
            mock_dispatch.assert_not_called()

    def test_dispatch_on_real_transition(self):
        provider = _OptedInProvider()
        provider.update_health_status(HealthStatusType.HEALTHY, 'init')

        with patch.object(_OptedInProvider, '_dispatch_transition_alarm') as mock_dispatch:
            provider.update_health_status(HealthStatusType.ERROR, 'broken')
            mock_dispatch.assert_called_once()
            kwargs = mock_dispatch.call_args.kwargs
            self.assertEqual(kwargs['previous_status'], HealthStatusType.HEALTHY)
            self.assertEqual(kwargs['current_status'], HealthStatusType.ERROR)
            self.assertEqual(kwargs['last_message'], 'broken')

    def test_opted_out_provider_skips_alarm_path(self):
        """alarm_ceiling() returning None must short-circuit dispatch."""
        provider = _OptedOutProvider()
        provider.update_health_status(HealthStatusType.HEALTHY, 'init')

        with patch('hi.apps.alert.alert_manager.AlertManager') as mock_alert_manager:
            provider.update_health_status(HealthStatusType.ERROR, 'broken')
            # AlertManager must never be touched for opted-out providers.
            mock_alert_manager.assert_not_called()

    def test_dispatch_failure_does_not_break_health_update(self):
        """A misbehaving alarm path must not break health bookkeeping."""
        provider = _OptedInProvider()
        provider.update_health_status(HealthStatusType.HEALTHY, 'init')

        with patch.object(
            _OptedInProvider, '_dispatch_transition_alarm',
            side_effect=RuntimeError('alarm path exploded'),
        ):
            # Health bookkeeping must succeed regardless of alarm-path failure.
            try:
                provider.update_health_status(HealthStatusType.ERROR, 'broken')
            except RuntimeError:
                self.fail('update_health_status leaked an alarm-path exception')

        # Status was updated despite the alarm exception.
        self.assertEqual(provider.health_status.status, HealthStatusType.ERROR)


class HealthStatusProviderRecoveryDispatchTest(SimpleTestCase):
    """Recovery transitions clear the prior bad-state alert via
    ``AlertManager.clear_alarms`` instead of producing a second
    "recovered" alarm. End result: the operator returns to a clean
    dashboard when the system has recovered while they were away.
    """

    def test_degrade_then_recover_leaves_no_alerts(self):
        """Round-trip: HEALTHY -> ERROR -> HEALTHY. After the recovery
        dispatch fires, the only effect on AlertManager is one
        ``upsert_alarm`` (for the degrade) followed by one
        ``clear_alarms`` (for the recovery) -- no second alert is
        added."""
        provider = _OptedInProvider()
        provider.update_health_status(HealthStatusType.HEALTHY, 'init')

        with patch('hi.apps.alert.alert_manager.AlertManager'
                   ) as mock_alert_manager_cls:
            mock_alert_manager = mock_alert_manager_cls.return_value
            provider.update_health_status(HealthStatusType.ERROR, 'broken')
            mock_alert_manager.upsert_alarm.assert_called_once()
            mock_alert_manager.clear_alarms.assert_not_called()

            mock_alert_manager.reset_mock()
            mock_alert_manager_cls.reset_mock()
            provider.update_health_status(HealthStatusType.HEALTHY, 'recovered')

            # Recovery path takes clear_alarms, NOT upsert_alarm.
            mock_alert_manager.upsert_alarm.assert_not_called()
            mock_alert_manager.clear_alarms.assert_called_once()

    def test_recovery_from_error_clears_critical_signature(self):
        """Recovery from ERROR clears the CRITICAL-level error alarm
        (matching the level the original degrade alarm was queued at)."""
        provider = _OptedInProvider()
        provider.update_health_status(HealthStatusType.ERROR, 'broken')

        with patch('hi.apps.alert.alert_manager.AlertManager'
                   ) as mock_alert_manager_cls:
            mock_alert_manager = mock_alert_manager_cls.return_value
            provider.update_health_status(HealthStatusType.HEALTHY, 'recovered')

            mock_alert_manager.clear_alarms.assert_called_once()
            kwargs = mock_alert_manager.clear_alarms.call_args.kwargs
            self.assertEqual(kwargs['signature'].alarm_level, AlarmLevel.CRITICAL)

    def test_recovery_from_warning_clears_warning_signature(self):
        """Recovery from WARNING clears the WARNING-level alarm, not
        the CRITICAL-level one. Distinct levels would queue distinct
        signatures, so ``clear_alarms`` must target the right one."""
        provider = _OptedInProvider()
        provider.update_health_status(HealthStatusType.WARNING, 'flaky')

        with patch('hi.apps.alert.alert_manager.AlertManager'
                   ) as mock_alert_manager_cls:
            mock_alert_manager = mock_alert_manager_cls.return_value
            provider.update_health_status(HealthStatusType.HEALTHY, 'recovered')

            mock_alert_manager.clear_alarms.assert_called_once()
            kwargs = mock_alert_manager.clear_alarms.call_args.kwargs
            self.assertEqual(kwargs['signature'].alarm_level, AlarmLevel.WARNING)

    def test_recovery_from_suppressed_state_does_not_call_clear_alarms(self):
        """Recoveries from UNKNOWN or DISABLED had no prior alarm
        queued, so the dispatch path must be a no-op."""
        for prev in (HealthStatusType.UNKNOWN, HealthStatusType.DISABLED):
            provider = _OptedInProvider()
            # Seed the prior status WITHOUT going through update_health_status
            # so we don't dispatch the seed transition.
            provider._ensure_health_status_provider_setup()
            with provider._health_lock:
                provider._health_status.status = prev

            with patch('hi.apps.alert.alert_manager.AlertManager'
                       ) as mock_alert_manager_cls:
                mock_alert_manager = mock_alert_manager_cls.return_value
                provider.update_health_status(
                    HealthStatusType.HEALTHY, 'recovered',
                )
                self.assertFalse(
                    mock_alert_manager.clear_alarms.called,
                    f'recovery from {prev} should not clear anything',
                )
                self.assertFalse(
                    mock_alert_manager.upsert_alarm.called,
                    f'recovery from {prev} should not upsert anything',
                )

    def test_degrade_to_degrade_transition_takes_upsert_path(self):
        """``is_recovery`` requires ``current_status == HEALTHY``, so
        any non-HEALTHY destination -- including degrade-to-degrade
        moves like WARNING->ERROR or partial recovery ERROR->WARNING --
        takes the upsert path and never the clear path. Operator
        impact is intentional and accepted: the prior-level alert may
        coexist with the new-level alert until natural expiry; the
        operator drills into health-status detail to see the current
        truth."""
        for prev, current in [
            (HealthStatusType.WARNING, HealthStatusType.ERROR),
            (HealthStatusType.ERROR, HealthStatusType.WARNING),
        ]:
            with self.subTest(prev=prev, current=current):
                provider = _OptedInProvider()
                provider.update_health_status(prev, 'init-degraded')

                with patch('hi.apps.alert.alert_manager.AlertManager'
                           ) as mock_alert_manager_cls:
                    mock_alert_manager = mock_alert_manager_cls.return_value
                    provider.update_health_status(current, 'still-degraded')

                    mock_alert_manager.upsert_alarm.assert_called_once()
                    mock_alert_manager.clear_alarms.assert_not_called()

    def test_opted_out_provider_skips_clear_alarms_too(self):
        """A provider with no alarm ceiling never queued an alarm to
        begin with, so the recovery path must also short-circuit."""
        provider = _OptedOutProvider()
        provider.update_health_status(HealthStatusType.ERROR, 'broken')

        with patch('hi.apps.alert.alert_manager.AlertManager'
                   ) as mock_alert_manager:
            provider.update_health_status(HealthStatusType.HEALTHY, 'recovered')
            mock_alert_manager.assert_not_called()
