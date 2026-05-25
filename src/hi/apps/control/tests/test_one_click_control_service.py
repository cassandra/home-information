import json
import logging
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from hi.apps.control.controller_manager import ControllerManager
from hi.apps.control.models import Controller
from hi.apps.control.one_click_control_service import (
    OneClickControlService,
    OneClickNotSupported,
)
from hi.apps.entity.enums import EntityStateRole, EntityStateType, EntityType
from hi.apps.entity.models import Entity, EntityState
from hi.apps.sense.transient_models import SensorResponse
from hi.integrations.transient_models import IntegrationControlResult
from hi.testing.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


def _make_state( entity, state_type, role = None, value_range_str = '' ):
    state = EntityState.objects.create(
        entity = entity,
        entity_state_type_str = str(state_type),
        name = f'{state_type.label} State',
        value_range_str = value_range_str,
    )
    if role is not None:
        state.entity_state_role = role
        state.save()
    return state


def _add_controller( state, name = 'ctrl' ):
    return Controller.objects.create(
        entity_state = state,
        name = name,
        controller_type_str = 'DEFAULT',
    )


class TestOneClickFindController(BaseTestCase):

    def test_unknown_entity_type_falls_back_to_default_on_off(self):
        # No override entry → curated default ON_OFF applies.
        # A WALL_SWITCH-style entity with an ON_OFF-role controlled
        # state gets one-clicked.
        entity = Entity.objects.create(
            name = 'Wall Switch',
            entity_type_str = str(EntityType.WALL_SWITCH),
        )
        state = _make_state( entity, EntityStateType.ON_OFF, EntityStateRole.ON_OFF )
        controller = _add_controller( state )

        picked = OneClickControlService()._find_controller( entity = entity )
        self.assertEqual( picked, controller )

    def test_light_override_prefers_light_on_off_over_other_roles(self):
        # LIGHT override = [LIGHT_ON_OFF]; the LIGHT_BRIGHTNESS role
        # state is ignored even though it has a controller. The
        # default ON_OFF tail still applies if no LIGHT_ON_OFF state
        # is present (covered in the next test).
        entity = Entity.objects.create(
            name = 'Smart Bulb',
            entity_type_str = str(EntityType.LIGHT),
        )
        brightness = _make_state(
            entity, EntityStateType.LIGHT_DIMMER, EntityStateRole.LIGHT_BRIGHTNESS,
            value_range_str = json.dumps({ 'min': 0, 'max': 100 }),
        )
        _add_controller( brightness, name = 'brightness-ctrl' )

        on_off = _make_state(
            entity, EntityStateType.ON_OFF, EntityStateRole.LIGHT_ON_OFF,
        )
        on_off_controller = _add_controller( on_off, name = 'on-off-ctrl' )

        picked = OneClickControlService()._find_controller( entity = entity )
        self.assertEqual( picked, on_off_controller )

    def test_color_bulb_without_light_on_off_uses_light_brightness(self):
        # Fully-modeled color bulbs (HA's substate-decomposition
        # path) carry refined roles only — LIGHT_BRIGHTNESS, HUE,
        # SATURATION, COLOR_TEMPERATURE, COLOR_MODE — with no plain
        # ON_OFF or LIGHT_ON_OFF state. The LIGHT override falls
        # through to LIGHT_BRIGHTNESS so the bulb's brightness
        # slider toggles between off and full on one-click.
        entity = Entity.objects.create(
            name = 'Color Bulb',
            entity_type_str = str(EntityType.LIGHT),
        )
        brightness = _make_state(
            entity, EntityStateType.LIGHT_DIMMER, EntityStateRole.LIGHT_BRIGHTNESS,
            value_range_str = json.dumps({ 'min': 0, 'max': 100 }),
        )
        controller = _add_controller( brightness, name = 'brightness-ctrl' )
        _make_state( entity, EntityStateType.HUE, EntityStateRole.LIGHT_HUE )

        picked = OneClickControlService()._find_controller( entity = entity )
        self.assertEqual( picked, controller )

    def test_light_without_light_on_off_falls_through_to_default_on_off(self):
        # LIGHT override is [LIGHT_ON_OFF]; default appends ON_OFF.
        # A light minimally modeled (only an ON_OFF-role state) still
        # gets one-click via the default fallback.
        entity = Entity.objects.create(
            name = 'Plain Light',
            entity_type_str = str(EntityType.LIGHT),
        )
        on_off = _make_state(
            entity, EntityStateType.ON_OFF, EntityStateRole.ON_OFF,
        )
        controller = _add_controller( on_off )

        picked = OneClickControlService()._find_controller( entity = entity )
        self.assertEqual( picked, controller )

    def test_thermometer_with_no_controllable_state_is_unsupported(self):
        # Sensor-only entity: no controllers → no one-click target.
        entity = Entity.objects.create(
            name = 'Thermometer',
            entity_type_str = str(EntityType.THERMOMETER),
        )
        _make_state( entity, EntityStateType.TEMPERATURE )

        with self.assertRaises( OneClickNotSupported ):
            OneClickControlService()._find_controller( entity = entity )

    def test_thermostat_with_only_complex_substates_is_unsupported(self):
        # THERMOSTAT has no override and no plain ON_OFF state — the
        # default ON_OFF fallback finds nothing. The setpoint and
        # mode substates carry domain-prefixed roles
        # (THERMOSTAT_TARGET_TEMPERATURE_*, HVAC_MODE, etc.) that
        # aren't in the curated default or any override, so one-click
        # is correctly refused even though those states have
        # controllers.
        entity = Entity.objects.create(
            name = 'Thermostat',
            entity_type_str = str(EntityType.THERMOSTAT),
        )
        setpoint = _make_state(
            entity, EntityStateType.TEMPERATURE,
            EntityStateRole.THERMOSTAT_TARGET_TEMPERATURE,
            value_range_str = json.dumps({ 'min': 60, 'max': 80 }),
        )
        _add_controller( setpoint, name = 'setpoint-ctrl' )

        with self.assertRaises( OneClickNotSupported ):
            OneClickControlService()._find_controller( entity = entity )

    def test_speed_only_fan_falls_through_to_power_level_default(self):
        # Speed-only fans (no oscillation / direction / presets) are
        # imported as a bare-key POWER_LEVEL state — not the
        # FAN_SPEED-role substate. The default tail includes
        # POWER_LEVEL so the bare-key shape is still one-clickable.
        entity = Entity.objects.create(
            name = 'Speed Fan',
            entity_type_str = str(EntityType.CEILING_FAN),
        )
        speed = _make_state(
            entity, EntityStateType.POWER_LEVEL, EntityStateRole.POWER_LEVEL,
            value_range_str = json.dumps({ 'min': 0, 'max': 100 }),
        )
        controller = _add_controller( speed )

        picked = OneClickControlService()._find_controller( entity = entity )
        self.assertEqual( picked, controller )

    def test_open_close_position_cover_falls_through_to_default(self):
        # Covers with position (blinds, shades, generic covers)
        # carry the OPEN_CLOSE_POSITION role. The default tail
        # includes it so the bare-key continuous cover toggles
        # between closed and open.
        entity = Entity.objects.create(
            name = 'Window Blind',
            entity_type_str = str(EntityType.OPEN_CLOSE_ACTUATOR),
        )
        position = _make_state(
            entity, EntityStateType.OPEN_CLOSE_POSITION, EntityStateRole.OPEN_CLOSE_POSITION,
            value_range_str = json.dumps({ 'min': 0, 'max': 100 }),
        )
        controller = _add_controller( position )

        picked = OneClickControlService()._find_controller( entity = entity )
        self.assertEqual( picked, controller )

    def test_execute_one_click_toggles_on_to_off_through_full_pipeline(self):
        # End-to-end glue test: a controllable ON_OFF state whose
        # latest sensor reading is "on" should one-click to "off" via
        # _find_controller → _get_current_state_value →
        # _determine_control_value → ControllerManager.do_control.
        # Mocks at the integration boundary (do_control) and at the
        # sensor-response boundary (latest reading); everything in
        # between is exercised for real.
        entity = Entity.objects.create(
            name = 'Wall Switch',
            entity_type_str = str(EntityType.WALL_SWITCH),
        )
        state = _make_state( entity, EntityStateType.ON_OFF, EntityStateRole.ON_OFF )
        controller = Controller.objects.create(
            entity_state = state,
            name = 'wall-ctrl',
            controller_type_str = 'DEFAULT',
            integration_id = 'home_assistant',
            integration_name = 'Home Assistant',
        )

        latest_response = SensorResponse(
            integration_key = controller.integration_key,
            value = 'on',
            timestamp = datetime.now( timezone.utc ),
        )

        mock_control_result = IntegrationControlResult(
            new_value = 'off', error_list = [],
        )
        mock_integration_controller = Mock()
        mock_integration_controller.do_control.return_value = mock_control_result
        mock_integration_gateway = Mock()
        mock_integration_gateway.get_connector.return_value.get_controller.return_value = mock_integration_controller
        mock_integration_manager = Mock()
        mock_integration_manager.get_integration_gateway.return_value = mock_integration_gateway

        with patch.object( ControllerManager, '_instance', None ), \
             patch( 'hi.apps.control.controller_manager.IntegrationManager',
                    return_value = mock_integration_manager ), \
             patch( 'hi.apps.monitor.status_display_manager.StatusDisplayManager'
                    '.get_latest_sensor_response',
                    return_value = latest_response ):
            outcome = OneClickControlService().execute_one_click_control( entity = entity )

        # do_control received the toggle target value derived from the
        # current "on" sensor reading.
        call_kwargs = mock_integration_controller.do_control.call_args.kwargs
        self.assertEqual( call_kwargs[ 'hi_control_value' ], 'off' )
        self.assertEqual( call_kwargs[ 'integration_details' ].key,
                          controller.integration_key )

        self.assertFalse( outcome.has_errors )
        self.assertEqual( outcome.new_value, 'off' )
        self.assertEqual( outcome.controller, controller )

    def test_execute_one_click_picks_first_value_when_no_sensor_history(self):
        # When there's no sensor history, _get_current_state_value
        # returns None and _determine_control_value falls through to
        # toggle_values()[0]. End-to-end: pipeline still dispatches.
        entity = Entity.objects.create(
            name = 'Wall Switch',
            entity_type_str = str(EntityType.WALL_SWITCH),
        )
        state = _make_state( entity, EntityStateType.ON_OFF, EntityStateRole.ON_OFF )
        controller = Controller.objects.create(
            entity_state = state,
            name = 'wall-ctrl',
            controller_type_str = 'DEFAULT',
            integration_id = 'home_assistant',
            integration_name = 'Home Assistant',
        )
        first_toggle = state.toggle_values()[ 0 ]

        mock_control_result = IntegrationControlResult(
            new_value = first_toggle, error_list = [],
        )
        mock_integration_controller = Mock()
        mock_integration_controller.do_control.return_value = mock_control_result
        mock_integration_gateway = Mock()
        mock_integration_gateway.get_connector.return_value.get_controller.return_value = mock_integration_controller
        mock_integration_manager = Mock()
        mock_integration_manager.get_integration_gateway.return_value = mock_integration_gateway

        with patch.object( ControllerManager, '_instance', None ), \
             patch( 'hi.apps.control.controller_manager.IntegrationManager',
                    return_value = mock_integration_manager ), \
             patch( 'hi.apps.monitor.status_display_manager.StatusDisplayManager'
                    '.get_latest_sensor_response',
                    return_value = None ):
            outcome = OneClickControlService().execute_one_click_control( entity = entity )

        call_kwargs = mock_integration_controller.do_control.call_args.kwargs
        self.assertEqual( call_kwargs[ 'hi_control_value' ], first_toggle )
        self.assertFalse( outcome.has_errors )
        self.assertEqual( outcome.controller, controller )

    def test_too_many_toggle_values_disqualifies_state(self):
        # A controllable state with more than ONE_CLICK_CHOICE_LIMIT
        # toggle values isn't one-click eligible (cycling through
        # many discrete options isn't a usable single-click
        # affordance). With no other eligible state, the entity is
        # NotSupported.
        entity = Entity.objects.create(
            name = 'Multi-mode',
            entity_type_str = str(EntityType.WALL_SWITCH),
        )
        many_values = _make_state(
            entity, EntityStateType.ON_OFF, EntityStateRole.ON_OFF,
            value_range_str = json.dumps([ 'a', 'b', 'c', 'd', 'e' ]),
        )
        _add_controller( many_values )

        with self.assertRaises( OneClickNotSupported ):
            OneClickControlService()._find_controller( entity = entity )
