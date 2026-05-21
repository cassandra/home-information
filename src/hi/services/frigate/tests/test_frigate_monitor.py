"""Tests for the FrigateMonitor polling pipeline.

Frigate's ``?after=T`` filters strictly on ``start_time > T``, so
once the cursor advances past an event's start_time that event is
invisible to cursor scans even after it closes. The pipeline mixes
a monotonic cursor scan for new events with a per-id direct refresh
for events currently in the open-tracking set. These tests cover
each phase's invariants and the open→closed transition that the
cursor-only approach drops.
"""
import logging
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

from django.test import TestCase

from hi.apps.entity.enums import EntityStateValue
from hi.apps.sense.enums import CorrelationRole
from hi.testing.async_task_utils import AsyncTaskFastTestCase

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


class TestFrigateEventDetailAttrs( TestCase ):
    """``_build_event_detail_attrs`` packs a FrigateEvent's metadata
    into the dict that's persisted on SensorResponse.detail_attrs and
    surfaced in the event-detail UI. The keys are wire-stable (see
    FrigateDetailKeys docstring) so regressions need a guard here."""

    def setUp(self):
        self.monitor = FrigateMonitor()
        self.t0 = datetime( 2026, 5, 20, 12, 0, 0, tzinfo = timezone.utc )

    def test_open_event_packs_metadata_without_duration(self):
        opened = _make_event(
            event_id = '99', start = self.t0, label = 'person',
        )
        opened.score = 0.91
        opened.sub_label = 'jane_doe'
        opened.zones = [ 'driveway', 'walkway' ]

        attrs = self.monitor._build_event_detail_attrs(
            event = opened, is_closed = False,
        )
        from hi.services.frigate.constants import FrigateDetailKeys
        self.assertEqual( attrs[ FrigateDetailKeys.EVENT_ID ], '99' )
        self.assertEqual( attrs[ FrigateDetailKeys.OBJECT_CLASS ], 'person' )
        self.assertEqual( attrs[ FrigateDetailKeys.SCORE ], '0.91' )
        self.assertEqual( attrs[ FrigateDetailKeys.SUB_LABEL ], 'jane_doe' )
        self.assertEqual(
            attrs[ FrigateDetailKeys.ZONES ], 'driveway, walkway',
        )
        # Duration is omitted while the event is open — value isn't
        # known until the event closes.
        self.assertNotIn( FrigateDetailKeys.DURATION_SECS, attrs )

    def test_closed_event_includes_duration(self):
        closed = _make_event(
            event_id = '7',
            start = self.t0,
            end = self.t0 + timedelta( seconds = 15 ),
        )
        attrs = self.monitor._build_event_detail_attrs(
            event = closed, is_closed = True,
        )
        from hi.services.frigate.constants import FrigateDetailKeys
        self.assertEqual( attrs[ FrigateDetailKeys.DURATION_SECS ], '15.0' )


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


