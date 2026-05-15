"""
Unit tests for the Issue #283 sync-check primitives, framework
monitor, and post-sync cache hook in ``IntegrationSynchronizer``.

The sync_check module is small and pure (set arithmetic + cache
round-trip + dataclass building); most of the value here is in the
monitor's ``do_work`` iteration semantics — that is where bugs would
hide as more integrations are added.
"""

import asyncio
import logging
from unittest.mock import Mock, patch

from django.core.cache import cache
from django.test import TestCase

from hi.integrations.sync_check import (
    IntegrationSyncCheck,
    SyncCheckOutcome,
    SyncCheckResult,
    SyncDelta,
)
from hi.integrations.monitors import IntegrationSyncCheckMonitor
from hi.integrations.transient_models import IntegrationKey


def _key(name: str, integration_id: str = 'test') -> IntegrationKey:
    """Concise IntegrationKey builder for test fixtures."""
    return IntegrationKey(integration_id=integration_id, integration_name=name)


logging.disable(logging.CRITICAL)


class SyncDeltaTests(TestCase):

    def test_empty_delta_is_not_needs_sync(self):
        delta = SyncDelta()
        self.assertFalse(delta.needs_sync)
        self.assertEqual(delta.added_count, 0)
        self.assertEqual(delta.removed_count, 0)

    def test_added_only(self):
        delta = SyncDelta(added={_key('a'), _key('b')})
        self.assertTrue(delta.needs_sync)
        self.assertEqual(delta.added_count, 2)
        self.assertEqual(delta.removed_count, 0)

    def test_removed_only(self):
        delta = SyncDelta(removed={_key('x')})
        self.assertTrue(delta.needs_sync)
        self.assertEqual(delta.added_count, 0)
        self.assertEqual(delta.removed_count, 1)

    def test_both_sides(self):
        delta = SyncDelta(added={_key('a')}, removed={_key('x'), _key('y')})
        self.assertTrue(delta.needs_sync)
        self.assertEqual(delta.added_count, 1)
        self.assertEqual(delta.removed_count, 2)


class ComputeDeltaTests(TestCase):

    def test_identical_sets_yield_no_drift(self):
        delta = IntegrationSyncCheck.compute_delta(
            upstream_keys={_key('a'), _key('b'), _key('c')},
            current_keys={_key('a'), _key('b'), _key('c')},
        )
        self.assertFalse(delta.needs_sync)

    def test_disjoint_sets_yield_full_drift_both_sides(self):
        delta = IntegrationSyncCheck.compute_delta(
            upstream_keys={_key('a'), _key('b')},
            current_keys={_key('x'), _key('y')},
        )
        self.assertEqual(delta.added, {_key('a'), _key('b')})
        self.assertEqual(delta.removed, {_key('x'), _key('y')})

    def test_upstream_added(self):
        delta = IntegrationSyncCheck.compute_delta(
            upstream_keys={_key('a'), _key('b'), _key('c')},
            current_keys={_key('a'), _key('b')},
        )
        self.assertEqual(delta.added, {_key('c')})
        self.assertEqual(delta.removed, set())

    def test_upstream_removed(self):
        delta = IntegrationSyncCheck.compute_delta(
            upstream_keys={_key('a')},
            current_keys={_key('a'), _key('b')},
        )
        self.assertEqual(delta.added, set())
        self.assertEqual(delta.removed, {_key('b')})

    def test_both_sides_empty(self):
        delta = IntegrationSyncCheck.compute_delta(
            upstream_keys=set(),
            current_keys=set(),
        )
        self.assertFalse(delta.needs_sync)

    def test_case_mismatch_handled_via_integration_key(self):
        # Regression: stored entity.integration_name values are
        # lowercased by IntegrationKey.__post_init__. A probe whose
        # upstream-key derivation produces mixed-case integration
        # names would false-positive every time without IntegrationKey
        # canonicalization. Set arithmetic on IntegrationKey instances
        # picks up the lowercasing automatically via __hash__/__eq__.
        delta = IntegrationSyncCheck.compute_delta(
            upstream_keys={_key('INSTEON:01.AA.01'), _key('insteon:01.AA.02')},
            current_keys={_key('insteon:01.aa.01'), _key('insteon:01.aa.02')},
        )
        self.assertFalse(delta.needs_sync)


