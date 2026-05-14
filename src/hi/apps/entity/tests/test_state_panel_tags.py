import logging

from hi.apps.entity.enums import EntityStateRole, EntityType
from hi.apps.entity.models import Entity, EntityState, EntityStateDelegation
from hi.apps.entity.templatetags.state_panel_tags import panel_state
from hi.testing.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestPanelState(BaseTestCase):
    """``panel_state`` looks up an EntityState on the entity by
    EntityStateRole (case-insensitive name match), walking the
    entity's own states then delegated states. Returns None when
    no state with the requested role is bound to the entity."""

    def setUp(self):
        super().setUp()
        self.entity = Entity.objects.create(
            name = 'Test Thermostat',
            entity_type_str = str( EntityType.THERMOSTAT ),
        )
        self.current_temp_state = EntityState.objects.create(
            entity = self.entity,
            name = 'Current Temperature',
            entity_state_type_str = 'TEMPERATURE',
            role_str = str( EntityStateRole.THERMOSTAT_CURRENT_TEMPERATURE ),
        )
        self.setpoint_state = EntityState.objects.create(
            entity = self.entity,
            name = 'Target Temperature',
            entity_state_type_str = 'TEMPERATURE',
            role_str = str( EntityStateRole.THERMOSTAT_TARGET_TEMPERATURE ),
        )

    def test_returns_state_matching_role(self):
        state = panel_state( self.entity, 'thermostat_current_temperature' )
        self.assertEqual( state, self.current_temp_state )

    def test_role_match_is_case_insensitive(self):
        state = panel_state( self.entity, 'THERMOSTAT_TARGET_TEMPERATURE' )
        self.assertEqual( state, self.setpoint_state )

    def test_returns_none_when_no_state_matches_role(self):
        # The entity has no HVAC_MODE state; lookup returns None.
        result = panel_state( self.entity, 'hvac_mode' )
        self.assertIsNone( result )

    def test_returns_none_for_unknown_role_name(self):
        result = panel_state( self.entity, 'definitely_not_a_real_role' )
        self.assertIsNone( result )

    def test_walks_delegated_states(self):
        # A state delegated from another entity should be reachable
        # by role lookup on the delegating entity.
        principal_entity = Entity.objects.create(
            name = 'External Humidity Sensor',
            entity_type_str = str( EntityType.OTHER ),
        )
        humidity_state = EntityState.objects.create(
            entity = principal_entity,
            name = 'Humidity',
            entity_state_type_str = 'HUMIDITY',
            role_str = str( EntityStateRole.HUMIDITY ),
        )
        EntityStateDelegation.objects.create(
            delegate_entity = self.entity,
            entity_state = humidity_state,
        )

        state = panel_state( self.entity, 'humidity' )
        self.assertEqual( state, humidity_state )

    def test_own_state_wins_over_delegated_when_roles_collide(self):
        # If both an own state and a delegated state carry the same
        # role, the entity's own state is returned (own-states pass
        # is first in the lookup order).
        principal_entity = Entity.objects.create(
            name = 'External', entity_type_str = str( EntityType.OTHER ),
        )
        delegated_dup = EntityState.objects.create(
            entity = principal_entity,
            name = 'Other Current Temp',
            entity_state_type_str = 'TEMPERATURE',
            role_str = str( EntityStateRole.THERMOSTAT_CURRENT_TEMPERATURE ),
        )
        EntityStateDelegation.objects.create(
            delegate_entity = self.entity,
            entity_state = delegated_dup,
        )

        state = panel_state( self.entity, 'thermostat_current_temperature' )
        self.assertEqual( state, self.current_temp_state )
