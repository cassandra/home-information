import logging
from datetime import datetime, timedelta, timezone

from hi.apps.control.models import Controller, ControllerHistory
from hi.apps.entity.entity_state_history import (
    InstrumentType,
    StateHistoryValueType,
    get_entity_state_history_page,
    merge_history,
)
from hi.apps.entity.models import Entity, EntityState
from hi.apps.sense.models import Sensor, SensorHistory
from hi.testing.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


BASE_TIME = datetime( 2024, 3, 1, 12, 0, 0, tzinfo = timezone.utc )


def _at( seconds_offset : int ) -> datetime:
    return BASE_TIME + timedelta( seconds = seconds_offset )


class TestMergeHistory( BaseTestCase ):
    """``merge_history`` is the pure foundation of the per-EntityState
    merged history view. It collapses controller intents that were
    confirmed by a subsequent sensor reading into annotated
    observations, leaves unmatched intents standalone, and returns
    rows in descending timestamp order."""

    def setUp(self):
        super().setUp()
        self.entity = Entity.objects.create(
            name = 'Test Entity', entity_type_str = 'WALL_SWITCH',
        )
        self.state = EntityState.objects.create(
            entity = self.entity,
            name = 'on_off',
            entity_state_type_str = 'ON_OFF',
        )
        self.sensor = Sensor.objects.create(
            entity_state = self.state,
            name = 'sw-sensor',
            sensor_type_str = 'DEFAULT',
            integration_payload = '{}',
        )
        self.controller = Controller.objects.create(
            entity_state = self.state,
            name = 'sw-ctrl',
            controller_type_str = 'DEFAULT',
            integration_payload = '{}',
        )

    # ------------------------------------------------------------------
    # Helpers

    def _observation( self, value : str, at : datetime, sensor : Sensor = None ):
        return SensorHistory.objects.create(
            sensor = sensor or self.sensor,
            value = value,
            response_datetime = at,
        )

    def _intent( self, value : str, at : datetime, controller : Controller = None ):
        ctrl = controller or self.controller
        # ControllerHistory.created_datetime is auto_now_add; need to
        # override after create for deterministic test timestamps.
        h = ControllerHistory.objects.create( controller = ctrl, value = value )
        ControllerHistory.objects.filter( pk = h.pk ).update( created_datetime = at )
        h.refresh_from_db()
        return h

    # ------------------------------------------------------------------
    # Base cases

    def test_empty_inputs_returns_empty_list(self):
        result = merge_history(
            entity_state = self.state,
            observation_rows = [],
            intent_rows = [],
        )
        self.assertEqual( result, [] )

    def test_lone_observation_emits_plain_observation_row(self):
        obs = self._observation( 'on', _at( 0 ) )

        result = merge_history(
            entity_state = self.state,
            observation_rows = [ obs ],
            intent_rows = [],
        )

        self.assertEqual( len( result ), 1 )
        row = result[ 0 ]
        self.assertEqual( row.history_value_type, StateHistoryValueType.OBSERVATION )
        self.assertEqual( row.value, 'on' )
        self.assertEqual( row.instrument.instrument_type, InstrumentType.SENSOR )
        self.assertEqual( row.instrument.id, self.sensor.id )
        self.assertIsNone( row.matched_intent )

    def test_lone_unmatched_intent_emits_intent_row(self):
        intent = self._intent( 'on', _at( 0 ) )

        result = merge_history(
            entity_state = self.state,
            observation_rows = [],
            intent_rows = [ intent ],
        )

        self.assertEqual( len( result ), 1 )
        row = result[ 0 ]
        self.assertEqual( row.history_value_type, StateHistoryValueType.INTENT )
        self.assertEqual( row.value, 'on' )
        self.assertEqual( row.instrument.instrument_type, InstrumentType.CONTROLLER )
        self.assertEqual( row.instrument.id, self.controller.id )
        self.assertIsNone( row.matched_intent )

    # ------------------------------------------------------------------
    # Matching semantics

    def test_intent_with_matching_observation_in_window_collapses(self):
        # Intent at T=0, observation at T=3 with same value. Within 10s
        # window — observation absorbs the intent.
        intent = self._intent( 'on', _at( 0 ) )
        obs = self._observation( 'on', _at( 3 ) )

        result = merge_history(
            entity_state = self.state,
            observation_rows = [ obs ],
            intent_rows = [ intent ],
        )

        # Single row: the observation, annotated.
        self.assertEqual( len( result ), 1 )
        row = result[ 0 ]
        self.assertEqual( row.history_value_type, StateHistoryValueType.OBSERVATION )
        self.assertEqual( row.timestamp, _at( 3 ) )
        self.assertIsNotNone( row.matched_intent )
        self.assertEqual( row.matched_intent.timestamp, _at( 0 ) )
        self.assertEqual( row.matched_intent.instrument.id, self.controller.id )

    def test_intent_with_non_matching_value_within_window_keeps_both(self):
        # Same time window, different values — no merge.
        intent = self._intent( 'on', _at( 0 ) )
        obs = self._observation( 'off', _at( 3 ) )

        result = merge_history(
            entity_state = self.state,
            observation_rows = [ obs ],
            intent_rows = [ intent ],
        )

        self.assertEqual( len( result ), 2 )
        kinds = sorted( r.history_value_type.name for r in result )
        self.assertEqual( kinds, [ 'INTENT', 'OBSERVATION' ] )

    def test_intent_with_matching_observation_past_window_keeps_both(self):
        # Observation is past the merge window — no match.
        intent = self._intent( 'on', _at( 0 ) )
        obs = self._observation( 'on', _at( 15 ) )

        result = merge_history(
            entity_state = self.state,
            observation_rows = [ obs ],
            intent_rows = [ intent ],
            window_seconds = 10,
        )

        self.assertEqual( len( result ), 2 )
        kinds = sorted( r.history_value_type.name for r in result )
        self.assertEqual( kinds, [ 'INTENT', 'OBSERVATION' ] )
        for row in result:
            self.assertIsNone( row.matched_intent )

    def test_observation_before_intent_does_not_match(self):
        # Sensor reading occurs BEFORE the intent — cannot have been
        # caused by it. No match.
        obs = self._observation( 'on', _at( 0 ) )
        intent = self._intent( 'on', _at( 3 ) )

        result = merge_history(
            entity_state = self.state,
            observation_rows = [ obs ],
            intent_rows = [ intent ],
        )

        self.assertEqual( len( result ), 2 )
        for row in result:
            self.assertIsNone( row.matched_intent )

    def test_window_boundary_is_inclusive(self):
        # Observation exactly at intent_time + window_seconds matches.
        intent = self._intent( 'on', _at( 0 ) )
        obs = self._observation( 'on', _at( 10 ) )

        result = merge_history(
            entity_state = self.state,
            observation_rows = [ obs ],
            intent_rows = [ intent ],
            window_seconds = 10,
        )

        self.assertEqual( len( result ), 1 )
        self.assertIsNotNone( result[ 0 ].matched_intent )

    # ------------------------------------------------------------------
    # Multi-instrument and multi-intent cases

    def test_two_intents_in_window_only_second_matches(self):
        # I1=off at T=0, I2=on at T=2, O=on at T=5. I2 matches; I1
        # standalone.
        intent_1 = self._intent( 'off', _at( 0 ) )
        intent_2 = self._intent( 'on', _at( 2 ) )
        obs = self._observation( 'on', _at( 5 ) )

        result = merge_history(
            entity_state = self.state,
            observation_rows = [ obs ],
            intent_rows = [ intent_1, intent_2 ],
        )

        self.assertEqual( len( result ), 2 )
        # Sorted descending: observation (annotated) at T=5, then intent_1 at T=0.
        self.assertEqual( result[ 0 ].history_value_type, StateHistoryValueType.OBSERVATION )
        self.assertIsNotNone( result[ 0 ].matched_intent )
        self.assertEqual( result[ 0 ].matched_intent.timestamp, _at( 2 ) )
        self.assertEqual( result[ 1 ].history_value_type, StateHistoryValueType.INTENT )
        self.assertEqual( result[ 1 ].value, 'off' )

    def test_two_intents_same_value_claim_distinct_observations(self):
        # I1=on at T=0, I2=on at T=2, O1=on at T=4, O2=on at T=6.
        # First-claim-wins: I1 claims O1; I2 claims O2. Both
        # observations annotated, both intents matched.
        intent_1 = self._intent( 'on', _at( 0 ) )
        intent_2 = self._intent( 'on', _at( 2 ) )
        obs_1 = self._observation( 'on', _at( 4 ) )
        obs_2 = self._observation( 'on', _at( 6 ) )

        result = merge_history(
            entity_state = self.state,
            observation_rows = [ obs_1, obs_2 ],
            intent_rows = [ intent_1, intent_2 ],
        )

        self.assertEqual( len( result ), 2 )
        for row in result:
            self.assertEqual( row.history_value_type, StateHistoryValueType.OBSERVATION )
            self.assertIsNotNone( row.matched_intent )
        # Newest first: O2 (matched to I2) then O1 (matched to I1).
        self.assertEqual( result[ 0 ].timestamp, _at( 6 ) )
        self.assertEqual( result[ 0 ].matched_intent.timestamp, _at( 2 ) )
        self.assertEqual( result[ 1 ].timestamp, _at( 4 ) )
        self.assertEqual( result[ 1 ].matched_intent.timestamp, _at( 0 ) )

    def test_redundant_intent_with_single_observation_leaves_one_unmatched(self):
        # I1=on at T=0, I2=on at T=1 (redundant), O=on at T=3.
        # First-claim-wins: I1 claims O. I2 has no remaining
        # observation in its window and emits standalone.
        intent_1 = self._intent( 'on', _at( 0 ) )
        intent_2 = self._intent( 'on', _at( 1 ) )
        obs = self._observation( 'on', _at( 3 ) )

        result = merge_history(
            entity_state = self.state,
            observation_rows = [ obs ],
            intent_rows = [ intent_1, intent_2 ],
        )

        self.assertEqual( len( result ), 2 )
        # Newest first: the annotated observation, then the unmatched I2.
        self.assertEqual( result[ 0 ].history_value_type, StateHistoryValueType.OBSERVATION )
        self.assertEqual( result[ 0 ].matched_intent.timestamp, _at( 0 ) )
        self.assertEqual( result[ 1 ].history_value_type, StateHistoryValueType.INTENT )
        self.assertEqual( result[ 1 ].timestamp, _at( 1 ) )

    def test_multiple_sensors_observations_merge_into_single_timeline(self):
        # Two sensors on the same state both contribute observations.
        other_sensor = Sensor.objects.create(
            entity_state = self.state,
            name = 'sw-sensor-b',
            sensor_type_str = 'DEFAULT',
            integration_payload = '{}',
        )
        obs_a = self._observation( 'on', _at( 0 ) )
        obs_b = self._observation( 'off', _at( 5 ), sensor = other_sensor )

        result = merge_history(
            entity_state = self.state,
            observation_rows = [ obs_a, obs_b ],
            intent_rows = [],
        )

        self.assertEqual( len( result ), 2 )
        sensor_ids = { r.instrument.id for r in result }
        self.assertEqual( sensor_ids, { self.sensor.id, other_sensor.id } )

    def test_multiple_controllers_intents_considered_separately(self):
        # Two controllers; only one of their intents matches an
        # observation. The unmatched intent on the other controller
        # still emits standalone.
        other_controller = Controller.objects.create(
            entity_state = self.state,
            name = 'sw-ctrl-b',
            controller_type_str = 'DEFAULT',
            integration_payload = '{}',
        )
        intent_a = self._intent( 'on', _at( 0 ) )
        intent_b = self._intent( 'off', _at( 1 ), controller = other_controller )
        obs = self._observation( 'on', _at( 4 ) )

        result = merge_history(
            entity_state = self.state,
            observation_rows = [ obs ],
            intent_rows = [ intent_a, intent_b ],
        )

        self.assertEqual( len( result ), 2 )
        # Annotated observation absorbed intent_a (from self.controller).
        annotated = [ r for r in result
                      if r.history_value_type == StateHistoryValueType.OBSERVATION ][ 0 ]
        self.assertIsNotNone( annotated.matched_intent )
        self.assertEqual( annotated.matched_intent.instrument.id, self.controller.id )
        # Unmatched intent retained its other-controller identity.
        unmatched = [ r for r in result
                      if r.history_value_type == StateHistoryValueType.INTENT ][ 0 ]
        self.assertEqual( unmatched.instrument.id, other_controller.id )
        self.assertEqual( unmatched.value, 'off' )

    # ------------------------------------------------------------------
    # Output ordering

    def test_result_is_sorted_descending_by_timestamp(self):
        # Out-of-order input still produces newest-first output.
        obs_old = self._observation( 'on', _at( 0 ) )
        obs_new = self._observation( 'off', _at( 100 ) )
        intent_mid = self._intent( 'idle', _at( 50 ) )

        result = merge_history(
            entity_state = self.state,
            observation_rows = [ obs_old, obs_new ],
            intent_rows = [ intent_mid ],
        )

        timestamps = [ r.timestamp for r in result ]
        self.assertEqual( timestamps, sorted( timestamps, reverse = True ) )

    # ------------------------------------------------------------------
    # Click-through metadata on OBSERVATION rows.

    def test_observation_row_carries_sensor_history_id(self):
        obs = self._observation( 'on', _at( 0 ) )

        result = merge_history(
            entity_state = self.state,
            observation_rows = [ obs ],
            intent_rows = [],
        )

        self.assertEqual( len( result ), 1 )
        self.assertEqual( result[ 0 ].sensor_history_id, obs.id )

    def test_observation_row_reflects_has_event_video_clip_from_source(self):
        obs_with = SensorHistory.objects.create(
            sensor = self.sensor, value = 'on',
            response_datetime = _at( 0 ), has_event_video_clip = True,
        )
        obs_without = SensorHistory.objects.create(
            sensor = self.sensor, value = 'on',
            response_datetime = _at( 1 ), has_event_video_clip = False,
        )

        result = merge_history(
            entity_state = self.state,
            observation_rows = [ obs_with, obs_without ],
            intent_rows = [],
        )

        by_id = { r.sensor_history_id: r for r in result }
        self.assertTrue( by_id[ obs_with.id ].has_event_video_clip )
        self.assertFalse( by_id[ obs_without.id ].has_event_video_clip )

    def test_observation_row_has_details_when_details_present(self):
        obs_with = SensorHistory.objects.create(
            sensor = self.sensor, value = 'on',
            response_datetime = _at( 0 ),
            details = '{"trigger": "motion"}',
        )
        obs_without = self._observation( 'on', _at( 1 ) )

        result = merge_history(
            entity_state = self.state,
            observation_rows = [ obs_with, obs_without ],
            intent_rows = [],
        )

        by_id = { r.sensor_history_id: r for r in result }
        self.assertTrue( by_id[ obs_with.id ].has_details )
        self.assertFalse( by_id[ obs_without.id ].has_details )

    def test_observation_row_reflects_provides_event_video_clip_from_sensor(self):
        # Two sensors on the same state, one with provides_event_video_clip
        # set. Each observation row carries its sensor's flag.
        video_sensor = Sensor.objects.create(
            entity_state = self.state,
            name = 'cam-sensor',
            sensor_type_str = 'DEFAULT',
            integration_payload = '{}',
            provides_event_video_clip = True,
        )
        obs_video = self._observation( 'on', _at( 0 ), sensor = video_sensor )
        obs_plain = self._observation( 'on', _at( 1 ) )

        result = merge_history(
            entity_state = self.state,
            observation_rows = [ obs_video, obs_plain ],
            intent_rows = [],
        )

        by_id = { r.sensor_history_id: r for r in result }
        self.assertTrue( by_id[ obs_video.id ].provides_event_video_clip )
        self.assertFalse( by_id[ obs_plain.id ].provides_event_video_clip )

    def test_intent_row_click_through_fields_at_defaults(self):
        intent = self._intent( 'on', _at( 0 ) )

        result = merge_history(
            entity_state = self.state,
            observation_rows = [],
            intent_rows = [ intent ],
        )

        self.assertEqual( len( result ), 1 )
        row = result[ 0 ]
        self.assertIsNone( row.sensor_history_id )
        self.assertFalse( row.has_event_video_clip )
        self.assertFalse( row.has_details )
        self.assertFalse( row.provides_event_video_clip )

    # ------------------------------------------------------------------
    # Click-through URL properties on the row type.

    def test_observation_with_video_stream_has_video_browse_url(self):
        obs = SensorHistory.objects.create(
            sensor = self.sensor, value = 'on',
            response_datetime = _at( 0 ), has_event_video_clip = True,
        )

        result = merge_history(
            entity_state = self.state,
            observation_rows = [ obs ],
            intent_rows = [],
        )

        self.assertIsNotNone( result[ 0 ].video_browse_url )

    def test_observation_with_details_has_details_url(self):
        obs = SensorHistory.objects.create(
            sensor = self.sensor, value = 'on',
            response_datetime = _at( 0 ),
            details = '{"trigger": "motion"}',
        )

        result = merge_history(
            entity_state = self.state,
            observation_rows = [ obs ],
            intent_rows = [],
        )

        self.assertIsNotNone( result[ 0 ].details_url )

    def test_observation_without_video_or_details_has_no_click_url(self):
        obs = self._observation( 'on', _at( 0 ) )

        result = merge_history(
            entity_state = self.state,
            observation_rows = [ obs ],
            intent_rows = [],
        )

        row = result[ 0 ]
        self.assertIsNone( row.video_browse_url )
        self.assertIsNone( row.details_url )
        self.assertIsNone( row.click_url )

    def test_intent_row_has_no_click_through_urls(self):
        intent = self._intent( 'on', _at( 0 ) )

        result = merge_history(
            entity_state = self.state,
            observation_rows = [],
            intent_rows = [ intent ],
        )

        row = result[ 0 ]
        self.assertIsNone( row.video_browse_url )
        self.assertIsNone( row.details_url )
        self.assertIsNone( row.click_url )

    def test_click_url_prefers_video_over_details(self):
        obs = SensorHistory.objects.create(
            sensor = self.sensor, value = 'on',
            response_datetime = _at( 0 ),
            has_event_video_clip = True,
            details = '{"trigger": "motion"}',
        )

        result = merge_history(
            entity_state = self.state,
            observation_rows = [ obs ],
            intent_rows = [],
        )

        row = result[ 0 ]
        self.assertEqual( row.click_url, row.video_browse_url )