class BuildResultAndSummaryTests(TestCase):

    def test_in_sync_message_is_concise(self):
        result = IntegrationSyncCheck.build_result(
            delta=SyncDelta(),
            integration_label='HomeBox',
        )
        self.assertFalse(result.needs_sync)
        self.assertIn('up to date', result.summary_message)
        self.assertIn('HomeBox', result.summary_message)

    def test_added_only_message_pluralizes(self):
        result = IntegrationSyncCheck.build_result(
            delta=SyncDelta(added={_key('a'), _key('b'), _key('c')}),
            integration_label='Home Assistant',
        )
        self.assertIn('3 new items upstream', result.summary_message)
        # The Refresh call-to-action is intentionally NOT in the
        # summary string — it is rendered as a real link by the
        # manage-page banner template.
        self.assertNotIn('REFRESH', result.summary_message)

    def test_singular_pluralization(self):
        result = IntegrationSyncCheck.build_result(
            delta=SyncDelta(added={_key('a')}),
            integration_label='HomeBox',
        )
        self.assertIn('1 new item upstream', result.summary_message)

    def test_removed_message(self):
        result = IntegrationSyncCheck.build_result(
            delta=SyncDelta(removed={_key('x'), _key('y')}),
            integration_label='ZoneMinder',
        )
        self.assertIn('2 items removed upstream', result.summary_message)

    def test_both_sides_message(self):
        result = IntegrationSyncCheck.build_result(
            delta=SyncDelta(added={_key('a')}, removed={_key('x')}),
            integration_label='HomeBox',
        )
        self.assertIn('1 new item upstream', result.summary_message)
        self.assertIn('1 item removed upstream', result.summary_message)


class CacheHelperTests(TestCase):

    INTEGRATION_A = 'integration_a'
    INTEGRATION_B = 'integration_b'

    def setUp(self):
        cache.clear()

    def tearDown(self):
        cache.clear()

    def test_round_trip(self):
        result = IntegrationSyncCheck.build_result(
            delta=SyncDelta(added={_key('k1')}),
            integration_label='Test Integration',
        )
        IntegrationSyncCheck.set_state(
            integration_id=self.INTEGRATION_A,
            result=result,
        )
        loaded = IntegrationSyncCheck.get_state(self.INTEGRATION_A)
        self.assertIsNotNone(loaded)
        self.assertTrue(loaded.needs_sync)
        self.assertEqual(loaded.delta.added, {_key('k1')})
        self.assertEqual(loaded.summary_message, result.summary_message)

    def test_per_integration_isolation(self):
        result_a = IntegrationSyncCheck.build_result(
            delta=SyncDelta(added={_key('k1')}),
            integration_label='A',
        )
        IntegrationSyncCheck.set_state(self.INTEGRATION_A, result_a)
        # B has no entry — must not surface A's result.
        self.assertIsNone(IntegrationSyncCheck.get_state(self.INTEGRATION_B))
        # Setting B does not perturb A.
        result_b = IntegrationSyncCheck.build_result(
            delta=SyncDelta(removed={_key('k2')}),
            integration_label='B',
        )
        IntegrationSyncCheck.set_state(self.INTEGRATION_B, result_b)
        loaded_a = IntegrationSyncCheck.get_state(self.INTEGRATION_A)
        loaded_b = IntegrationSyncCheck.get_state(self.INTEGRATION_B)
        self.assertEqual(loaded_a.delta.added, {_key('k1')})
        self.assertEqual(loaded_b.delta.removed, {_key('k2')})

    def test_clear_removes_entry(self):
        IntegrationSyncCheck.set_state(
            integration_id=self.INTEGRATION_A,
            result=IntegrationSyncCheck.build_result(
                delta=SyncDelta(added={_key('x')}),
                integration_label='A',
            ),
        )
        IntegrationSyncCheck.clear_state(self.INTEGRATION_A)
        self.assertIsNone(IntegrationSyncCheck.get_state(self.INTEGRATION_A))

    def test_get_with_no_entry_returns_none(self):
        self.assertIsNone(IntegrationSyncCheck.get_state('never_set'))

    def test_empty_integration_id_is_safe_no_op(self):
        # Defensive: empty / None integration_id must not pollute the
        # cache namespace or raise.
        self.assertIsNone(IntegrationSyncCheck.get_state(''))
        IntegrationSyncCheck.set_state(
            integration_id='',
            result=IntegrationSyncCheck.build_result(
                delta=SyncDelta(),
                integration_label='whatever',
            ),
        )
        IntegrationSyncCheck.clear_state('')
        # No exceptions; nothing to assert beyond reaching here.

    def test_record_sync_complete_writes_zero_delta_with_timestamp(self):
        # Pre-populate a stale "needs sync" state.
        IntegrationSyncCheck.set_state(
            integration_id=self.INTEGRATION_A,
            result=IntegrationSyncCheck.build_result(
                delta=SyncDelta(added={_key('k1'), _key('k2')}),
                integration_label='A',
            ),
        )
        # Record completion.
        IntegrationSyncCheck.record_sync_complete(
            integration_id=self.INTEGRATION_A,
            integration_label='A',
        )
        loaded = IntegrationSyncCheck.get_state(self.INTEGRATION_A)
        # Cache is now a zero-delta result, not cleared.
        self.assertIsNotNone(loaded)
        self.assertFalse(loaded.needs_sync)
        self.assertEqual(loaded.delta.added, set())
        self.assertEqual(loaded.delta.removed, set())
        self.assertIsNotNone(loaded.last_checked_at)