class _PipelineTestBase( AsyncTaskFastTestCase ):
    """Shared scaffolding for the cursor + per-id refresh pipeline.

    Frigate's ``?after=T`` filters strictly on ``start_time > T``, so
    the cursor advances monotonically over each event's start_time and
    open events are tracked by id and refreshed via direct fetch. These
    tests verify each phase's invariants in isolation and across the
    open→closed transition.
    """

    def setUp(self):
        self.monitor = FrigateMonitor()
        self.monitor._was_initialized = True
        self.start = datetime( 2026, 5, 20, 12, 0, 0, tzinfo = timezone.utc )
        self.monitor._poll_cursor_datetime = self.start
        self.monitor._tracked_events = {}

        # Pin ``datetimeproxy.now`` to ``self.start`` so phase-2 age
        # math operates on test-relative time. Without this, real
        # wall-clock vs ``self.start`` is ~years apart and seeded
        # open events always look aged-out.
        self._now_patcher = patch(
            'hi.services.frigate.monitors.datetimeproxy.now',
            return_value = self.start,
        )
        self._now_patcher.start()
        self.addCleanup( self._now_patcher.stop )

        self.mock_manager = Mock( spec = FrigateManager )

        async def empty_events( after = None, limit = None ):
            return []

        async def empty_cameras():
            return []

        async def event_not_found( event_id ):
            from django.http import Http404
            raise Http404( event_id )

        self.mock_manager.get_events_async = Mock( side_effect = empty_events )
        self.mock_manager.get_cameras_async = Mock( side_effect = empty_cameras )
        self.mock_manager.get_event_async = Mock( side_effect = event_not_found )
        self.monitor._frigate_manager = self.mock_manager
        return

    def _set_events(self, events_api_list):
        async def fake_events( after = None, limit = None ):
            return events_api_list

        self.mock_manager.get_events_async = Mock( side_effect = fake_events )

    def _set_event_by_id(self, by_id):
        async def fake_event( event_id ):
            from django.http import Http404
            if event_id not in by_id:
                raise Http404( event_id )
            return by_id[ event_id ]

        self.mock_manager.get_event_async = Mock( side_effect = fake_event )

    def _set_cameras(self, names):
        async def fake_cameras():
            return [ { 'name': n, 'config': {} } for n in names ]

        self.mock_manager.get_cameras_async = Mock( side_effect = fake_cameras )

    def _api_event(
            self,
            event_id    = '1',
            camera_name = 'front_yard',
            label       = 'person',
            start       = None,
            end         = None,
            has_clip    = True,
            has_snapshot = True,
    ):
        if start is None:
            start = self.start + timedelta( seconds = 1 )
        return {
            'id': event_id,
            'camera': camera_name,
            'label': label,
            'start_time': start.timestamp(),
            'end_time': end.timestamp() if end is not None else None,
            'has_clip': has_clip,
            'has_snapshot': has_snapshot,
        }

    def _find_response(self, responses, camera_name):
        """Return the sole response for the given camera. Asserts the
        list has exactly one entry — tests that legitimately expect a
        multi-response cycle must use ``_find_responses`` and assert
        on the full list explicitly."""
        response_list = self._find_responses( responses, camera_name )
        if len( response_list ) != 1:
            raise AssertionError(
                f'Expected exactly one response for {camera_name!r}, '
                f'got {len(response_list)}: {response_list}'
            )
        return response_list[ 0 ]

    def _find_responses(self, responses, camera_name):
        target = f'{FrigateManager.OBJECT_PRESENCE_SENSOR_PREFIX}.{camera_name}'
        for integration_key, response_list in responses.items():
            if integration_key.integration_name == target:
                return response_list
            continue
        raise AssertionError( f'No OBJECT_PRESENCE responses for {camera_name!r}' )

    async def _run(self):
        return await self.monitor._process_events()


