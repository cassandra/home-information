"""Tests for ``ZoneMinderMonitor._process_events`` per-transition emit.

The monitor's polling/cursor/cache machinery is preserved verbatim
from the prior aggregation-based implementation — these tests guard
both the emit semantics introduced by #351 (one response per real
transition, no per-monitor collapse) and the hard-won cursor /
cache invariants that #351 explicitly did not touch.
"""
import logging
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

from hi.apps.entity.enums import EntityStateValue
from hi.apps.sense.enums import CorrelationRole
from hi.integrations.transient_models import IntegrationKey
from hi.testing.async_task_utils import AsyncTaskFastTestCase

from hi.services.zoneminder.monitors import ZoneMinderMonitor

logging.disable( logging.CRITICAL )


def _mock_zm_event( event_id : str, monitor_id : int, start, end = None ):
    """Build a duck-typed stand-in for ``ZmEvent``. The monitor only
    reads ``event_id`` / ``monitor_id`` / ``start_datetime`` /
    ``end_datetime`` / ``is_open`` on these objects, so a Mock with
    those attributes suffices and avoids the pyzm-shaped api-dict
    construction path."""
    event = Mock()
    event.event_id = event_id
    event.monitor_id = monitor_id
    event.start_datetime = start
    event.end_datetime = end
    event.is_open = ( end is None )
    return event


def _mock_zm_monitor( monitor_id : int ):
    monitor = Mock()
    monitor.id.return_value = monitor_id
    return monitor


class _ZmMonitorPipelineBase( AsyncTaskFastTestCase ):
    """Shared scaffolding. ``_process_events`` is async and depends on
    the ZM manager's events / monitors fetches plus the response-
    factory helpers. We mock the manager methods and stub the
    factories with thin tagged-Mock returns so tests can assert on
    the sequence of emissions per integration_key without involving
    full ``SensorResponse`` construction."""

    def setUp(self):
        super().setUp()
        self.monitor = ZoneMinderMonitor()
        self.monitor._was_initialized = True
        self.start = datetime( 2026, 5, 22, 12, 0, 0, tzinfo = timezone.utc )
        self.monitor._poll_from_datetime = self.start
        self.monitor._zm_tzname = 'UTC'

        # Mock the ZM manager. ``zm_manager()`` (the SensorResponseMixin
        # getter) returns ``self._zm_manager``; we assign directly to
        # bypass async initialization.
        self.mock_manager = Mock()
        self.monitor._zm_manager = self.mock_manager

        async def empty_events( options = None ):
            return []

        async def empty_monitors( force_load = False ):
            return []

        self.mock_manager.get_zm_events_async = Mock( side_effect = empty_events )
        self.mock_manager.get_zm_monitors_async = Mock( side_effect = empty_monitors )

        # The ZmEvent construction path requires a real pyzm-shaped
        # api dict. Bypass it by stubbing the construction to take
        # our duck-typed mock events directly. Tests pass already-
        # built mock events via ``_set_events`` below.
        self._next_events_returns_directly = []

        async def fake_events( options = None ):
            return self._next_events_returns_directly

        self.mock_manager.get_zm_events_async = Mock( side_effect = fake_events )

        # Real ``IntegrationKey`` (frozen-equality dataclass) so all
        # responses for the same monitor share an identical hashable
        # key — required for the per-key dict grouping in
        # ``_process_events`` to collapse correctly. Mock instances
        # would be unique-by-identity and split each emission into
        # its own dict slot.
        def _key_for( monitor_id ):
            return IntegrationKey(
                integration_id = 'zm',
                integration_name = f'movement.{monitor_id}',
            )

        def fake_active( zm_event ):
            response = Mock()
            response.integration_key = _key_for( zm_event.monitor_id )
            response.value = str( EntityStateValue.ACTIVE )
            response.correlation_role = CorrelationRole.START
            response.correlation_id = zm_event.event_id
            response.timestamp = zm_event.start_datetime
            return response

        def fake_idle( zm_event ):
            response = Mock()
            response.integration_key = _key_for( zm_event.monitor_id )
            response.value = str( EntityStateValue.IDLE )
            response.correlation_role = CorrelationRole.END
            response.correlation_id = zm_event.event_id
            response.timestamp = zm_event.end_datetime
            return response

        def fake_heartbeat_idle( zm_monitor, timestamp ):
            response = Mock()
            response.integration_key = _key_for( zm_monitor.id() )
            response.value = str( EntityStateValue.IDLE )
            response.correlation_role = None
            response.correlation_id = None
            response.timestamp = timestamp
            return response

        self.monitor._create_movement_active_sensor_response = Mock(
            side_effect = fake_active,
        )
        self.monitor._create_movement_idle_sensor_response = Mock(
            side_effect = fake_idle,
        )
        self.monitor._create_idle_sensor_response = Mock(
            side_effect = fake_heartbeat_idle,
        )

        # The collation step at the top of ``_process_events`` runs
        # ``ZmEvent(zm_api_event=..., zm_tzname=...)`` on each item
        # returned from ``get_zm_events_async``. Stubbing
        # ``get_zm_events_async`` to return our duck-typed mocks
        # isn't enough — the ZmEvent constructor would still run.
        # Patch the constructor in the monitor module so it returns
        # the duck-typed mock unchanged.
        import hi.services.zoneminder.monitors as monitors_mod
        self._original_zm_event = monitors_mod.ZmEvent
        monitors_mod.ZmEvent = lambda zm_api_event, zm_tzname : zm_api_event
        self.addCleanup(
            lambda: setattr( monitors_mod, 'ZmEvent', self._original_zm_event ),
        )
        return

    def _set_events(self, zm_events):
        self._next_events_returns_directly = zm_events

    def _set_monitors(self, monitor_ids):
        async def fake_monitors( force_load = False ):
            return [ _mock_zm_monitor( mid ) for mid in monitor_ids ]
        self.mock_manager.get_zm_monitors_async = Mock(
            side_effect = fake_monitors,
        )

    def _responses_for(self, response_map, monitor_id):
        target = f'movement.{monitor_id}'
        for integration_key, response_list in response_map.items():
            if integration_key.integration_name == target:
                return response_list
            continue
        raise AssertionError(
            f'No responses for monitor {monitor_id!r}'
        )

    async def _run(self):
        return await self.monitor._process_events()


