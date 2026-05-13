import logging
from datetime import datetime, timedelta, timezone

from hi.apps.control.models import Controller, ControllerHistory
from hi.apps.entity.entity_state_history import (
    InstrumentType,
    StateHistoryValueType,
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