class TransitionAlarmTests(TestCase):
    """Phase 4 (Issue #283): clear→needs_sync transition fires a
    fresh alarm; in-progress drift does not re-alarm cycle after
    cycle. The predicate ``_should_alarm`` is the single source of
    truth and is tested directly; the wiring inside ``set_state`` is
    tested by patching ``_fire_needs_sync_alarm`` and asserting call
    counts."""

    INTEGRATION_ID = 'transition_test'

    def setUp(self):
        cache.clear()

    def tearDown(self):
        cache.clear()

    def _result(self, *, needs_sync):
        return IntegrationSyncCheck.build_result(
            delta=(
                SyncDelta(added={_key('x')}) if needs_sync else SyncDelta()
            ),
            integration_label='Transition Test',
        )

    # ---- predicate ----

    def test_should_alarm_when_prior_is_none_and_needs_sync(self):
        self.assertTrue(IntegrationSyncCheck._should_alarm(
            prior=None,
            current=self._result(needs_sync=True),
        ))

    def test_should_alarm_on_clean_to_needs_sync_transition(self):
        self.assertTrue(IntegrationSyncCheck._should_alarm(
            prior=self._result(needs_sync=False),
            current=self._result(needs_sync=True),
        ))

    def test_should_not_alarm_when_drift_persists(self):
        self.assertFalse(IntegrationSyncCheck._should_alarm(
            prior=self._result(needs_sync=True),
            current=self._result(needs_sync=True),
        ))

    def test_should_not_alarm_on_set_to_clear_transition(self):
        # Refresh just succeeded — current is in-sync. Never an
        # alarm direction.
        self.assertFalse(IntegrationSyncCheck._should_alarm(
            prior=self._result(needs_sync=True),
            current=self._result(needs_sync=False),
        ))

    def test_should_not_alarm_when_both_clean(self):
        self.assertFalse(IntegrationSyncCheck._should_alarm(
            prior=self._result(needs_sync=False),
            current=self._result(needs_sync=False),
        ))

    def test_should_not_alarm_when_prior_none_and_current_clean(self):
        # First-ever probe finds no drift — nothing to alarm about.
        self.assertFalse(IntegrationSyncCheck._should_alarm(
            prior=None,
            current=self._result(needs_sync=False),
        ))

    # ---- wiring ----

    def test_set_state_fires_alarm_on_first_drift_detection(self):
        with patch.object(
                IntegrationSyncCheck, '_fire_needs_sync_alarm',
        ) as mock_fire:
            IntegrationSyncCheck.set_state(
                integration_id=self.INTEGRATION_ID,
                result=self._result(needs_sync=True),
            )
        mock_fire.assert_called_once()

    def test_set_state_does_not_re_fire_when_drift_persists(self):
        # First write triggers alarm.
        IntegrationSyncCheck.set_state(
            integration_id=self.INTEGRATION_ID,
            result=self._result(needs_sync=True),
        )
        # Second write with same needs_sync state must NOT re-fire.
        with patch.object(
                IntegrationSyncCheck, '_fire_needs_sync_alarm',
        ) as mock_fire:
            IntegrationSyncCheck.set_state(
                integration_id=self.INTEGRATION_ID,
                result=self._result(needs_sync=True),
            )
        mock_fire.assert_not_called()

    def test_set_state_re_fires_after_refresh_then_drift(self):
        # Initial drift → alarm.
        IntegrationSyncCheck.set_state(
            integration_id=self.INTEGRATION_ID,
            result=self._result(needs_sync=True),
        )
        # Refresh succeeds → zero-delta result; no alarm.
        IntegrationSyncCheck.record_sync_complete(
            integration_id=self.INTEGRATION_ID,
            integration_label='Transition Test',
        )
        # New drift cycle → alarm again (this is the canonical
        # re-fire path: user acted, then upstream changed again).
        with patch.object(
                IntegrationSyncCheck, '_fire_needs_sync_alarm',
        ) as mock_fire:
            IntegrationSyncCheck.set_state(
                integration_id=self.INTEGRATION_ID,
                result=self._result(needs_sync=True),
            )
        mock_fire.assert_called_once()

    def test_record_sync_complete_does_not_fire_alarm(self):
        # Pre-populate a stale needs-sync state.
        IntegrationSyncCheck.set_state(
            integration_id=self.INTEGRATION_ID,
            result=self._result(needs_sync=True),
        )
        with patch.object(
                IntegrationSyncCheck, '_fire_needs_sync_alarm',
        ) as mock_fire:
            IntegrationSyncCheck.record_sync_complete(
                integration_id=self.INTEGRATION_ID,
                integration_label='Transition Test',
            )
        mock_fire.assert_not_called()

    def test_alarm_failure_does_not_break_set_state(self):
        # Alarm subsystem unavailable / raises — cache write should
        # have already succeeded and set_state should not propagate
        # the failure.
        with patch.object(
                IntegrationSyncCheck, '_fire_needs_sync_alarm',
                side_effect=RuntimeError('alert system down'),
        ):
            IntegrationSyncCheck.set_state(
                integration_id=self.INTEGRATION_ID,
                result=self._result(needs_sync=True),
            )
        # State is still recorded despite the alarm failure.
        loaded = IntegrationSyncCheck.get_state(self.INTEGRATION_ID)
        self.assertIsNotNone(loaded)
        self.assertTrue(loaded.needs_sync)

    # ---- alarm shape ----

    def test_fire_needs_sync_alarm_constructs_expected_alarm(self):
        from hi.apps.alert.alarm import Alarm
        from hi.apps.alert.enums import AlarmLevel, AlarmSource
        captured = []

        def capture(alarm):
            captured.append(alarm)

        with patch(
                'hi.apps.alert.alert_manager.AlertManager',
        ) as mock_manager_class:
            mock_manager_class.return_value.add_alarm = capture
            IntegrationSyncCheck._fire_needs_sync_alarm(
                integration_id=self.INTEGRATION_ID,
                result=self._result(needs_sync=True),
            )

        self.assertEqual(len(captured), 1)
        alarm = captured[0]
        self.assertEqual(alarm.alarm_source, AlarmSource.INTEGRATION)
        self.assertEqual(
            alarm.alarm_type,
            f'integrations.needs_sync.{self.INTEGRATION_ID}',
        )
        self.assertEqual(alarm.alarm_level, AlarmLevel.INFO)
        # Drift alarms should persist until acknowledged, which is
        # expressed in this codebase as ``Alarm.MAX_LIFETIME_SECS``
        # (a sentinel "never expires" value — non-zero so
        # ``end_datetime`` arithmetic remains uniform across all
        # alarm types).
        self.assertEqual(alarm.alarm_lifetime_secs, Alarm.MAX_LIFETIME_SECS)
        # Per-integration unique signature so two integrations
        # drifting yield two distinct alerts.
        self.assertIn(self.INTEGRATION_ID, alarm.signature)