class TestZoneMinderMonitorEventEmission( _ZmMonitorPipelineBase ):
    """Per-transition emit: each real motion event start and stop
    produces its own response. The old single-response-per-monitor
    collapse is gone; multi-event-per-monitor cycles propagate
    fully."""

    def test_single_open_event_emits_start_and_caches_start(self):
        event = _mock_zm_event( 'A', 1, self.start + timedelta( seconds = 1 ))
        self._set_events([ event ])
        result = self.run_async( self._run() )

        responses = self._responses_for( result, 1 )
        self.assertEqual( len( responses ), 1 )
        self.assertEqual( responses[ 0 ].correlation_role, CorrelationRole.START )
        self.assertEqual( responses[ 0 ].correlation_id, 'A' )
        self.assertIn( 'A', self.monitor._start_processed_event_ids )
        self.assertNotIn( 'A', self.monitor._fully_processed_event_ids )

    def test_still_open_event_across_two_polls_emits_start_only_once(self):
        # The cursor-hold model re-fetches an open event on each poll
        # until it closes. The start_processed cache must gate START
        # re-emission so the downstream stream sees a single START.
        event = _mock_zm_event( 'A', 1, self.start + timedelta( seconds = 1 ))

        self._set_events([ event ])
        first = self.run_async( self._run() )
        self.assertEqual( len( self._responses_for( first, 1 )), 1 )

        self._set_events([ event ])
        second = self.run_async( self._run() )
        # No new response on the second poll for the same open event.
        with self.assertRaises( AssertionError ):
            self._responses_for( second, 1 )

    def test_open_then_closed_across_polls_emits_paired_start_then_end(self):
        # Cycle 1: event A is open. START emitted, cached.
        # Cycle 2: same event is now closed. END emitted; START not
        # re-emitted.
        s = self.start + timedelta( seconds = 1 )
        e = s + timedelta( seconds = 30 )

        self._set_events([ _mock_zm_event( 'A', 1, s, None ) ])
        cycle1 = self.run_async( self._run() )
        c1 = self._responses_for( cycle1, 1 )
        self.assertEqual( len( c1 ), 1 )
        self.assertEqual( c1[ 0 ].correlation_role, CorrelationRole.START )

        self._set_events([ _mock_zm_event( 'A', 1, s, e ) ])
        cycle2 = self.run_async( self._run() )
        c2 = self._responses_for( cycle2, 1 )
        self.assertEqual( len( c2 ), 1 )
        self.assertEqual( c2[ 0 ].correlation_role, CorrelationRole.END )
        self.assertIn( 'A', self.monitor._fully_processed_event_ids )

    def test_event_observed_already_closed_emits_both_start_and_end(self):
        # Event opened and closed entirely within one poll window —
        # the monitor never saw it open, so both START and END must
        # be emitted in this single cycle so the active interval is
        # recorded.
        s = self.start + timedelta( seconds = 1 )
        e = s + timedelta( seconds = 30 )
        self._set_events([ _mock_zm_event( 'A', 1, s, e ) ])
        result = self.run_async( self._run() )

        responses = self._responses_for( result, 1 )
        roles = [ r.correlation_role for r in responses ]
        self.assertEqual(
            roles, [ CorrelationRole.START, CorrelationRole.END ],
        )
        self.assertTrue(
            all( r.correlation_id == 'A' for r in responses ),
        )
        self.assertIn( 'A', self.monitor._fully_processed_event_ids )

    def test_scenario_a_closed_plus_open_same_monitor_emits_both(self):
        # Issue #351 Scenario A. Monitor M sees:
        #   - Event A (closed, ended T1)
        #   - Event B (open, started T2 > T1)
        # Under the old aggregation, A's END was silently dropped.
        # The new emit path produces BOTH transitions for monitor M.
        a_start = self.start + timedelta( seconds = 1 )
        a_end = a_start + timedelta( seconds = 30 )
        b_start = a_end + timedelta( seconds = 10 )
        self._set_events([
            _mock_zm_event( 'A', 1, a_start, a_end ),
            _mock_zm_event( 'B', 1, b_start, None ),
        ])
        result = self.run_async( self._run() )

        responses = self._responses_for( result, 1 )
        roles_and_ids = [
            ( r.correlation_role, r.correlation_id ) for r in responses
        ]
        # A was observed only-closed in this cycle, so both START A
        # and END A emit. B was observed open, so START B emits.
        # Total: 3 responses on monitor 1.
        self.assertEqual( len( responses ), 3 )
        self.assertIn( ( CorrelationRole.START, 'A' ), roles_and_ids )
        self.assertIn( ( CorrelationRole.END, 'A' ), roles_and_ids )
        self.assertIn( ( CorrelationRole.START, 'B' ), roles_and_ids )
        self.assertIn( 'A', self.monitor._fully_processed_event_ids )
        self.assertIn( 'B', self.monitor._start_processed_event_ids )
        self.assertNotIn( 'B', self.monitor._fully_processed_event_ids )

    def test_scenario_b_two_closed_same_monitor_emits_full_sequence(self):
        # Issue #351 Scenario B. Monitor M sees:
        #   - Event A (closed, ended T1)
        #   - Event B (closed, ended T2 > T1)
        # Old aggregation dropped A's transitions entirely AND
        # dropped B's START. New emit produces all four transitions.
        a_start = self.start + timedelta( seconds = 1 )
        a_end = a_start + timedelta( seconds = 30 )
        b_start = a_end + timedelta( seconds = 10 )
        b_end = b_start + timedelta( seconds = 30 )
        self._set_events([
            _mock_zm_event( 'A', 1, a_start, a_end ),
            _mock_zm_event( 'B', 1, b_start, b_end ),
        ])
        result = self.run_async( self._run() )

        responses = self._responses_for( result, 1 )
        roles_and_ids = [
            ( r.correlation_role, r.correlation_id ) for r in responses
        ]
        self.assertEqual( len( responses ), 4 )
        for expected in [
                ( CorrelationRole.START, 'A' ),
                ( CorrelationRole.END, 'A' ),
                ( CorrelationRole.START, 'B' ),
                ( CorrelationRole.END, 'B' ),
        ]:
            self.assertIn( expected, roles_and_ids )
        self.assertIn( 'A', self.monitor._fully_processed_event_ids )
        self.assertIn( 'B', self.monitor._fully_processed_event_ids )

    def test_multiple_monitors_independent(self):
        a = _mock_zm_event( 'A', 1, self.start + timedelta( seconds = 1 ))
        b = _mock_zm_event( 'B', 2, self.start + timedelta( seconds = 2 ))
        self._set_events([ a, b ])
        result = self.run_async( self._run() )

        m1 = self._responses_for( result, 1 )
        m2 = self._responses_for( result, 2 )
        self.assertEqual( len( m1 ), 1 )
        self.assertEqual( m1[ 0 ].correlation_id, 'A' )
        self.assertEqual( len( m2 ), 1 )
        self.assertEqual( m2[ 0 ].correlation_id, 'B' )

    def test_fully_processed_event_is_skipped_on_next_poll(self):
        # Once an event is fully processed (closed and emitted), the
        # cursor-hold model may still return it on subsequent polls
        # (start_time >= cursor); the cache filter at the top of
        # ``_process_events`` ensures it's not re-emitted.
        s = self.start + timedelta( seconds = 1 )
        e = s + timedelta( seconds = 30 )
        self._set_events([ _mock_zm_event( 'A', 1, s, e ) ])
        self.run_async( self._run() )
        self.assertIn( 'A', self.monitor._fully_processed_event_ids )

        # Subsequent poll: ZM returns the same closed event again.
        self._set_events([ _mock_zm_event( 'A', 1, s, e ) ])
        result = self.run_async( self._run() )
        # No new responses; the cache short-circuited.
        with self.assertRaises( AssertionError ):
            self._responses_for( result, 1 )


