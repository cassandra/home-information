"""Tests for the load-bearing FrigateMonitor pipeline.

The ZM monitor's event-aggregation logic has known pitfalls (multiple
events on the same monitor overwriting each other; cursor advance
when there were no events; open events going stale across polls).
Frigate's monitor uses the same shape — these tests guard the
equivalent invariants here.
"""
import logging
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

from django.test import TestCase

from hi.apps.entity.enums import EntityStateValue
from hi.apps.sense.enums import CorrelationRole

from hi.services.frigate.frigate_models import FrigateEvent
from hi.services.frigate.frigate_manager import FrigateManager
from hi.services.frigate.monitors import FrigateMonitor

logging.disable( logging.CRITICAL )


def _make_event(
        event_id    : str,
        camera_name : str   = 'front_yard',
        start       : datetime = None,
        end         : datetime = None,
        label       : str   = 'person' ) -> FrigateEvent:
    if start is None:
        start = datetime( 2026, 5, 20, 12, 0, 0, tzinfo = timezone.utc )
    return FrigateEvent(
        event_id = event_id,
        camera_name = camera_name,
        object_class = label,
        start_datetime = start,
        end_datetime = end,
    )


class TestFrigateEventAggregation( TestCase ):
    """``_aggregate_camera_states`` correctness across the cross-product
    of open / closed event counts. Direct mirror of the ZM monitor's
    aggregation tests — same logic, same pitfalls to guard against.
    """

    def setUp(self):
        self.monitor = FrigateMonitor()
        self.t0 = datetime( 2026, 5, 20, 12, 0, 0, tzinfo = timezone.utc )

    # ---- single-camera permutations: open/closed × {none, one, many}

    def test_no_events_yields_empty_aggregation(self):
        self.assertEqual(
            self.monitor._aggregate_camera_states( [], [] ),
            {},
        )

    def test_one_closed_event_yields_idle(self):
        closed = _make_event(
            event_id = '1',
            start = self.t0,
            end = self.t0 + timedelta( seconds = 30 ),
        )
        states = self.monitor._aggregate_camera_states( [], [ closed ] )
        self.assertEqual( set( states.keys() ), { 'front_yard' } )
        s = states[ 'front_yard' ]
        self.assertTrue( s.is_idle )
        self.assertIs( s.canonical_event, closed )
        self.assertEqual( s.effective_timestamp, closed.end_datetime )

    def test_multiple_closed_events_pick_latest_end_as_canonical(self):
        earlier = _make_event(
            event_id = '1',
            start = self.t0,
            end = self.t0 + timedelta( seconds = 10 ),
        )
        later = _make_event(
            event_id = '2',
            start = self.t0 + timedelta( seconds = 20 ),
            end = self.t0 + timedelta( seconds = 60 ),
        )
        states = self.monitor._aggregate_camera_states( [], [ earlier, later ] )
        s = states[ 'front_yard' ]
        self.assertTrue( s.is_idle )
        self.assertIs( s.canonical_event, later )
        self.assertEqual( s.effective_timestamp, later.end_datetime )
        # All events make it onto the aggregated state for cache bookkeeping.
        self.assertCountEqual( s.all_events, [ earlier, later ] )

    def test_one_open_event_yields_active(self):
        opened = _make_event( event_id = '1', start = self.t0 )
        states = self.monitor._aggregate_camera_states( [ opened ], [] )
        s = states[ 'front_yard' ]
        self.assertTrue( s.is_active )
        self.assertIs( s.canonical_event, opened )
        self.assertEqual( s.effective_timestamp, opened.start_datetime )

    def test_open_event_wins_over_closed_event_on_same_camera(self):
        """Even one open event keeps the camera ACTIVE — closed events
        on the same camera don't downgrade it."""
        opened = _make_event(
            event_id = '2',
            start = self.t0 + timedelta( seconds = 30 ),
        )
        closed = _make_event(
            event_id = '1',
            start = self.t0,
            end = self.t0 + timedelta( seconds = 10 ),
        )
        states = self.monitor._aggregate_camera_states( [ opened ], [ closed ] )
        s = states[ 'front_yard' ]
        self.assertTrue( s.is_active )
        self.assertIs( s.canonical_event, opened )

    def test_multiple_open_events_pick_earliest_start_as_canonical(self):
        later_open = _make_event(
            event_id = '2',
            start = self.t0 + timedelta( seconds = 30 ),
        )
        earlier_open = _make_event(
            event_id = '1',
            start = self.t0,
        )
        states = self.monitor._aggregate_camera_states(
            [ later_open, earlier_open ], [],
        )
        s = states[ 'front_yard' ]
        self.assertTrue( s.is_active )
        self.assertIs( s.canonical_event, earlier_open )
        self.assertEqual( s.effective_timestamp, earlier_open.start_datetime )

    def test_multiple_cameras_aggregate_independently(self):
        """Regression for the original ZM bug: same-camera events used
        to overwrite each other; here we verify independent aggregation
        across cameras AND multiple events on the same camera collapse
        to one entry without losing the canonical-event picks."""
        front_open = _make_event(
            event_id = 'A1', camera_name = 'front_yard', start = self.t0,
        )
        front_open_later = _make_event(
            event_id = 'A2', camera_name = 'front_yard',
            start = self.t0 + timedelta( seconds = 5 ),
        )
        back_closed_earlier = _make_event(
            event_id = 'B1', camera_name = 'back_door',
            start = self.t0,
            end = self.t0 + timedelta( seconds = 10 ),
        )
        back_closed_later = _make_event(
            event_id = 'B2', camera_name = 'back_door',
            start = self.t0 + timedelta( seconds = 20 ),
            end = self.t0 + timedelta( seconds = 40 ),
        )
        states = self.monitor._aggregate_camera_states(
            [ front_open, front_open_later ],
            [ back_closed_earlier, back_closed_later ],
        )
        self.assertEqual( set( states.keys() ), { 'front_yard', 'back_door' } )

        # Front: ACTIVE, earliest-start open is canonical.
        front = states[ 'front_yard' ]
        self.assertTrue( front.is_active )
        self.assertIs( front.canonical_event, front_open )
        self.assertCountEqual(
            front.all_events, [ front_open, front_open_later ],
        )

        # Back: IDLE, latest-end closed is canonical.
        back = states[ 'back_door' ]
        self.assertTrue( back.is_idle )
        self.assertIs( back.canonical_event, back_closed_later )
        self.assertCountEqual(
            back.all_events, [ back_closed_earlier, back_closed_later ],
        )


