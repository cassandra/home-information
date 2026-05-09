import logging

from django.test import TestCase

from hi.apps.control.models import Controller
from hi.apps.entity.enums import EntityStateType, EntityStateValue, EntityType
from hi.apps.entity.models import EntityState
from hi.services.hass.hass_converter import HassConverter
from hi.services.hass.hass_models import HassDevice, HassServiceCall, HassState

logging.disable(logging.CRITICAL)


def _make_lock_hass_state(api_dict, entity_id='lock.front_door'):
    return HassState(
        api_dict=api_dict,
        entity_id=entity_id,
        domain='lock',
        entity_name_sans_prefix=entity_id.split('.', 1)[1],
        entity_name_sans_suffix=entity_id.split('.', 1)[1],
    )


def _build_lock_device(device_id='front_door', state='locked'):
    api_dict = {
        'entity_id': f'lock.{device_id}',
        'state': state,
        'attributes': {
            'friendly_name': device_id.replace('_', ' ').title(),
        },
        'last_changed': '2026-01-01T00:00:00+00:00',
        'last_reported': '2026-01-01T00:00:00+00:00',
        'last_updated': '2026-01-01T00:00:00+00:00',
        'context': {'id': 'ctx', 'parent_id': None, 'user_id': None},
    }
    hass_state = HassConverter.create_hass_state(api_dict)
    device = HassDevice(device_id=device_id)
    device.add_state(hass_state)
    return device


class TestLockInboundStateTranslation(TestCase):
    """``hass_state_to_sensor_value_map`` translates HA's
    domain-specific lock state strings to HI's canonical ON_OFF
    values; without this, HI's checkbox display always reads as
    Off because ``SensorResponse.is_on`` checks for ``'on'``."""

    def test_locked_maps_to_canonical_on(self):
        hass_state = _make_lock_hass_state({
            'entity_id': 'lock.front_door',
            'state': 'locked',
            'attributes': {'friendly_name': 'Front Door'},
        })
        value_map = HassConverter.hass_state_to_sensor_value_map(hass_state)
        self.assertEqual(len(value_map), 1)
        self.assertEqual(list(value_map.values())[0], str(EntityStateValue.ON))

    def test_unlocked_maps_to_canonical_off(self):
        hass_state = _make_lock_hass_state({
            'entity_id': 'lock.front_door',
            'state': 'unlocked',
            'attributes': {'friendly_name': 'Front Door'},
        })
        value_map = HassConverter.hass_state_to_sensor_value_map(hass_state)
        self.assertEqual(list(value_map.values())[0], str(EntityStateValue.OFF))

    def test_unrecognized_state_value_passes_through(self):
        # HA may emit transitional states like 'locking' or
        # 'unlocking' on real locks; we don't translate those — the
        # next poll will land on a final state.
        hass_state = _make_lock_hass_state({
            'entity_id': 'lock.front_door',
            'state': 'locking',
            'attributes': {'friendly_name': 'Front Door'},
        })
        value_map = HassConverter.hass_state_to_sensor_value_map(hass_state)
        self.assertEqual(list(value_map.values())[0], 'locking')


class TestLockImport(TestCase):
    """Verify a lock entity from HA is imported with the right
    EntityType, EntityStateType, and a controllable on/off path."""

    def test_lock_imports_as_door_lock_entity_with_on_off_state_and_controller(self):
        device = _build_lock_device(device_id='front_door', state='locked')
        entity = HassConverter.create_models_for_hass_device(
            hass_device=device,
            add_alarm_events=False,
        )
        self.assertEqual(entity.entity_type, EntityType.DOOR_LOCK)

        entity_states = list(EntityState.objects.filter(entity=entity))
        self.assertEqual(len(entity_states), 1)
        self.assertEqual(entity_states[0].entity_state_type, EntityStateType.ON_OFF)

        controllers = list(Controller.objects.filter(entity_state=entity_states[0]))
        self.assertEqual(len(controllers), 1)
        # Outbound payload routes 'on' to lock.lock, 'off' to
        # lock.unlock — the existing CONTROL_SERVICE_MAPPING entry.
        payload = controllers[0].integration_payload
        self.assertEqual(payload.get('domain'), 'lock')
        self.assertEqual(payload.get('on_service'), 'lock')
        self.assertEqual(payload.get('off_service'), 'unlock')


class TestLockOutboundDispatch(TestCase):
    """Verify ``hi_value_to_hass_service_call`` routes the lock's
    payload-driven 'on'/'off' to the right HA services. This is
    the production path for a real imported lock; the existing
    best-effort lock test in ``test_hass_controller.py`` covers
    the no-payload fallback."""

    def _payload(self):
        return {
            'domain': 'lock',
            'is_controllable': True,
            'on_service': 'lock',
            'off_service': 'unlock',
            'parameters': {},
        }

    def test_on_routes_to_lock_service(self):
        service_call = HassConverter.hi_value_to_hass_service_call(
            hass_substate_id='lock.front_door',
            hi_control_value='on',
            domain_payload=self._payload(),
        )
        self.assertEqual(service_call, HassServiceCall(
            domain='lock', service='lock', hass_entity_id='lock.front_door',
        ))

    def test_off_routes_to_unlock_service(self):
        service_call = HassConverter.hi_value_to_hass_service_call(
            hass_substate_id='lock.front_door',
            hi_control_value='off',
            domain_payload=self._payload(),
        )
        self.assertEqual(service_call, HassServiceCall(
            domain='lock', service='unlock', hass_entity_id='lock.front_door',
        ))