class TestZoneMinderMonitorIdleHeartbeat( _ZmMonitorPipelineBase ):
    """Monitors with no events this cycle still emit an IDLE
    heartbeat so their state stays fresh."""

    def test_idle_for_unseen_monitor_emits_heartbeat(self):
        self._set_monitors([ 1, 2 ])
        self._set_events([])  # no events
        result = self.run_async( self._run() )

        for monitor_id in ( 1, 2 ):
            with self.subTest( monitor_id = monitor_id ):
                responses = self._responses_for( result, monitor_id )
                self.assertEqual( len( responses ), 1 )
                self.assertEqual(
                    responses[ 0 ].value, str( EntityStateValue.IDLE ),
                )
                self.assertIsNone( responses[ 0 ].correlation_role )

    def test_monitor_with_active_event_does_not_get_heartbeat(self):
        # Monitor 1 has an active event; monitor 2 is idle. The
        # heartbeat must fire ONLY on monitor 2.
        self._set_monitors([ 1, 2 ])
        self._set_events([
            _mock_zm_event( 'A', 1, self.start + timedelta( seconds = 1 )),
        ])
        result = self.run_async( self._run() )

        m1 = self._responses_for( result, 1 )
        self.assertEqual( len( m1 ), 1 )
        self.assertEqual( m1[ 0 ].correlation_role, CorrelationRole.START )

        m2 = self._responses_for( result, 2 )
        self.assertEqual( len( m2 ), 1 )
        self.assertIsNone( m2[ 0 ].correlation_role )