class TestFrigateSensorResponseGeneration( TestCase ):

    def setUp(self):
        self.monitor = FrigateMonitor()
        self.t0 = datetime( 2026, 5, 20, 12, 0, 0, tzinfo = timezone.utc )

    def test_active_state_emits_active_response_with_start_correlation(self):
        opened = _make_event( event_id = '99', start = self.t0 )
        states = self.monitor._aggregate_camera_states( [ opened ], [] )
        responses = self.monitor._generate_sensor_responses_from_states( states )
        self.assertEqual( len( responses ), 1 )
        ( resp, ) = responses.values()
        self.assertEqual( resp.value, str( EntityStateValue.ACTIVE ) )
        self.assertEqual( resp.correlation_role, CorrelationRole.START )
        self.assertEqual( resp.correlation_id, '99' )
        self.assertEqual( resp.timestamp, opened.start_datetime )
        # Integration key uses the MOVEMENT_SENSOR_PREFIX scheme.
        self.assertEqual(
            resp.integration_key.integration_name,
            f'{FrigateManager.MOVEMENT_SENSOR_PREFIX}.front_yard',
        )

    def test_idle_state_emits_idle_response_with_end_correlation(self):
        closed = _make_event(
            event_id = '7',
            start = self.t0,
            end = self.t0 + timedelta( seconds = 15 ),
        )
        states = self.monitor._aggregate_camera_states( [], [ closed ] )
        responses = self.monitor._generate_sensor_responses_from_states( states )
        ( resp, ) = responses.values()
        self.assertEqual( resp.value, str( EntityStateValue.IDLE ) )
        self.assertEqual( resp.correlation_role, CorrelationRole.END )
        self.assertEqual( resp.correlation_id, '7' )
        self.assertEqual( resp.timestamp, closed.end_datetime )

    def test_event_cache_updates_correctly(self):
        """Closed events go to fully_processed (won't be re-emitted);
        all events go to start_processed."""
        opened = _make_event(
            event_id = 'open-1', start = self.t0,
        )
        closed = _make_event(
            event_id = 'closed-1',
            camera_name = 'back_door',
            start = self.t0,
            end = self.t0 + timedelta( seconds = 5 ),
        )
        states = self.monitor._aggregate_camera_states( [ opened ], [ closed ] )
        self.monitor._generate_sensor_responses_from_states( states )

        # closed-1 in fully_processed → won't be re-emitted next poll.
        self.assertIn( 'closed-1', self.monitor._fully_processed_event_ids )
        # open-1 NOT in fully_processed → cursor + skip-check will let
        # us see it again next poll so we can detect when it closes.
        self.assertNotIn( 'open-1', self.monitor._fully_processed_event_ids )
        # Both in start_processed (symmetric with ZM's bookkeeping).
        self.assertIn( 'open-1', self.monitor._start_processed_event_ids )
        self.assertIn( 'closed-1', self.monitor._start_processed_event_ids )


