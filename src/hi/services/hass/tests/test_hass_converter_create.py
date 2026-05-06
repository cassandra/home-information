"""
Pre-refactor safety net for HassConverter.create_models_for_hass_device.

The Phase 3 refactor of Issue #281 will change this entrypoint's
signature to accept an optional existing Entity (for the auto-reconnect
path). These tests pin the current "create a new Entity from upstream
payload" contract so the refactor can't silently regress it.

Coverage is deliberately narrow: one happy-path assertion that the
entrypoint produces an Entity with the right integration_key + at least
one ancillary component. State-mapping branches are already covered by
test_hass_converter_mapping.py.
"""
import logging

from django.test import TestCase

from hi.apps.attribute.enums import AttributeType, AttributeValueType
from hi.apps.entity.models import Entity, EntityAttribute, EntityState
from hi.apps.event.models import EventDefinition
from hi.integrations.entity_operations import EntityIntegrationOperations
from hi.services.hass.hass_converter import HassConverter
from hi.services.hass.hass_metadata import HassMetaData
from hi.services.hass.hass_models import HassDevice

logging.disable(logging.CRITICAL)


class CreateModelsForHassDeviceCreateNewContractTests(TestCase):
    """Pin the create-new-entity contract before the optional-entity refactor."""

    def _build_simple_light_device(self, device_id='kitchen_light'):
        """Hand-built HassDevice with a single light HassState — enough
        to drive the converter through entity + state + sensor/controller
        creation without coupling to specific fixture JSON."""
        api_dict = {
            'entity_id': f'light.{device_id}',
            'state': 'on',
            'attributes': {
                'friendly_name': device_id.replace('_', ' ').title(),
                'supported_color_modes': ['onoff'],
                'color_mode': 'onoff',
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

    def test_creates_entity_with_correct_integration_key(self):
        device = self._build_simple_light_device()

        entity = HassConverter.create_models_for_hass_device(
            hass_device=device,
            add_alarm_events=False,
        )

        self.assertIsInstance(entity, Entity)
        self.assertEqual(entity.integration_id, HassMetaData.integration_id)
        # integration_name is set from the device — converter normalizes it.
        self.assertIsNotNone(entity.integration_name)
        self.assertTrue(entity.integration_name)

    def test_creates_at_least_one_entity_state_for_the_device(self):
        device = self._build_simple_light_device()

        entity = HassConverter.create_models_for_hass_device(
            hass_device=device,
            add_alarm_events=False,
        )

        # Light produces at least one EntityState (the on/off state).
        self.assertGreaterEqual(EntityState.objects.filter(entity=entity).count(), 1)


class CreateModelsForHassDeviceReconnectContractTests(TestCase):
    """
    Pin the reconnect contract added in Issue #281 Phase 3:
    when ``entity`` is provided, the converter populates that entity's
    integration-owned components without creating a new Entity row and
    without overwriting the entity's name. The user may have edited
    the name before/after the intervening disconnect; reconnect must
    not clobber that.
    """

    def _build_simple_light_device(self, device_id='kitchen_light'):
        api_dict = {
            'entity_id': f'light.{device_id}',
            'state': 'on',
            'attributes': {
                'friendly_name': device_id.replace('_', ' ').title(),
                'supported_color_modes': ['onoff'],
                'color_mode': 'onoff',
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

    def test_with_existing_entity_does_not_create_new_entity(self):
        from hi.apps.entity.models import Entity as EntityModel

        # Pre-existing user-renamed entity (simulating one that was
        # disconnected and is now being reconnected).
        existing = EntityModel.objects.create(
            name='User Renamed Light',
            entity_type_str='LIGHT',
        )
        device = self._build_simple_light_device()
        baseline_count = EntityModel.objects.count()

        result = HassConverter.create_models_for_hass_device(
            hass_device=device,
            add_alarm_events=False,
            entity=existing,
        )

        self.assertEqual(EntityModel.objects.count(), baseline_count)
        self.assertEqual(result.id, existing.id)

    def test_with_existing_entity_preserves_entity_name(self):
        existing = Entity.objects.create(
            name='User Renamed Light',
            entity_type_str='LIGHT',
        )
        device = self._build_simple_light_device()

        HassConverter.create_models_for_hass_device(
            hass_device=device,
            add_alarm_events=False,
            entity=existing,
        )

        existing.refresh_from_db()
        self.assertEqual(existing.name, 'User Renamed Light')

    def test_with_existing_entity_sets_integration_key(self):
        existing = Entity.objects.create(
            name='User Renamed Light',
            entity_type_str='LIGHT',
        )
        device = self._build_simple_light_device()

        HassConverter.create_models_for_hass_device(
            hass_device=device,
            add_alarm_events=False,
            entity=existing,
        )

        existing.refresh_from_db()
        self.assertEqual(existing.integration_id, HassMetaData.integration_id)
        self.assertIsNotNone(existing.integration_name)


class EventDefinitionLifecycleCycleTests(TestCase):
    """
    Issue #288 Phase 3: end-to-end EventDefinition lifecycle for HASS
    across disable/re-enable cycles. Verifies that integration-owned
    EventDefinitions return to a stable count rather than accumulating.

    Uses a binary_sensor + motion device_class state — the converter
    maps that to ``EntityStateType.MOVEMENT`` and creates a
    ``create_movement_event_definition`` when ``add_alarm_events=True``.
    A single state shape is enough to exercise the cycle; the
    connectivity / open_close / battery branches share the same
    cleanup-and-recreate dispatch.
    """

    def _build_motion_sensor_device(self, device_id='hallway_motion'):
        api_dict = {
            'entity_id': f'binary_sensor.{device_id}',
            'state': 'off',
            'attributes': {
                'friendly_name': device_id.replace('_', ' ').title(),
                'device_class': 'motion',
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

    def _hass_event_def_count(self):
        return EventDefinition.objects.filter(
            integration_id=HassMetaData.integration_id,
        ).count()

    def test_motion_sensor_creates_one_event_definition(self):
        # Sanity: the chosen state shape actually drives the
        # add_alarm_events branch we're exercising.
        device = self._build_motion_sensor_device()
        HassConverter.create_models_for_hass_device(
            hass_device=device,
            add_alarm_events=True,
        )
        self.assertEqual(self._hass_event_def_count(), 1)

    def test_hard_delete_then_recreate_cycle_baseline_count(self):
        device = self._build_motion_sensor_device()
        entity = HassConverter.create_models_for_hass_device(
            hass_device=device,
            add_alarm_events=True,
        )
        self.assertEqual(self._hass_event_def_count(), 1)

        EntityIntegrationOperations.remove_entities_with_closure(
            seed_entity_ids=[entity.id],
            integration_name=HassMetaData.integration_id,
            preserve_user_data=False,
        )
        self.assertEqual(self._hass_event_def_count(), 0)

        # Re-import the same upstream device. Without Phase 2 cleanup,
        # the prior EventDefinition would still be present and we'd see
        # 2; with the fix, we're back to 1.
        HassConverter.create_models_for_hass_device(
            hass_device=self._build_motion_sensor_device(),
            add_alarm_events=True,
        )
        self.assertEqual(self._hass_event_def_count(), 1)

    def test_preserve_then_reconnect_cycle_baseline_count(self):
        device = self._build_motion_sensor_device()
        entity = HassConverter.create_models_for_hass_device(
            hass_device=device,
            add_alarm_events=True,
        )
        EntityAttribute.objects.create(
            entity=entity,
            name='User Note',
            value='retain me',
            value_type_str=str(AttributeValueType.TEXT),
            attribute_type_str=str(AttributeType.CUSTOM),
        )
        self.assertEqual(self._hass_event_def_count(), 1)

        EntityIntegrationOperations.preserve_with_user_data(
            entity=entity,
            integration_name=HassMetaData.integration_id,
        )
        self.assertEqual(self._hass_event_def_count(), 0)

        # Reconnect dispatch is the same converter call with
        # ``entity=existing``. Should recreate exactly one
        # EventDefinition for the upstream item.
        entity.refresh_from_db()
        HassConverter.create_models_for_hass_device(
            hass_device=self._build_motion_sensor_device(),
            add_alarm_events=True,
            entity=entity,
        )
        self.assertEqual(self._hass_event_def_count(), 1)
