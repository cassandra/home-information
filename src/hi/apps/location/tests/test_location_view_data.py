import logging
from datetime import datetime, timezone

from hi.apps.entity.enums import EntityStateRole, EntityStateType, EntityType
from hi.apps.entity.models import Entity, EntityState
from hi.apps.location.location_view_data import LocationViewData
from hi.apps.monitor.status_data import EntityStateStatusData
from hi.apps.sense.transient_models import SensorResponse
from hi.integrations.transient_models import IntegrationKey
from hi.testing.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


def _make_status_data( entity_state : EntityState, value : str, timestamp : datetime ):
    response = SensorResponse(
        integration_key = IntegrationKey( integration_id='test', integration_name='test' ),
        value = value,
        timestamp = timestamp,
    )
    return EntityStateStatusData(
        entity_state = entity_state,
        sensor_response_list = [ response ],
        controller_data_list = [],
        has_sensor = True,
    )


class TestLatestEntityStateStatusDataPicker(BaseTestCase):

    def _make_location_view_data( self, entity_to_list ):
        # Minimal construction — only the picker path needs the
        # entity-to-status-data map; other fields can be empty.
        return LocationViewData(
            location_view = None,
            entity_positions = [],
            entity_paths = [],
            collection_positions = [],
            collection_paths = [],
            unpositioned_collections = [],
            orphan_entities = set(),
            entity_to_entity_state_status_data_list = entity_to_list,
        )

    def test_role_priority_picks_primary_regardless_of_timestamp(self):
        # The picker selects the state whose role ranks highest in
        # ENTITY_PRIMARY_STATE_ORDERING for the entity's type, NOT
        # the most-recently-timestamped state. For a ceiling fan,
        # FAN_SPEED is the configured primary and must win even when
        # another state's response is more recent.
        fan = Entity.objects.create(
            name = 'Test Fan',
            entity_type_str = str( EntityType.CEILING_FAN ),
        )
        speed_state = EntityState.objects.create(
            entity = fan,
            entity_state_type_str = str( EntityStateType.POWER_LEVEL ),
            name = 'Speed',
        )
        speed_state.entity_state_role = EntityStateRole.FAN_SPEED
        speed_state.save()

        oscillation_state = EntityState.objects.create(
            entity = fan,
            entity_state_type_str = str( EntityStateType.ON_OFF ),
            name = 'Oscillation',
        )
        oscillation_state.entity_state_role = EntityStateRole.FAN_OSCILLATION
        oscillation_state.save()

        older = datetime( 2026, 1, 1, 10, 0, 0, tzinfo = timezone.utc )
        newer = datetime( 2026, 1, 1, 11, 0, 0, tzinfo = timezone.utc )
        status_list = [
            # Oscillation has the newer timestamp; the old picker
            # would have selected it. The role-based picker selects
            # FAN_SPEED.
            _make_status_data( oscillation_state, 'on', newer ),
            _make_status_data( speed_state, '75', older ),
        ]

        data = self._make_location_view_data({ fan: status_list })
        picked = data._latest_entity_state_status_data_map[ fan ]
        self.assertEqual( picked.entity_state, speed_state )

    def test_states_without_responses_are_skipped(self):
        # Locks in the "must have a response to be picked" guard.
        fan = Entity.objects.create(
            name = 'Test Fan',
            entity_type_str = str( EntityType.CEILING_FAN ),
        )
        speed_state = EntityState.objects.create(
            entity = fan,
            entity_state_type_str = str( EntityStateType.POWER_LEVEL ),
            name = 'Speed',
        )
        # No response — should be filtered out, leaving nothing
        # for the picker to choose.
        status_list = [
            EntityStateStatusData(
                entity_state = speed_state,
                sensor_response_list = [],
                controller_data_list = [],
                has_sensor = True,
            ),
        ]
        data = self._make_location_view_data({ fan: status_list })
        self.assertNotIn( fan, data._latest_entity_state_status_data_map )