class _StubIntegrationData:
    """Minimal duck-typed IntegrationData stand-in for the monitor's
    iteration tests. The real IntegrationData is a dataclass over
    Integration model rows; the monitor only reads the gateway, the
    metadata, the integration_id, and the is_paused flag, so a stub
    keeps the tests focused and isolated from DB fixtures."""

    def __init__(self, integration_id, label, gateway, is_paused=False):
        self.integration_id = integration_id
        self.integration_gateway = gateway
        self.integration_metadata = Mock(integration_id=integration_id, label=label)
        self.is_paused = is_paused


def _stub_gateway_returning(delta_or_exception, has_synchronizer=True):
    """Build a Mock gateway whose ``get_synchronizer()`` returns a
    Mock synchronizer whose ``check_needs_sync`` coroutine returns
    the given SyncDelta (or None) — or raises if an Exception is
    supplied. Pass ``has_synchronizer=False`` to simulate an
    integration that does not support sync at all (gateway returns
    None from get_synchronizer)."""
    gateway = Mock()
    if not has_synchronizer:
        gateway.get_synchronizer = Mock(return_value=None)
        return gateway

    synchronizer = Mock()

    async def check_needs_sync():
        if isinstance(delta_or_exception, BaseException):
            raise delta_or_exception
        return delta_or_exception

    synchronizer.check_needs_sync = check_needs_sync
    gateway.get_synchronizer = Mock(return_value=synchronizer)
    return gateway