class TestFrigateScanNewEventsPhase( _PipelineTestBase ):
    """Phase 1: ``?after=cursor`` scan.

    Cursor advance is monotonic on ``start_time``. Each event seen
    here is brand-new to us; START is always emitted, END too if the
    event was already closed when first observed (lifetime shorter
    than poll interval)."""

    def test_cursor_unchanged_when_no_events(self):
        self.run_async( self._run() )
        self.assertEqual( self.monitor._poll_cursor_datetime, self.start )

    def test_cursor_advances_to_latest_start_time(self):
        s1 = self.start + timedelta( seconds = 5 )
        s2 = self.start + timedelta( seconds = 20 )
        self._set_events([
            self._api_event( event_id = '1', start = s1 ),
            self._api_event( event_id = '2', start = s2,
                             end = s2 + timedelta( seconds = 10 )),
        ])
        # Phase 2 will refresh id '1'; pretend Frigate still has it.
        self._set_event_by_id({
            '1': self._api_event( event_id = '1', start = s1 ),
        })
        self.run_async( self._run() )
        self.assertEqual( self.monitor._poll_cursor_datetime, s2 )

    def test_open_event_enters_tracked_set_and_emits_start(self):
        """The open→closed transition bug fix: after the open event
        is seen once, the cursor advances PAST its start_time. Future
        cursor scans won't return it — phase 2 must track it by id."""
        open_start = self.start + timedelta( seconds = 5 )
        self._set_events([
            self._api_event( event_id = 'A', start = open_start, end = None ),
        ])
        self._set_event_by_id({
            'A': self._api_event( event_id = 'A', start = open_start, end = None ),
        })
        responses = self.run_async( self._run() )

        self.assertIn( 'A', self.monitor._tracked_events )
        self.assertEqual( self.monitor._poll_cursor_datetime, open_start )

        obj = self._find_response( responses, 'front_yard' )
        self.assertEqual( obj.value, str( EntityStateValue.OBJECT_PERSON ) )
        self.assertEqual( obj.correlation_role, CorrelationRole.START )
        self.assertEqual( obj.correlation_id, 'A' )

    def test_open_and_closed_within_one_cycle_emits_both_rows(self):
        """Lifetime shorter than poll interval: a single scan returns
        the event already-closed. Both START and END must travel in
        the per-key response list — the SensorResponseManager records
        each as its own history row and transition."""
        s = self.start + timedelta( seconds = 5 )
        e = s + timedelta( seconds = 1 )
        self._set_events([
            self._api_event( event_id = 'X', start = s, end = e ),
        ])
        responses = self.run_async( self._run() )

        self.assertNotIn( 'X', self.monitor._tracked_events )
        response_list = self._find_responses( responses, 'front_yard' )
        roles = [ r.correlation_role for r in response_list ]
        self.assertEqual(
            roles, [ CorrelationRole.START, CorrelationRole.END ],
        )
        self.assertTrue(
            all( r.correlation_id == 'X' for r in response_list ),
        )

    def test_malformed_event_payload_is_skipped(self):
        # Use an open event for 'good' so the test exercises the
        # malformed-skip path without also producing a START+END pair
        # that would obscure the assertion.
        s = self.start + timedelta( seconds = 5 )
        self._set_events([
            { 'id': 'bad', 'camera': 'front_yard' },  # missing label/start
            self._api_event( event_id = 'good', start = s, end = None ),
        ])
        self._set_event_by_id({
            'good': self._api_event( event_id = 'good', start = s, end = None ),
        })
        responses = self.run_async( self._run() )
        self.assertEqual(
            self._find_response( responses, 'front_yard' ).correlation_id,
            'good',
        )

    def test_cursor_does_not_regress_when_event_returned_below_cursor(self):
        """Defensive: if upstream ever serves an event with
        ``start_time <= cursor`` (Frigate bug, replayed payload),
        the cursor must not move backward."""
        # Advance the cursor first so we have a meaningful "above".
        ahead = self.start + timedelta( seconds = 100 )
        self.monitor._poll_cursor_datetime = ahead

        # Return an event with start_time well below the cursor.
        stale_start = self.start + timedelta( seconds = 5 )
        self._set_events([
            self._api_event( event_id = 'stale', start = stale_start,
                             end = stale_start + timedelta( seconds = 1 )),
        ])
        self.run_async( self._run() )
        self.assertEqual( self.monitor._poll_cursor_datetime, ahead )

    def test_duplicate_id_in_tracked_events_is_skipped(self):
        """Cursor is monotonic so phase 1 shouldn't see an id that's
        already in ``_tracked_events`` — but if it does (re-served by
        Frigate after a clock blip), the tracked event must not be
        replaced and no duplicate START must be emitted."""
        from hi.services.frigate.frigate_models import TrackedFrigateEvent
        existing_start = self.start + timedelta( seconds = 1 )
        existing = FrigateEvent(
            event_id = 'A',
            camera_name = 'front_yard',
            object_class = 'person',
            start_datetime = existing_start,
        )
        original_tracked_event = TrackedFrigateEvent(
            event = existing,
            first_observed_at = self.start,
        )
        self.monitor._tracked_events[ 'A' ] = original_tracked_event

        # Frigate returns the same id again (phase 2 will refresh it,
        # so set the by-id mock too).
        self._set_events([
            self._api_event( event_id = 'A', start = existing_start, end = None ),
        ])
        self._set_event_by_id({
            'A': self._api_event( event_id = 'A', start = existing_start, end = None ),
        })
        self.run_async( self._run() )

        # Tracker object preserved (not replaced) — first_observed_at
        # would have rolled forward otherwise.
        self.assertIs( self.monitor._tracked_events[ 'A' ], original_tracked_event )
        self.assertEqual( original_tracked_event.first_observed_at, self.start )


