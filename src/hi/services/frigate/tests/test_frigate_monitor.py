"""Tests for the load-bearing FrigateMonitor pipeline.

The ZM monitor's event-aggregation logic has known pitfalls (multiple
events on the same monitor overwriting each other; cursor advance
when there were no events; open events going stale across polls).
Frigate's monitor uses the same shape — these tests guard the
equivalent invariants here.
"""
import logging
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

from django.test import TestCase

from hi.apps.entity.enums import EntityStateValue
from hi.apps.sense.enums import CorrelationRole

from hi.services.frigate.frigate_converter import FrigateConverter
from hi.services.frigate.frigate_models import FrigateEvent
from hi.services.frigate.frigate_manager import FrigateManager
from hi.services.frigate.monitors import FrigateMonitor

logging.disable( logging.CRITICAL )


def _make_event(
        event_id    : str,
        camera_name : str   = 'front_yard',
        start       : datetime = None,
        end         : datetime = None,
        label       : str   = 'person',
        has_clip    : bool  = True ) -> FrigateEvent:
    if start is None:
        start = datetime( 2026, 5, 20, 12, 0, 0, tzinfo = timezone.utc )
    return FrigateEvent(
        event_id = event_id,
        camera_name = camera_name,
        object_class = label,
        start_datetime = start,
        end_datetime = end,
        has_clip = has_clip,
    )


class TestFrigateEventAggregation( TestCase ):
    """``_aggregate_camera_states`` correctness across the cross-product
    of open / closed event counts. Direct mirror of the ZM monitor's
    aggregation tests — same logic, same pitfalls to guard against.
    """

    def setUp(self):
        self.monitor = FrigateMonitor()
        self.t0 = datetime( 2026, 5, 20, 12, 0, 0, tzinfo = timezone.utc )

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

        front = states[ 'front_yard' ]
        self.assertTrue( front.is_active )
        self.assertIs( front.canonical_event, front_open )
        self.assertCountEqual(
            front.all_events, [ front_open, front_open_later ],
        )

        back = states[ 'back_door' ]
        self.assertTrue( back.is_idle )
        self.assertIs( back.canonical_event, back_closed_later )
        self.assertCountEqual(
            back.all_events, [ back_closed_earlier, back_closed_later ],
        )