class IntegrationSyncCheckMonitorTests(TestCase):
    """Iteration semantics for the framework monitor's do_work."""

    def setUp(self):
        cache.clear()

    def tearDown(self):
        cache.clear()

    def _run(self, monitor):
        asyncio.run(monitor.do_work())

    def _patch_manager_with(self, integration_data_list):
        """Patch IntegrationManager so do_work sees this fixture set.
        The manager's get_integration_data_list(enabled_only=True) is
        the only accessor do_work calls; mocking it keeps the test
        isolated from singleton state."""
        manager = Mock()
        manager.get_integration_data_list.return_value = integration_data_list
        return patch(
            'hi.integrations.integration_manager.IntegrationManager',
            return_value=manager,
        )

    def test_writes_cache_when_gateway_returns_delta(self):
        gateway = _stub_gateway_returning(SyncDelta(added={_key('k1')}))
        data = _StubIntegrationData('a', 'A', gateway)

        with self._patch_manager_with([data]):
            self._run(IntegrationSyncCheckMonitor())

        loaded = IntegrationSyncCheck.get_state('a')
        self.assertIsNotNone(loaded)
        self.assertTrue(loaded.needs_sync)
        self.assertEqual(loaded.delta.added, {_key('k1')})

    def test_no_cache_write_when_synchronizer_returns_none(self):
        gateway = _stub_gateway_returning(None)
        data = _StubIntegrationData('a', 'A', gateway)

        with self._patch_manager_with([data]):
            self._run(IntegrationSyncCheckMonitor())

        # Synchronizer present but check returned None: opt-out, no
        # cache entry.
        self.assertIsNone(IntegrationSyncCheck.get_state('a'))

    def test_no_cache_write_when_gateway_has_no_synchronizer(self):
        # Integration that does not support sync at all
        # (get_synchronizer returns None) is naturally opted out of
        # sync-check too — sync-check rides on the same
        # capability.
        gateway = _stub_gateway_returning(None, has_synchronizer=False)
        data = _StubIntegrationData('a', 'A', gateway)

        with self._patch_manager_with([data]):
            self._run(IntegrationSyncCheckMonitor())

        self.assertIsNone(IntegrationSyncCheck.get_state('a'))

    def test_paused_integration_is_skipped(self):
        gateway = _stub_gateway_returning(SyncDelta(added={_key('k1')}))
        data = _StubIntegrationData('a', 'A', gateway, is_paused=True)

        with self._patch_manager_with([data]):
            self._run(IntegrationSyncCheckMonitor())

        # Paused → not invoked, nothing cached.
        self.assertIsNone(IntegrationSyncCheck.get_state('a'))

    def test_one_integration_failure_does_not_abort_cycle(self):
        # First integration raises; second returns a real delta.
        # Without the per-integration try/except, the cycle would
        # abort before reaching B and B's cache entry would never
        # land.
        failing = _StubIntegrationData(
            'a', 'A', _stub_gateway_returning(RuntimeError('upstream down')),
        )
        ok = _StubIntegrationData(
            'b', 'B', _stub_gateway_returning(SyncDelta(removed={_key('x')})),
        )

        with self._patch_manager_with([failing, ok]):
            self._run(IntegrationSyncCheckMonitor())

        self.assertIsNone(IntegrationSyncCheck.get_state('a'))
        loaded_b = IntegrationSyncCheck.get_state('b')
        self.assertIsNotNone(loaded_b)
        self.assertTrue(loaded_b.needs_sync)
        self.assertEqual(loaded_b.delta.removed, {_key('x')})

    def test_per_integration_probe_error_does_not_escalate_monitor_status(self):
        # Integration upstream error must NOT bump the framework
        # monitor to WARNING — that would duplicate the alert each
        # integration's own health monitor already raises and
        # mis-blame the framework monitor for an integration-level
        # failure. The cycle stays HEALTHY; the count is surfaced
        # in the message for operator visibility.
        failing = _StubIntegrationData(
            'a', 'A', _stub_gateway_returning(RuntimeError('upstream down')),
        )

        monitor = IntegrationSyncCheckMonitor()
        with self._patch_manager_with([failing]):
            self._run(monitor)

        from hi.apps.system.enums import HealthStatusType
        self.assertEqual(monitor.health_status.status, HealthStatusType.HEALTHY)
        self.assertIn('1 integration probe error', monitor.health_status.last_message)

    def test_outcome_classification(self):
        # Direct test of _check_one_integration so the enum classifications
        # are pinned independently of do_work bookkeeping.
        monitor = IntegrationSyncCheckMonitor()

        opted_out_data = _StubIntegrationData(
            'opt', 'Opt', _stub_gateway_returning(None),
        )
        in_sync_data = _StubIntegrationData(
            'in_sync', 'InSync', _stub_gateway_returning(SyncDelta()),
        )
        needs_sync_data = _StubIntegrationData(
            'needs', 'Needs', _stub_gateway_returning(SyncDelta(added={_key('k')})),
        )
        error_data = _StubIntegrationData(
            'err', 'Err', _stub_gateway_returning(RuntimeError('boom')),
        )

        self.assertEqual(
            asyncio.run(monitor._check_one_integration(opted_out_data)),
            SyncCheckOutcome.OPTED_OUT,
        )
        self.assertEqual(
            asyncio.run(monitor._check_one_integration(in_sync_data)),
            SyncCheckOutcome.IN_SYNC,
        )
        self.assertEqual(
            asyncio.run(monitor._check_one_integration(needs_sync_data)),
            SyncCheckOutcome.NEEDS_SYNC,
        )
        self.assertEqual(
            asyncio.run(monitor._check_one_integration(error_data)),
            SyncCheckOutcome.ERROR,
        )