class TestFrigateRefreshTrackedEventsPhase( _PipelineTestBase ):
    """Phase 2: per-id refresh for events currently in the open set.

    Each refresh is one ``GET /api/events/<id>``. Closed → emit END,
    remove. 404 → force-close. Aged out → force-close. Still open →
    keep, refresh snapshot."""

    def _seed_open(
            self, event_id = 'A', camera = 'front_yard',
            first_observed_at = None,
    ):
        from hi.services.frigate.frigate_models import TrackedFrigateEvent
        if first_observed_at is None:
            first_observed_at = self.start
        start = self.start + timedelta( seconds = 1 )
        event = FrigateEvent(
            event_id = event_id,
            camera_name = camera,
            object_class = 'person',
            start_datetime = start,
        )
        self.monitor._tracked_events[ event_id ] = TrackedFrigateEvent(
            event = event,
            first_observed_at = first_observed_at,
        )
        # Advance cursor past the open event to mirror what phase 1
        # would have done.
        self.monitor._poll_cursor_datetime = start
        return event

    def test_closed_event_emits_end_and_clears_from_open_set(self):
        """The headline bug fix: a previously-open event, now closed
        in Frigate, must emit an END row with correlation_id matching
        the original event."""
        self._seed_open( event_id = 'A' )
        end_dt = self.start + timedelta( seconds = 30 )
        self._set_event_by_id({
            'A': self._api_event(
                event_id = 'A',
                start = self.start + timedelta( seconds = 1 ),
                end = end_dt,
            ),
        })
        responses = self.run_async( self._run() )

        self.assertNotIn( 'A', self.monitor._tracked_events )
        obj = self._find_response( responses, 'front_yard' )
        self.assertEqual( obj.correlation_role, CorrelationRole.END )
        self.assertEqual( obj.correlation_id, 'A' )
        self.assertEqual( obj.value, str( EntityStateValue.OBJECT_NONE ) )
        self.assertEqual( obj.timestamp, end_dt )

    def test_still_open_event_stays_tracked(self):
        self._seed_open( event_id = 'A' )
        self._set_event_by_id({
            'A': self._api_event(
                event_id = 'A',
                start = self.start + timedelta( seconds = 1 ),
                end = None,
            ),
        })
        self.run_async( self._run() )
        self.assertIn( 'A', self.monitor._tracked_events )

    def test_404_force_closes_and_removes(self):
        """Frigate dropped the event (cleared from history) → end the
        correlation pair with a synthesized END so the UI doesn't show
        a dangling start."""
        self._seed_open( event_id = 'gone' )
        self._set_event_by_id({})  # any id → 404
        responses = self.run_async( self._run() )

        self.assertNotIn( 'gone', self.monitor._tracked_events )
        obj = self._find_response( responses, 'front_yard' )
        self.assertEqual( obj.correlation_role, CorrelationRole.END )
        self.assertEqual( obj.correlation_id, 'gone' )

    def test_force_close_timeout_fires_on_aged_open_event(self):
        very_old = self.start - timedelta(
            seconds = self.monitor.MAX_OPEN_EVENT_AGE_SECS + 60,
        )
        self._seed_open( event_id = 'old', first_observed_at = very_old )
        self._set_event_by_id({
            'old': self._api_event(
                event_id = 'old',
                start = self.start + timedelta( seconds = 1 ),
                end = None,
            ),
        })
        responses = self.run_async( self._run() )

        self.assertNotIn( 'old', self.monitor._tracked_events )
        obj = self._find_response( responses, 'front_yard' )
        self.assertEqual( obj.correlation_role, CorrelationRole.END )
        self.assertEqual( obj.correlation_id, 'old' )

    def test_transient_failure_keeps_event_and_does_not_force_close(self):
        """Non-404 failures (network blip, 500) shouldn't force-close
        unless the age timeout has also been crossed. Next cycle
        retries the refresh."""
        self._seed_open( event_id = 'A', first_observed_at = self.start )

        async def boom( event_id ):
            raise ValueError( 'simulated transport failure' )
        self.mock_manager.get_event_async = Mock( side_effect = boom )

        responses = self.run_async( self._run() )
        self.assertIn( 'A', self.monitor._tracked_events )
        # No END emitted for the still-tracked event.
        with self.assertRaises( AssertionError ):
            obj = self._find_response( responses, 'front_yard' )
            self.assertEqual( obj.correlation_role, CorrelationRole.END )

    def test_malformed_refresh_payload_leaves_event_tracked(self):
        """If the direct-fetch returns a payload we can't parse, the
        open event must stay in the tracking set so a later cycle can
        retry — dropping it silently would orphan the START with no
        END pair."""
        self._seed_open( event_id = 'A' )
        # By-id returns a dict missing required fields → from_api_dict
        # raises, and the refresh path logs + continues.
        self._set_event_by_id({
            'A': { 'id': 'A', 'camera': 'front_yard' },  # no label / start_time
        })
        responses = self.run_async( self._run() )
        self.assertIn( 'A', self.monitor._tracked_events )
        # No END emitted for the still-tracked event.
        with self.assertRaises( AssertionError ):
            obj = self._find_response( responses, 'front_yard' )
            self.assertEqual( obj.correlation_role, CorrelationRole.END )