class TestFrigateIdleSensorResponse( TestCase ):
    """The no-event-this-cycle IDLE response that keeps every camera's
    state fresh even when nothing happened in the poll window."""

    def setUp(self):
        self.monitor = FrigateMonitor()
        self.now = datetime( 2026, 5, 20, 12, 0, 0, tzinfo = timezone.utc )

    def test_idle_response_uses_camera_movement_key(self):
        resp = self.monitor._create_idle_sensor_response(
            camera_name = 'driveway', timestamp = self.now,
        )
        self.assertEqual( resp.value, str( EntityStateValue.IDLE ) )
        self.assertEqual( resp.timestamp, self.now )
        self.assertEqual(
            resp.integration_key.integration_name,
            f'{FrigateManager.MOVEMENT_SENSOR_PREFIX}.driveway',
        )

    def test_idle_response_has_no_correlation(self):
        """No correlation id on the no-event-this-cycle IDLE — there's
        no event to pair with."""
        resp = self.monitor._create_idle_sensor_response(
            camera_name = 'driveway', timestamp = self.now,
        )
        self.assertIsNone( resp.correlation_role )
        self.assertIsNone( resp.correlation_id )


class TestFrigateEventFromApiDict( TestCase ):
    """``FrigateEvent.from_api_dict`` is the wire-to-model boundary
    where bad payloads need to surface with a useful error."""

    def test_parses_open_event(self):
        api_dict = {
            'id': '42',
            'camera': 'front_yard',
            'label': 'person',
            'start_time': 1747750800.0,
            'end_time': None,
            'top_score': 0.91,
            'sub_label': None,
            'zones': [ 'driveway' ],
        }
        event = FrigateEvent.from_api_dict( api_dict )
        self.assertEqual( event.event_id, '42' )
        self.assertEqual( event.camera_name, 'front_yard' )
        self.assertEqual( event.object_class, 'person' )
        self.assertTrue( event.is_open )
        self.assertFalse( event.is_closed )
        self.assertEqual( event.score, 0.91 )
        self.assertEqual( event.zones, [ 'driveway' ] )

    def test_parses_closed_event(self):
        start_epoch = 1747750800.0
        end_epoch = start_epoch + 30
        api_dict = {
            'id': '42',
            'camera': 'front_yard',
            'label': 'car',
            'start_time': start_epoch,
            'end_time': end_epoch,
        }
        event = FrigateEvent.from_api_dict( api_dict )
        self.assertTrue( event.is_closed )
        self.assertFalse( event.is_open )
        self.assertEqual(
            event.start_datetime,
            datetime.fromtimestamp( start_epoch, tz = timezone.utc ),
        )
        self.assertEqual(
            event.end_datetime,
            datetime.fromtimestamp( end_epoch, tz = timezone.utc ),
        )

    def test_missing_required_field_raises(self):
        with self.assertRaises( ValueError ) as ctx:
            FrigateEvent.from_api_dict({
                'id': '42', 'camera': 'front_yard',
                # missing label + start_time
            })
        self.assertIn( 'missing required field', str( ctx.exception ) )