class IntegrationSynchronizerPostSyncHookTests(TestCase):
    """The post-sync hook clears (writes a zero-delta SyncCheckResult
    with current timestamp) on a successful sync, and leaves the
    cache alone when the sync errored."""

    INTEGRATION_ID = 'sync_post_hook_test'
    INTEGRATION_LABEL = 'Post-Hook Test Integration'

    def setUp(self):
        cache.clear()

    def tearDown(self):
        cache.clear()

    def _make_synchronizer(self, sync_impl_result):
        """Build a concrete IntegrationSynchronizer whose _sync_impl
        returns the given result. We test sync() (the public entry
        point) so the post-hook fires the same way it does in
        production."""
        from hi.integrations.integration_synchronizer import IntegrationSynchronizer
        from hi.integrations.transient_models import IntegrationMetaData

        class _TestSynchronizer(IntegrationSynchronizer):
            SYNCHRONIZATION_LOCK_NAME = 'sync_check_test_lock'

            def get_integration_metadata(self):
                return IntegrationMetaData(
                    integration_id=IntegrationSynchronizerPostSyncHookTests.INTEGRATION_ID,
                    label=IntegrationSynchronizerPostSyncHookTests.INTEGRATION_LABEL,
                    attribute_type=Mock(),
                    allow_entity_deletion=True,
                )

            def _sync_impl(self, is_initial_import):
                return sync_impl_result

        return _TestSynchronizer()

    def test_successful_sync_records_zero_delta_completion(self):
        from hi.integrations.sync_result import IntegrationSyncResult

        # Pre-populate a stale "needs sync" state.
        IntegrationSyncCheck.set_state(
            integration_id=self.INTEGRATION_ID,
            result=IntegrationSyncCheck.build_result(
                delta=SyncDelta(added={'a', 'b'}),
                integration_label=self.INTEGRATION_LABEL,
            ),
        )
        synchronizer = self._make_synchronizer(
            sync_impl_result=IntegrationSyncResult(title='Refresh Result'),
        )

        synchronizer.sync(is_initial_import=False)

        loaded = IntegrationSyncCheck.get_state(self.INTEGRATION_ID)
        self.assertIsNotNone(loaded)
        self.assertFalse(loaded.needs_sync)

    def test_failed_sync_leaves_cache_alone(self):
        from hi.integrations.sync_result import IntegrationSyncResult

        # Pre-populate a stale needs-sync state.
        stale = IntegrationSyncCheck.build_result(
            delta=SyncDelta(added={_key('a'), _key('b')}),
            integration_label=self.INTEGRATION_LABEL,
        )
        IntegrationSyncCheck.set_state(
            integration_id=self.INTEGRATION_ID,
            result=stale,
        )
        synchronizer = self._make_synchronizer(
            sync_impl_result=IntegrationSyncResult(
                title='Refresh Result',
                error_list=['something went wrong'],
            ),
        )

        synchronizer.sync(is_initial_import=False)

        loaded = IntegrationSyncCheck.get_state(self.INTEGRATION_ID)
        self.assertIsNotNone(loaded)
        # Stale state still present — failed sync did not clear it.
        self.assertTrue(loaded.needs_sync)
        self.assertEqual(loaded.delta.added, {_key('a'), _key('b')})


class SyncCheckResultEqualityTests(TestCase):
    """Frozen dataclass equality is the only path tests use to compare
    cache entries; pin it explicitly so a future field change does
    not silently change comparison semantics."""

    def test_two_results_with_same_fields_compare_equal(self):
        from datetime import datetime, timezone
        ts = datetime(2026, 5, 6, 12, 0, tzinfo=timezone.utc)
        a = SyncCheckResult(
            delta=SyncDelta(added={_key('k')}),
            last_checked_at=ts,
            summary_message='msg',
        )
        b = SyncCheckResult(
            delta=SyncDelta(added={_key('k')}),
            last_checked_at=ts,
            summary_message='msg',
        )
        self.assertEqual(a, b)