class TestFrigateHeartbeatPhase( _PipelineTestBase ):
    """Phase 3: OBJECT_NONE heartbeat for cameras with no activity
    this cycle and no event in the open set. Without this, a camera
    that's been quiet since startup would never produce a response."""

    def test_idle_camera_gets_object_none_heartbeat(self):
        self._set_cameras([ 'driveway' ])
        responses = self.run_async( self._run() )
        obj = self._find_response( responses, 'driveway' )
        self.assertEqual( obj.value, str( EntityStateValue.OBJECT_NONE ) )
        self.assertIsNone( obj.correlation_role )

    def test_camera_with_open_event_skips_heartbeat(self):
        """A camera that's actively tracking an open event must not
        get an OBJECT_NONE clobber — phase 2's END (or future close)
        is what drives its state."""
        from hi.services.frigate.frigate_models import TrackedFrigateEvent
        event = FrigateEvent(
            event_id = 'A',
            camera_name = 'front_yard',
            object_class = 'person',
            start_datetime = self.start + timedelta( seconds = 1 ),
        )
        self.monitor._tracked_events[ 'A' ] = TrackedFrigateEvent(
            event = event,
            first_observed_at = self.start,
        )
        # Refresh keeps it open.
        self._set_event_by_id({
            'A': self._api_event(
                event_id = 'A',
                start = self.start + timedelta( seconds = 1 ),
                end = None,
            ),
        })
        self._set_cameras([ 'front_yard', 'back_door' ])
        responses = self.run_async( self._run() )

        # back_door gets a heartbeat; front_yard does not get clobbered.
        back = self._find_response( responses, 'back_door' )
        self.assertEqual( back.value, str( EntityStateValue.OBJECT_NONE ) )
        self.assertIsNone( back.correlation_role )
        # front_yard's response should NOT be OBJECT_NONE — Phase 2
        # left it alone (event still open, no END this cycle).
        target = (
            f'{FrigateManager.OBJECT_PRESENCE_SENSOR_PREFIX}.front_yard'
        )
        for integration_key in responses.keys():
            if integration_key.integration_name == target:
                self.fail(
                    'front_yard should not receive a phase-3 heartbeat'
                    ' while it has an open event in the tracking set.'
                )

    def test_camera_active_this_cycle_skips_heartbeat(self):
        """A camera whose START was emitted this cycle (phase 1) must
        not also get a phase-3 OBJECT_NONE."""
        s = self.start + timedelta( seconds = 5 )
        self._set_events([
            self._api_event( event_id = 'A', start = s, end = None ),
        ])
        self._set_event_by_id({
            'A': self._api_event( event_id = 'A', start = s, end = None ),
        })
        self._set_cameras([ 'front_yard' ])
        responses = self.run_async( self._run() )

        obj = self._find_response( responses, 'front_yard' )
        # Phase 1's START survives — not overwritten by an OBJECT_NONE.
        self.assertEqual( obj.correlation_role, CorrelationRole.START )

    def test_camera_list_fetch_failure_does_not_break_pipeline(self):
        """A transient failure on ``get_cameras_async`` must not
        propagate — phases 1 and 2 may have produced legitimate
        responses that should still be delivered, just no heartbeat
        responses this cycle."""
        async def boom():
            raise ValueError( 'simulated camera list failure' )
        self.mock_manager.get_cameras_async = Mock( side_effect = boom )

        # No phase-1 or phase-2 activity either — pipeline must still
        # return a dict without raising.
        result = self.run_async( self._run() )
        self.assertEqual( result, {} )