class TestFrigateSensorResponseGeneration( TestCase ):
    """One OBJECT_PRESENCE response per aggregated camera state.

    OBJECT_PRESENCE is the single per-camera state the Frigate
    integration tracks — any non-OBJECT_NONE value implies motion is
    currently happening *and* names the class. There is no separate
    MOVEMENT sensor."""

    def setUp(self):
        self.monitor = FrigateMonitor()
        self.t0 = datetime( 2026, 5, 20, 12, 0, 0, tzinfo = timezone.utc )

    def _object_response( self, responses, camera_name = 'front_yard' ):
        for r in responses.values():
            if r.integration_key.integration_name == (
                f'{FrigateManager.OBJECT_PRESENCE_SENSOR_PREFIX}.{camera_name}'
            ):
                return r
            continue
        raise AssertionError(
            f'No OBJECT_PRESENCE response found for {camera_name!r}'
        )

    def test_active_state_emits_object_class_with_start_correlation(self):
        opened = _make_event( event_id = '99', start = self.t0, label = 'person' )
        states = self.monitor._aggregate_camera_states( [ opened ], [] )
        responses = self.monitor._generate_sensor_responses_from_states( states )
        self.assertEqual( len( responses ), 1 )

        obj = self._object_response( responses )
        self.assertEqual( obj.value, str( EntityStateValue.OBJECT_PERSON ) )
        self.assertEqual( obj.correlation_role, CorrelationRole.START )
        self.assertEqual( obj.correlation_id, '99' )
        self.assertEqual( obj.timestamp, opened.start_datetime )
        # has_clip / has_snapshot propagate from FrigateEvent to the
        # SensorResponse; the gateway uses correlation_id (the
        # event_id) to build URLs on demand.
        self.assertTrue( obj.has_event_video_clip )
        self.assertTrue( obj.has_event_video_snapshot )

    def test_active_state_with_no_clip_does_not_advertise_clip(self):
        opened = _make_event(
            event_id = '99', start = self.t0, label = 'person', has_clip = False,
        )
        states = self.monitor._aggregate_camera_states( [ opened ], [] )
        responses = self.monitor._generate_sensor_responses_from_states( states )
        obj = self._object_response( responses )
        self.assertFalse( obj.has_event_video_clip )

    def test_idle_state_emits_object_none_with_end_correlation(self):
        closed = _make_event(
            event_id = '7',
            start = self.t0,
            end = self.t0 + timedelta( seconds = 15 ),
            label = 'person',
        )
        states = self.monitor._aggregate_camera_states( [], [ closed ] )
        responses = self.monitor._generate_sensor_responses_from_states( states )
        self.assertEqual( len( responses ), 1 )

        obj = self._object_response( responses )
        self.assertEqual( obj.value, str( EntityStateValue.OBJECT_NONE ) )
        self.assertEqual( obj.correlation_role, CorrelationRole.END )
        self.assertEqual( obj.correlation_id, '7' )
        self.assertEqual( obj.timestamp, closed.end_datetime )
        # END responses carry the snapshot flag too — the Video Browse
        # page filters to END rows, and a clip-disabled event should
        # still fall back to its captured frame instead of the
        # "video unavailable" placeholder.
        self.assertTrue( obj.has_event_video_snapshot )

    def test_active_state_detail_attrs_carry_event_metadata(self):
        opened = _make_event(
            event_id = '99', start = self.t0, label = 'person',
        )
        opened.score = 0.91
        opened.sub_label = 'jane_doe'
        opened.zones = [ 'driveway', 'walkway' ]
        states = self.monitor._aggregate_camera_states( [ opened ], [] )
        responses = self.monitor._generate_sensor_responses_from_states( states )
        obj = self._object_response( responses )

        from hi.services.frigate.constants import FrigateDetailKeys
        self.assertEqual( obj.detail_attrs[ FrigateDetailKeys.EVENT_ID ], '99' )
        self.assertEqual(
            obj.detail_attrs[ FrigateDetailKeys.OBJECT_CLASS ], 'person',
        )
        self.assertEqual( obj.detail_attrs[ FrigateDetailKeys.SCORE ], '0.91' )
        self.assertEqual(
            obj.detail_attrs[ FrigateDetailKeys.SUB_LABEL ], 'jane_doe',
        )
        self.assertEqual(
            obj.detail_attrs[ FrigateDetailKeys.ZONES ], 'driveway, walkway',
        )
        # Duration is omitted while event is open — value isn't known
        # until the event closes.
        self.assertNotIn(
            FrigateDetailKeys.DURATION_SECS, obj.detail_attrs,
        )

    def test_idle_state_detail_attrs_include_duration(self):
        closed = _make_event(
            event_id = '7',
            start = self.t0,
            end = self.t0 + timedelta( seconds = 15 ),
            label = 'person',
        )
        states = self.monitor._aggregate_camera_states( [], [ closed ] )
        responses = self.monitor._generate_sensor_responses_from_states( states )
        obj = self._object_response( responses )

        from hi.services.frigate.constants import FrigateDetailKeys
        self.assertEqual(
            obj.detail_attrs[ FrigateDetailKeys.DURATION_SECS ], '15.0',
        )

    def test_no_snapshot_event_omits_snapshot_flag(self):
        # Events Frigate flagged ``has_snapshot=False`` for produce
        # responses with ``has_event_video_snapshot=False`` — honest
        # data rather than offering a URL that would 404.
        closed = _make_event(
            event_id = '7',
            start = self.t0,
            end = self.t0 + timedelta( seconds = 15 ),
            label = 'person',
        )
        closed.has_snapshot = False
        states = self.monitor._aggregate_camera_states( [], [ closed ] )
        responses = self.monitor._generate_sensor_responses_from_states( states )
        obj = self._object_response( responses )
        self.assertFalse( obj.has_event_video_snapshot )

    def test_object_presence_uses_canonical_bucket_for_active_state(self):
        """Raw Frigate label runs through the converter table; tests
        for the table itself live in TestFrigateConverter below."""
        opened = _make_event( event_id = '1', start = self.t0, label = 'dog' )
        states = self.monitor._aggregate_camera_states( [ opened ], [] )
        with patch.object(
            self.monitor, 'frigate_manager',
            return_value = Mock( get_event_snapshot_url = Mock( return_value = None )),
        ):
            responses = self.monitor._generate_sensor_responses_from_states( states )
        obj = self._object_response( responses )
        self.assertEqual( obj.value, str( EntityStateValue.OBJECT_ANIMAL ) )

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
        with patch.object(
            self.monitor, 'frigate_manager',
            return_value = Mock( get_event_snapshot_url = Mock( return_value = None )),
        ):
            self.monitor._generate_sensor_responses_from_states( states )

        self.assertIn( 'closed-1', self.monitor._fully_processed_event_ids )
        self.assertNotIn( 'open-1', self.monitor._fully_processed_event_ids )
        self.assertIn( 'open-1', self.monitor._start_processed_event_ids )
        self.assertIn( 'closed-1', self.monitor._start_processed_event_ids )


