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
from hi.apps.entity.enums import EntityStateType
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


class CreateModelsForComboSensorDeviceTests(TestCase):
    """A real-world combo temp+humidity sensor surfaces in HA as two
    ``sensor.x`` entities (``sensor.<name>_temperature`` and
    ``sensor.<name>_humidity``); HI's converter groups them via the
    ``_temperature`` / ``_humidity`` suffix strip in
    ``STATE_SUFFIXES`` so the parent device collapses to one HI
    Entity with two EntityStates. Pin that end-to-end composition —
    the suffix-strip grouping is the path that makes #301's combo
    sensor work without an explicit HA device_group_id."""

    def _build_combo_device(self, device_id='kitchen_climate'):
        def _state(suffix, value, device_class, unit):
            api_dict = {
                'entity_id': f'sensor.{device_id}_{suffix}',
                'state': value,
                'attributes': {
                    'friendly_name':
                        f'{device_id.replace("_", " ").title()} '
                        f'{suffix.title()}',
                    'device_class': device_class,
                    'unit_of_measurement': unit,
                },
                'last_changed': '2026-01-01T00:00:00+00:00',
                'last_reported': '2026-01-01T00:00:00+00:00',
                'last_updated': '2026-01-01T00:00:00+00:00',
                'context': {'id': 'ctx', 'parent_id': None, 'user_id': None},
            }
            return HassConverter.create_hass_state(api_dict)
        device = HassDevice(device_id=device_id)
        device.add_state(_state('temperature', '72', 'temperature', '°F'))
        device.add_state(_state('humidity', '45', 'humidity', '%'))
        return device

    def test_combo_device_creates_one_entity_with_two_entity_states(self):
        entity = HassConverter.create_models_for_hass_device(
            hass_device=self._build_combo_device(),
            add_alarm_events=False,
        )

        state_types = sorted(
            s.entity_state_type_str
            for s in EntityState.objects.filter(entity=entity)
        )
        self.assertEqual(
            state_types,
            sorted([
                str(EntityStateType.HUMIDITY),
                str(EntityStateType.TEMPERATURE),
            ]),
        )

    def test_combo_device_creates_only_one_entity_row(self):
        # Belt-and-suspenders for the grouping path — without the
        # ``_temperature`` / ``_humidity`` suffix-strip the two
        # wire entities would materialize as two separate HI
        # Entities. The single-row assertion pins that they
        # collapse.
        HassConverter.create_models_for_hass_device(
            hass_device=self._build_combo_device(),
            add_alarm_events=False,
        )
        self.assertEqual(
            Entity.objects.filter(
                integration_id=HassMetaData.integration_id,
            ).count(),
            1,
        )


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


class UpdateModelsForHassDeviceContractTests(TestCase):
    """Pin that ``update_models_for_hass_device`` treats user-editable
    fields (``name``, ``entity_type``) as user-owned after creation.
    HASS entities default ``allow_internal_attributes=True`` so the
    operator can edit name/type via the entity-edit modal; once
    edited, refreshes must not silently revert those changes."""

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

    def test_update_preserves_user_edited_name(self):
        existing = Entity.objects.create(
            name='Operator Picked Name',
            entity_type_str='WALL_SWITCH',
        )
        device = self._build_simple_light_device()

        HassConverter.update_models_for_hass_device(
            entity=existing, hass_device=device,
        )

        existing.refresh_from_db()
        self.assertEqual(existing.name, 'Operator Picked Name')

    def test_update_preserves_user_edited_entity_type(self):
        existing = Entity.objects.create(
            name='Kitchen Light',
            entity_type_str='WALL_SWITCH',  # operator chose switch icon for a light
        )
        device = self._build_simple_light_device()

        HassConverter.update_models_for_hass_device(
            entity=existing, hass_device=device,
        )

        existing.refresh_from_db()
        self.assertEqual(existing.entity_type_str, 'WALL_SWITCH')


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


class CameraDeviceVideoSnapshotFlagTests(TestCase):
    """Camera-domain HA devices must surface as Entities with
    ``has_video_snapshot=True``; the gateway uses that flag to gate
    snapshot-URL resolution. Covers create, reconnect, and update
    paths; the update path is the only one that heals pre-existing
    entities imported before the field existed."""

    def _build_camera_device(self, device_id='front_door'):
        api_dict = {
            'entity_id': f'camera.{device_id}',
            'state': 'idle',
            'attributes': {
                'friendly_name': device_id.replace('_', ' ').title(),
                'entity_picture': f'/api/camera_proxy/camera.{device_id}?token=abc',
                'access_token': 'abc',
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

    def _build_non_camera_device(self, device_id='kitchen_light'):
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

    def test_create_sets_flag_for_camera_device(self):
        entity = HassConverter.create_models_for_hass_device(
            hass_device=self._build_camera_device(),
            add_alarm_events=False,
        )
        self.assertTrue(entity.has_video_snapshot)
        self.assertEqual(entity.video_snapshot_stream_fps, 1.0)

    def test_create_leaves_flag_off_for_non_camera_device(self):
        entity = HassConverter.create_models_for_hass_device(
            hass_device=self._build_non_camera_device(),
            add_alarm_events=False,
        )
        self.assertFalse(entity.has_video_snapshot)
        self.assertIsNone(entity.video_snapshot_stream_fps)

    def test_reconnect_sets_flag_on_existing_entity(self):
        existing = Entity.objects.create(
            name='User Renamed Camera',
            entity_type_str='CAMERA',
            has_video_snapshot=False,
            video_snapshot_stream_fps=None,
        )
        HassConverter.create_models_for_hass_device(
            hass_device=self._build_camera_device(),
            add_alarm_events=False,
            entity=existing,
        )
        existing.refresh_from_db()
        self.assertTrue(existing.has_video_snapshot)
        self.assertEqual(existing.video_snapshot_stream_fps, 1.0)

    def test_update_heals_flag_on_existing_camera_entity(self):
        """Pre-PR cameras stay has_video_snapshot=False until the
        next sync cycle calls update_models_for_hass_device, which
        re-derives the flag from the current upstream device."""
        existing = Entity.objects.create(
            name='User Renamed Camera',
            entity_type_str='CAMERA',
            has_video_snapshot=False,
            video_snapshot_stream_fps=None,
        )
        # Set integration key so the converter recognizes the
        # entity as HASS-owned and the update path is well-formed.
        existing.integration_id = HassMetaData.integration_id
        existing.integration_name = 'camera.front_door'
        existing.save()

        HassConverter.update_models_for_hass_device(
            entity=existing,
            hass_device=self._build_camera_device(),
        )

        existing.refresh_from_db()
        self.assertTrue(existing.has_video_snapshot)
        self.assertEqual(existing.video_snapshot_stream_fps, 1.0)

    def test_update_clears_flag_when_device_no_longer_camera(self):
        """Self-healing in the opposite direction: if upstream
        reshapes a device away from the camera domain, the flag
        comes down."""
        existing = Entity.objects.create(
            name='Was a camera',
            entity_type_str='LIGHT',
            has_video_snapshot=True,
            video_snapshot_stream_fps=1.0,
        )
        existing.integration_id = HassMetaData.integration_id
        existing.integration_name = 'light.kitchen_light'
        existing.save()

        HassConverter.update_models_for_hass_device(
            entity=existing,
            hass_device=self._build_non_camera_device(),
        )

        existing.refresh_from_db()
        self.assertFalse(existing.has_video_snapshot)
        self.assertIsNone(existing.video_snapshot_stream_fps)