class TestZoneMinderMonitorCursorAdvance( _ZmMonitorPipelineBase ):
    """The cursor advance logic is the most-debugged part of the
    monitor and is explicitly preserved across the #351 refactor.
    Re-pin every rule so any future change has to confront these
    invariants."""

    def test_cursor_unchanged_when_no_events(self):
        original = self.monitor._poll_from_datetime
        self._set_events([])
        self.run_async( self._run() )
        self.assertEqual( self.monitor._poll_from_datetime, original )

    def test_cursor_advances_to_latest_end_when_all_closed(self):
        s1 = self.start + timedelta( seconds = 1 )
        e1 = s1 + timedelta( seconds = 10 )
        s2 = self.start + timedelta( seconds = 20 )
        e2 = s2 + timedelta( seconds = 30 )
        self._set_events([
            _mock_zm_event( 'A', 1, s1, e1 ),
            _mock_zm_event( 'B', 1, s2, e2 ),
        ])
        self.run_async( self._run() )
        self.assertEqual( self.monitor._poll_from_datetime, e2 )

    def test_cursor_holds_back_to_earliest_open_when_any_open(self):
        # Holding the cursor at the earliest open event's start
        # ensures the cursor-hold model re-fetches all currently-
        # open events on the next poll. ZM's filter is inclusive
        # (start_time >= cursor), so this works without epsilon
        # arithmetic — see issue #351 for the full filter-semantics
        # context.
        a_open_start = self.start + timedelta( seconds = 5 )
        b_closed_start = self.start + timedelta( seconds = 1 )
        b_closed_end = b_closed_start + timedelta( seconds = 30 )
        self._set_events([
            _mock_zm_event( 'A', 1, a_open_start, None ),
            _mock_zm_event( 'B', 1, b_closed_start, b_closed_end ),
        ])
        self.run_async( self._run() )
        self.assertEqual( self.monitor._poll_from_datetime, a_open_start )