class TestFrigateNoEventIdleResponse( TestCase ):
    """The no-event-this-cycle response that keeps every camera's
    OBJECT_PRESENCE fresh even when nothing happened in the poll
    window."""

    def setUp(self):
        self.monitor = FrigateMonitor()
        self.now = datetime( 2026, 5, 20, 12, 0, 0, tzinfo = timezone.utc )

    def test_uses_object_presence_key_with_object_none_value(self):
        resp = self.monitor._create_object_presence_sensor_response(
            camera_name = 'driveway',
            value = FrigateConverter.OBJECT_NONE_VALUE,
            timestamp = self.now,
        )
        self.assertEqual( resp.value, str( EntityStateValue.OBJECT_NONE ) )
        self.assertEqual( resp.timestamp, self.now )
        self.assertEqual(
            resp.integration_key.integration_name,
            f'{FrigateManager.OBJECT_PRESENCE_SENSOR_PREFIX}.driveway',
        )

    def test_no_correlation_on_unseen_cycle_response(self):
        """No correlation id on the no-event-this-cycle response —
        there's no event to pair with."""
        resp = self.monitor._create_object_presence_sensor_response(
            camera_name = 'driveway',
            value = FrigateConverter.OBJECT_NONE_VALUE,
            timestamp = self.now,
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

    def test_parses_has_clip_field(self):
        # Real Frigate emits has_clip / has_snapshot booleans per
        # event; HI carries them through to gate UI playback
        # affordances.
        api_dict = {
            'id': '42', 'camera': 'front_yard', 'label': 'person',
            'start_time': 1747750800.0, 'has_clip': False, 'has_snapshot': True,
        }
        event = FrigateEvent.from_api_dict( api_dict )
        self.assertFalse( event.has_clip )
        self.assertTrue( event.has_snapshot )

    def test_has_clip_defaults_to_true_when_absent(self):
        # Older Frigate responses don't carry the boolean. Default to
        # True (Frigate's own startup default).
        event = FrigateEvent.from_api_dict({
            'id': '42', 'camera': 'front_yard', 'label': 'person',
            'start_time': 1747750800.0,
        })
        self.assertTrue( event.has_clip )

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
        self.monitor._was_initialized = True
        self.start = datetime( 2026, 5, 20, 12, 0, 0, tzinfo = timezone.utc )
        self.monitor._poll_from_datetime = self.start

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
            return [ { 'name': n, 'config': {} } for n in names ]

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
        # One OBJECT_PRESENCE response for the camera.
        self.assertEqual( len( responses ), 1 )
        self.assertIn( 'reposted', self.monitor._fully_processed_event_ids )

        # Even though the API returns the same closed event again on
        # the next poll, it's filtered out by the fully-processed cache
        # → no event-driven response. The idle-for-unseen pass emits
        # an OBJECT_NONE response for the camera if it's still in
        # the camera list.
        self._set_cameras([ 'front_yard' ])
        responses = asyncio.run( self._run_process_events() )
        self.assertEqual( len( responses ), 1 )
        obj = next(
            r for r in responses.values()
            if r.integration_key.integration_name.startswith(
                FrigateManager.OBJECT_PRESENCE_SENSOR_PREFIX + '.'
            )
        )
        self.assertEqual( obj.value, str( EntityStateValue.OBJECT_NONE ) )
        # No correlation on the unseen-cycle idle response.
        self.assertIsNone( obj.correlation_role )

    def test_idle_response_for_camera_with_no_events_this_cycle(self):
        import asyncio
        self._set_cameras([ 'driveway', 'back_door' ])
        responses = asyncio.run( self._run_process_events() )
        # Both cameras produced no events → both get OBJECT_NONE.
        self.assertEqual( len( responses ), 2 )
        for resp in responses.values():
            name = resp.integration_key.integration_name
            self.assertTrue(
                name.startswith( FrigateManager.OBJECT_PRESENCE_SENSOR_PREFIX + '.' )
            )
            self.assertEqual( resp.value, str( EntityStateValue.OBJECT_NONE ) )
            self.assertIsNone( resp.correlation_role )
            continue


    def test_open_event_overrides_idle_for_unseen(self):
        """A camera with an open event gets a class-bearing
        OBJECT_PRESENCE — the idle-for-unseen pass must NOT clobber
        it with OBJECT_NONE."""
        import asyncio
        self._set_events([
            { 'id': '7', 'camera': 'front_yard', 'label': 'person',
              'start_time': self.start.timestamp(),
              'end_time': None },
        ])
        self._set_cameras([ 'front_yard', 'back_door' ])
        responses = asyncio.run( self._run_process_events() )

        # 2 cameras × 1 OBJECT_PRESENCE response each = 2 responses.
        self.assertEqual( len( responses ), 2 )

        def _find( camera ):
            target = f'{FrigateManager.OBJECT_PRESENCE_SENSOR_PREFIX}.{camera}'
            for r in responses.values():
                if r.integration_key.integration_name == target:
                    return r
                continue
            raise AssertionError( f'No response for {target}' )

        # front_yard had an open event → OBJECT_PERSON + START correlation.
        front_obj = _find( 'front_yard' )
        self.assertEqual( front_obj.value, str( EntityStateValue.OBJECT_PERSON ) )
        self.assertEqual( front_obj.correlation_role, CorrelationRole.START )
        self.assertEqual( front_obj.correlation_id, '7' )

        # back_door had no events → OBJECT_NONE with no correlation.
        back_obj = _find( 'back_door' )
        self.assertEqual( back_obj.value, str( EntityStateValue.OBJECT_NONE ) )
        self.assertIsNone( back_obj.correlation_role )


class TestFrigateConverterObjectClassMapping( TestCase ):
    """Raw Frigate label → canonical OBJECT_PRESENCE bucket. The
    table is integration-specific (no other integration maps to this
    enum yet) but the contract is stable: unknown labels bucket into
    ``OBJECT_OTHER`` rather than disappearing as ``OBJECT_NONE``."""

    def test_person_maps_to_object_person(self):
        self.assertEqual(
            FrigateConverter.to_canonical_object_class( 'person' ),
            str( EntityStateValue.OBJECT_PERSON ),
        )

    def test_vehicles_bucket_to_object_car(self):
        for raw in [ 'car', 'truck', 'bus', 'motorcycle', 'bicycle' ]:
            with self.subTest( raw = raw ):
                self.assertEqual(
                    FrigateConverter.to_canonical_object_class( raw ),
                    str( EntityStateValue.OBJECT_CAR ),
                )
            continue

    def test_animals_bucket_to_object_animal(self):
        for raw in [ 'dog', 'cat', 'bird', 'horse', 'cow', 'bear',
                     'deer', 'raccoon', 'fox', 'squirrel', 'rabbit' ]:
            with self.subTest( raw = raw ):
                self.assertEqual(
                    FrigateConverter.to_canonical_object_class( raw ),
                    str( EntityStateValue.OBJECT_ANIMAL ),
                )
            continue

    def test_package_maps_to_object_package(self):
        self.assertEqual(
            FrigateConverter.to_canonical_object_class( 'package' ),
            str( EntityStateValue.OBJECT_PACKAGE ),
        )

    def test_unknown_label_falls_through_to_object_other(self):
        """Custom-model classes that nobody's bucketed yet still
        register as "something is here" rather than disappearing into
        OBJECT_NONE."""
        for raw in [ 'unicorn', 'drone', 'frog', '' ]:
            with self.subTest( raw = raw ):
                self.assertEqual(
                    FrigateConverter.to_canonical_object_class( raw ),
                    str( EntityStateValue.OBJECT_OTHER ),
                )
            continue

    def test_label_lookup_is_case_insensitive(self):
        self.assertEqual(
            FrigateConverter.to_canonical_object_class( 'PERSON' ),
            str( EntityStateValue.OBJECT_PERSON ),
        )
        self.assertEqual(
            FrigateConverter.to_canonical_object_class( 'Dog' ),
            str( EntityStateValue.OBJECT_ANIMAL ),
        )