class TestFrigateProcessEventsCursor( TestCase ):
    """The cursor-advance invariants — the bit that took the most
    debugging on the ZM side.
    """

    def setUp(self):
        self.monitor = FrigateMonitor()
        # _process_events relies on these being set; bypass the
        # async _initialize path for these focused tests.
        self.monitor._was_initialized = True
        self.start = datetime( 2026, 5, 20, 12, 0, 0, tzinfo = timezone.utc )
        self.monitor._poll_from_datetime = self.start

        # Mock the manager with both async shims so the monitor can
        # call get_events_async / get_cameras_async.
        self.mock_manager = Mock( spec = FrigateManager )

        async def empty_events( after = None, limit = None ):
            return []

        async def empty_cameras():
            return []

        self.mock_manager.get_events_async = Mock( side_effect = empty_events )
        self.mock_manager.get_cameras_async = Mock( side_effect = empty_cameras )
        self.monitor._frigate_manager = self.mock_manager

    async def _run_process_events(self):
        return await self.monitor._process_events()

    def _set_events(self, events_api_list):
        async def fake_events( after = None, limit = None ):
            return events_api_list

        self.mock_manager.get_events_async = Mock( side_effect = fake_events )

    def _set_cameras(self, names):
        async def fake_cameras():
            return [ { 'name': n } for n in names ]

        self.mock_manager.get_cameras_async = Mock( side_effect = fake_cameras )

    def test_cursor_unchanged_when_no_events(self):
        """With no events, advancing the cursor risks missing an event
        that started right after the request — invariant from the ZM
        monitor."""
        import asyncio
        asyncio.run( self._run_process_events() )
        self.assertEqual( self.monitor._poll_from_datetime, self.start )

    def test_cursor_advances_to_latest_end_when_all_closed(self):
        import asyncio
        end_1 = self.start + timedelta( seconds = 10 )
        end_2 = self.start + timedelta( seconds = 30 )
        self._set_events([
            { 'id': '1', 'camera': 'front_yard', 'label': 'person',
              'start_time': self.start.timestamp(),
              'end_time': end_1.timestamp() },
            { 'id': '2', 'camera': 'front_yard', 'label': 'person',
              'start_time': (self.start + timedelta(seconds=15)).timestamp(),
              'end_time': end_2.timestamp() },
        ])
        asyncio.run( self._run_process_events() )
        # Cursor sits at the latest closed event's end_time.
        self.assertEqual( self.monitor._poll_from_datetime, end_2 )

    def test_cursor_holds_back_to_earliest_open_when_any_open(self):
        import asyncio
        open_start = self.start + timedelta( seconds = 5 )
        closed_end = self.start + timedelta( seconds = 30 )
        self._set_events([
            { 'id': '1', 'camera': 'front_yard', 'label': 'person',
              'start_time': self.start.timestamp(),
              'end_time': closed_end.timestamp() },
            { 'id': '2', 'camera': 'front_yard', 'label': 'person',
              'start_time': open_start.timestamp(),
              'end_time': None },  # open
        ])
        asyncio.run( self._run_process_events() )
        # Cursor held back to the open event's start so the next poll
        # still sees it until it closes.
        self.assertEqual( self.monitor._poll_from_datetime, open_start )

    def test_fully_processed_event_is_skipped_on_next_poll(self):
        import asyncio
        end_t = self.start + timedelta( seconds = 10 )
        api_event = {
            'id': 'reposted', 'camera': 'front_yard', 'label': 'person',
            'start_time': self.start.timestamp(),
            'end_time': end_t.timestamp(),
        }

        self._set_events([ api_event ])
        responses = asyncio.run( self._run_process_events() )
        self.assertEqual( len( responses ), 1 )
        self.assertIn( 'reposted', self.monitor._fully_processed_event_ids )

        # Even though the API returns the same closed event again on
        # the next poll, it's filtered out by the fully-processed cache
        # → no new MOVEMENT response, just an IDLE-for-unseen for the
        # camera if the camera list still mentions it.
        self._set_cameras([ 'front_yard' ])
        responses = asyncio.run( self._run_process_events() )
        # The only response should be the no-event-this-cycle IDLE
        # for the camera.
        ( only_resp, ) = responses.values()
        self.assertEqual( only_resp.value, str( EntityStateValue.IDLE ) )
        self.assertIsNone( only_resp.correlation_role )

    def test_idle_response_for_camera_with_no_events_this_cycle(self):
        import asyncio
        self._set_cameras([ 'driveway', 'back_door' ])
        responses = asyncio.run( self._run_process_events() )
        # Both cameras produced no events → both get IDLE responses.
        self.assertEqual( len( responses ), 2 )
        for resp in responses.values():
            self.assertEqual( resp.value, str( EntityStateValue.IDLE ) )
            self.assertIsNone( resp.correlation_role )
            continue

    def test_open_event_overrides_idle_for_unseen(self):
        """A camera with an open event gets ACTIVE — the
        idle-for-unseen pass must NOT clobber it."""
        import asyncio
        self._set_events([
            { 'id': '7', 'camera': 'front_yard', 'label': 'person',
              'start_time': self.start.timestamp(),
              'end_time': None },
        ])
        self._set_cameras([ 'front_yard', 'back_door' ])
        responses = asyncio.run( self._run_process_events() )

        # Two cameras → two responses, but front_yard is ACTIVE
        # (its event drove the state) and back_door is IDLE.
        by_camera = {
            r.integration_key.integration_name.rsplit( '.', 1 )[ -1 ]: r
            for r in responses.values()
        }
        self.assertEqual( by_camera[ 'front_yard' ].value,
                          str( EntityStateValue.ACTIVE ))
        self.assertEqual( by_camera[ 'front_yard' ].correlation_id, '7' )
        self.assertEqual( by_camera[ 'back_door' ].value,
                          str( EntityStateValue.IDLE ))
        self.assertIsNone( by_camera[ 'back_door' ].correlation_id )