class TestGetEntityStateHistoryPage( BaseTestCase ):
    """``get_entity_state_history_page`` is the sensor-anchored page
    fetcher that the per-EntityState merged history view consumes.
    Bounds the controller-history fetch to the observation page's
    time range so the merge sees a coherent window of both sides."""

    def setUp(self):
        super().setUp()
        self.entity = Entity.objects.create(
            name = 'Test Entity', entity_type_str = 'WALL_SWITCH',
        )
        self.state = EntityState.objects.create(
            entity = self.entity,
            name = 'on_off',
            entity_state_type_str = 'ON_OFF',
        )
        self.sensor = Sensor.objects.create(
            entity_state = self.state,
            name = 'sw-sensor',
            sensor_type_str = 'DEFAULT',
            integration_payload = '{}',
        )
        self.controller = Controller.objects.create(
            entity_state = self.state,
            name = 'sw-ctrl',
            controller_type_str = 'DEFAULT',
            integration_payload = '{}',
        )

    def _observation( self, value : str, at : datetime ):
        return SensorHistory.objects.create(
            sensor = self.sensor, value = value, response_datetime = at,
        )

    def _intent( self, value : str, at : datetime ):
        h = ControllerHistory.objects.create( controller = self.controller, value = value )
        ControllerHistory.objects.filter( pk = h.pk ).update( created_datetime = at )
        h.refresh_from_db()
        return h

    def test_empty_state_returns_empty(self):
        result = get_entity_state_history_page(
            entity_state = self.state, page_size = 25,
        )
        self.assertEqual( result, [] )

    def test_page_returns_descending_observations_and_matching_intents(self):
        # Five observations recent; two intents matching the first
        # two observations within window.
        obs_recent = [ self._observation( f'v{i}', _at( 100 - i ) ) for i in range( 5 ) ]
        # observations: v0 at 100, v1 at 99, v2 at 98, v3 at 97, v4 at 96
        # Match intents to the two oldest observations in the page.
        self._intent( 'v4', _at( 90 ) )    # within 10s of v4@96
        self._intent( 'v3', _at( 89 ) )    # within 10s of v3@97 (97-89=8)

        rows = get_entity_state_history_page(
            entity_state = self.state, page_size = 5,
        )

        self.assertEqual( len( rows ), 5 )
        # Descending timestamps: 100, 99, 98, 97, 96.
        timestamps = [ r.timestamp for r in rows ]
        self.assertEqual( timestamps, sorted( timestamps, reverse = True ) )
        # The two oldest rows in the page carry intent annotations.
        annotated = [ r for r in rows if r.matched_intent is not None ]
        self.assertEqual( len( annotated ), 2 )
        # Smoke-check: the page's observations are the ones we created.
        observation_values = [ r.value for r in rows ]
        self.assertEqual( observation_values, [ 'v0', 'v1', 'v2', 'v3', 'v4' ] )
        # And we didn't accidentally drop them — keep tied to fixture.
        for obs in obs_recent:
            self.assertIn( obs.value, observation_values )

    def test_before_cursor_filters_older_rows(self):
        # Ten observations spaced 10 seconds apart; ask for 3 older
        # than a cursor in the middle.
        for i in range( 10 ):
            self._observation( f'v{i}', _at( 100 + 10 * i ) )
        cursor = _at( 150 )    # corresponds to v5

        rows = get_entity_state_history_page(
            entity_state = self.state, page_size = 3, before = cursor,
        )

        self.assertEqual( len( rows ), 3 )
        # All returned rows must be strictly older than the cursor.
        for r in rows:
            self.assertLess( r.timestamp, cursor )
        # The newest of the three is the observation at T=140 (v4).
        self.assertEqual( rows[ 0 ].value, 'v4' )

    def test_state_with_controllers_only_falls_back_to_intent_anchored(self):
        # No sensors / no observations exist — only intents. The
        # function returns up to page_size most-recent intents.
        for i in range( 5 ):
            self._intent( f'i{i}', _at( 100 - i * 10 ) )

        rows = get_entity_state_history_page(
            entity_state = self.state, page_size = 3,
        )

        self.assertEqual( len( rows ), 3 )
        for r in rows:
            self.assertEqual( r.history_value_type, StateHistoryValueType.INTENT )
            self.assertEqual( r.instrument.instrument_type, InstrumentType.CONTROLLER )

    def test_gap_intents_between_observation_and_cursor_appear_in_page(self):
        # Page's newest observation is at T=50; an unmatched intent
        # fires at T=80 — between the page's observations and the
        # before-cursor (T=100). It must appear on this page rather
        # than disappear into a coverage gap.
        self._observation( 'on', _at( 50 ) )
        self._observation( 'on', _at( 40 ) )
        gap_intent = self._intent( 'mystery', _at( 80 ) )

        rows = get_entity_state_history_page(
            entity_state = self.state, page_size = 5, before = _at( 100 ),
        )

        intents = [ r for r in rows if r.history_value_type == StateHistoryValueType.INTENT ]
        self.assertEqual( len( intents ), 1 )
        self.assertEqual( intents[ 0 ].timestamp, gap_intent.created_datetime )

    def test_other_entity_state_history_is_not_returned(self):
        # A second EntityState with its own instruments should not
        # leak into the queried state's page.
        other_entity = Entity.objects.create( name = 'Other', entity_type_str = 'WALL_SWITCH' )
        other_state = EntityState.objects.create(
            entity = other_entity, name = 'on_off', entity_state_type_str = 'ON_OFF',
        )
        other_sensor = Sensor.objects.create(
            entity_state = other_state, name = 'other-sensor',
            sensor_type_str = 'DEFAULT', integration_payload = '{}',
        )
        SensorHistory.objects.create(
            sensor = other_sensor, value = 'should-not-appear',
            response_datetime = _at( 0 ),
        )
        self._observation( 'mine', _at( 0 ) )

        rows = get_entity_state_history_page(
            entity_state = self.state, page_size = 25,
        )

        values = [ r.value for r in rows ]
        self.assertIn( 'mine', values )
        self.assertNotIn( 'should-not-appear', values )