class TestFrigateOpenCloseTransitionAcrossCycles( _PipelineTestBase ):
    """End-to-end: the bug we're fixing. A typical motion event sees
    its open form on cycle N and its closed form on cycle N+1. The
    old pipeline lost the closure to Frigate's strict ``>`` filter on
    ``start_time``. The new pipeline tracks the event by id."""

    def test_open_then_close_emits_paired_start_and_end_rows(self):
        start_dt = self.start + timedelta( seconds = 5 )
        end_dt = self.start + timedelta( seconds = 30 )

        # Cycle 1: cursor scan returns the open event.
        self._set_events([
            self._api_event( event_id = 'evt', start = start_dt, end = None ),
        ])
        self._set_event_by_id({
            'evt': self._api_event( event_id = 'evt', start = start_dt, end = None ),
        })
        cycle1 = self.run_async( self._run() )
        start_obj = self._find_response( cycle1, 'front_yard' )
        self.assertEqual( start_obj.correlation_role, CorrelationRole.START )
        self.assertEqual( start_obj.correlation_id, 'evt' )

        # Cycle 2: cursor scan returns nothing (cursor has advanced
        # past the event's start_time). Phase 2's direct fetch
        # returns the now-closed form → END emitted.
        self._set_events([])
        self._set_event_by_id({
            'evt': self._api_event(
                event_id = 'evt', start = start_dt, end = end_dt,
            ),
        })
        cycle2 = self.run_async( self._run() )
        end_obj = self._find_response( cycle2, 'front_yard' )
        self.assertEqual( end_obj.correlation_role, CorrelationRole.END )
        self.assertEqual( end_obj.correlation_id, 'evt' )
        self.assertEqual( end_obj.timestamp, end_dt )

        # Open set is empty again — ready to receive the next event.
        self.assertEqual( self.monitor._tracked_events, {} )

    def test_object_class_switch_within_one_cycle_emits_both_transitions(self):
        """Person→Car switch within one poll cycle: Frigate closes the
        prior Person event and opens a Car event. HI's cursor scan
        sees the new Car; phase 2 refresh sees the closed Person. Both
        responses must travel in the per-key list — collapse to one
        would silently drop the Car START and a downstream rule on
        ``OBJECT_PRESENCE NEQ OBJECT_NONE`` would fail to re-fire."""
        # Cycle 1: Person event is open.
        person_start = self.start + timedelta( seconds = 1 )
        self._set_events([
            self._api_event(
                event_id = 'p', start = person_start, end = None,
                label = 'person',
            ),
        ])
        self._set_event_by_id({
            'p': self._api_event(
                event_id = 'p', start = person_start, end = None,
                label = 'person',
            ),
        })
        self.run_async( self._run() )
        self.assertIn( 'p', self.monitor._tracked_events )

        # Cycle 2: user switched Person → Car. Simulator closes the
        # Person event and opens a Car event with a later start_time.
        person_end = person_start + timedelta( seconds = 5 )
        car_start = person_end + timedelta( milliseconds = 1 )
        self._set_events([
            self._api_event(
                event_id = 'c', start = car_start, end = None,
                label = 'car',
            ),
        ])
        self._set_event_by_id({
            'p': self._api_event(
                event_id = 'p', start = person_start, end = person_end,
                label = 'person',
            ),
            'c': self._api_event(
                event_id = 'c', start = car_start, end = None,
                label = 'car',
            ),
        })
        cycle2 = self.run_async( self._run() )

        # Person END (phase 2) and Car START (phase 1) must BOTH be
        # in front_yard's response list, in chronological order. The
        # SensorResponseManager records each transition independently.
        response_list = self._find_responses( cycle2, 'front_yard' )
        sorted_responses = sorted( response_list, key = lambda r : r.timestamp )
        self.assertEqual( len( sorted_responses ), 2 )
        self.assertEqual( sorted_responses[ 0 ].correlation_role, CorrelationRole.END )
        self.assertEqual( sorted_responses[ 0 ].correlation_id, 'p' )
        self.assertEqual( sorted_responses[ 1 ].correlation_role, CorrelationRole.START )
        self.assertEqual( sorted_responses[ 1 ].correlation_id, 'c' )

        # Open set has swapped contents: Person gone, Car tracked.
        self.assertNotIn( 'p', self.monitor._tracked_events )
        self.assertIn( 'c', self.monitor._tracked_events )


