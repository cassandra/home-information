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

    def alarm_max_level(self):
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
        """alarm_max_level() returning None must short-circuit dispatch."""
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
