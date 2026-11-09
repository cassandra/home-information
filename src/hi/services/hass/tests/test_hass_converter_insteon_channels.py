import logging

from django.test import TestCase

from hi.apps.control.one_click_control_service import OneClickControlService
from hi.apps.entity.enums import EntityStateRole
from hi.apps.entity.models import EntityState
from hi.services.hass.hass_converter import HassConverter

logging.disable(logging.CRITICAL)


def _hass_state(entity_id, insteon_group, state='off', **attributes):
    attributes.setdefault('friendly_name', entity_id.split('.', 1)[1].replace('_', ' ').title())
    attributes['insteon_address'] = '71.83.8B'
    if insteon_group is not None:
        attributes['insteon_group'] = insteon_group
    return HassConverter.create_hass_state({
        'entity_id': entity_id,
        'state': state,
        'attributes': attributes,
        'last_changed': '2026-01-01T00:00:00+00:00',
        'last_reported': '2026-01-01T00:00:00+00:00',
        'last_updated': '2026-01-01T00:00:00+00:00',
        'context': {'id': 'ctx', 'parent_id': None, 'user_id': None},
    })


def _device(hass_states):
    devices = HassConverter.hass_states_to_hass_devices({
        hass_state.entity_id: hass_state for hass_state in hass_states
    })
    assert len(devices) == 1
    return next(iter(devices.values()))


def _keypad_states(main_group=1):
    return [
        _hass_state('switch.keypadlinc_on_off_71_83_8b_main', main_group),
        _hass_state('switch.keypadlinc_on_off_71_83_8b_button_a', 3),
        _hass_state('switch.keypadlinc_on_off_71_83_8b_button_b', 4),
    ]


def _roles_by_state_name(entity):
    return {
        state.name: state.entity_state_role
        for state in EntityState.objects.filter(entity=entity)
    }


class TestInsteonSecondaryChannelRoles(TestCase):
    """Multi-channel Insteon devices (KeypadLinc) report each button as
    its own HA state numbered by ``insteon_group``; group 1 is the
    device's load. Buttons get SECONDARY_ON_OFF so one-click and status
    choices favor the load."""

    def test_keypad_buttons_are_secondary_and_one_click_targets_the_load(self):
        entity = HassConverter.create_models_for_hass_device(
            hass_device=_device(_keypad_states()),
            add_alarm_events=False,
        )

        roles = _roles_by_state_name(entity)
        self.assertEqual(roles['Keypadlinc On Off 71 83 8B Main'], EntityStateRole.ON_OFF)
        self.assertEqual(roles['Keypadlinc On Off 71 83 8B Button A'], EntityStateRole.SECONDARY_ON_OFF)
        self.assertEqual(roles['Keypadlinc On Off 71 83 8B Button B'], EntityStateRole.SECONDARY_ON_OFF)
        controller = OneClickControlService()._find_controller(entity=entity)
        self.assertEqual(controller.integration_name, 'switch.keypadlinc_on_off_71_83_8b_main')

    def test_buttons_keep_default_role_without_a_group_one_state(self):
        """Only the device's own load justifies demoting the others; a
        device without one present keeps type-default roles."""
        entity = HassConverter.create_models_for_hass_device(
            hass_device=_device(_keypad_states(main_group=None)),
            add_alarm_events=False,
        )

        self.assertEqual(
            set(_roles_by_state_name(entity).values()),
            {EntityStateRole.ON_OFF},
        )

    def test_refresh_reconciles_roles_of_previously_imported_keypad(self):
        """Keypads imported before the role existed have ON_OFF buttons;
        a refresh moves them to SECONDARY_ON_OFF and reports the change."""
        device = _device(_keypad_states())
        entity = HassConverter.create_models_for_hass_device(
            hass_device=device,
            add_alarm_events=False,
        )
        EntityState.objects.filter(entity=entity).update(role_str=str(EntityStateRole.ON_OFF))

        messages = HassConverter.update_models_for_hass_device(entity=entity, hass_device=device)

        roles = _roles_by_state_name(entity)
        self.assertEqual(roles['Keypadlinc On Off 71 83 8B Main'], EntityStateRole.ON_OFF)
        self.assertEqual(roles['Keypadlinc On Off 71 83 8B Button A'], EntityStateRole.SECONDARY_ON_OFF)
        self.assertEqual(len([m for m in messages if 'role' in m]), 2)

    def test_refresh_restores_default_role_when_load_channel_disappears(self):
        entity = HassConverter.create_models_for_hass_device(
            hass_device=_device(_keypad_states()),
            add_alarm_events=False,
        )

        HassConverter.update_models_for_hass_device(
            entity=entity,
            hass_device=_device(_keypad_states(main_group=None)),
        )

        self.assertEqual(
            set(_roles_by_state_name(entity).values()),
            {EntityStateRole.ON_OFF},
        )
