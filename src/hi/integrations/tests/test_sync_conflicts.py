"""
Tests for sync-time integration-key conflict handling (Issue #422).

``IntegrationSyncConflictDetector`` decides which upstream items
claim keys whose components a different HI entity owns;
``IntegrationConnector.exclude_conflicting_items`` drops both sides
of each conflict from the sync maps and reports it.
"""
import logging
from types import SimpleNamespace

from django.test import TestCase

from hi.apps.control.models import Controller
from hi.apps.entity.models import Entity, EntityState
from hi.apps.sense.models import Sensor
from hi.integrations.connector.integration_connector import IntegrationConnector
from hi.integrations.connector.sync_conflicts import (
    IntegrationSyncConflict,
    IntegrationSyncConflictDetector,
)
from hi.integrations.connector.sync_result import IntegrationSyncResult
from hi.integrations.transient_models import IntegrationKey

logging.disable(logging.CRITICAL)

INTEGRATION_ID = 'test_integration'
INTEGRATION_LABEL = 'Test Integration'


def _key(name: str) -> IntegrationKey:
    return IntegrationKey(integration_id=INTEGRATION_ID, integration_name=name)


class _ConflictTestSynchronizer(IntegrationConnector):

    def get_metadata(self):
        return SimpleNamespace(integration_id=INTEGRATION_ID, label=INTEGRATION_LABEL)

    def _sync_impl(self, is_initial_connect=False):
        raise NotImplementedError


class _ConflictTestCase(TestCase):

    def _create_entity(self, name, integration_name, sensor_names=(), controller_names=()):
        entity = Entity.objects.create(
            name=name,
            entity_type_str='LIGHT',
            integration_id=INTEGRATION_ID,
            integration_name=integration_name,
        )
        entity_state = EntityState.objects.create(
            entity=entity,
            entity_state_type_str='ON_OFF',
            name=f'{name} State',
        )
        for sensor_name in sensor_names:
            Sensor.objects.create(
                name=sensor_name,
                entity_state=entity_state,
                sensor_type_str='DISCRETE',
                integration_id=INTEGRATION_ID,
                integration_name=sensor_name,
            )
        for controller_name in controller_names:
            Controller.objects.create(
                name=controller_name,
                entity_state=entity_state,
                controller_type_str='DISCRETE',
                integration_id=INTEGRATION_ID,
                integration_name=controller_name,
            )
        return entity


class IntegrationSyncConflictDetectorTests(_ConflictTestCase):

    def _find_conflicts(self, upstream_key_to_claim_keys, integration_key_to_entity,
                        component_key_to_claim_key=lambda component_key: component_key):
        return IntegrationSyncConflictDetector.find_conflicts(
            upstream_key_to_claim_keys=upstream_key_to_claim_keys,
            integration_key_to_entity=integration_key_to_entity,
            claim_key_to_owners=IntegrationSyncConflictDetector.load_claim_owners(
                integration_id=INTEGRATION_ID,
                component_key_to_claim_key=component_key_to_claim_key,
            ),
        )

    def test_keys_owned_by_matched_entity_are_not_conflicts(self):
        entity = self._create_entity(
            'Porch Light', 'insteon:aa.bb.cc',
            sensor_names=['light.porch'], controller_names=['light.porch'],
        )

        conflicts = self._find_conflicts(
            upstream_key_to_claim_keys={
                _key('insteon:aa.bb.cc'): {_key('light.porch'), _key('light.porch~brightness')},
            },
            integration_key_to_entity={_key('insteon:aa.bb.cc'): entity},
        )

        self.assertEqual(conflicts, [])

    def test_new_item_claiming_keys_of_another_entity_conflicts(self):
        """The regrouped-device case: same HA states, new device id."""
        owner = self._create_entity(
            'Side Deck Motion', 'insteon:28.5b.c1',
            sensor_names=['motion_28_5b_c1_motion', 'motion_28_5b_c1_battery'],
        )

        conflicts = self._find_conflicts(
            upstream_key_to_claim_keys={
                _key('motion_sensor_28_5b_c1'): {
                    _key('motion_28_5b_c1_motion'),
                    _key('motion_28_5b_c1_battery'),
                    _key('motion_28_5b_c1_light'),
                },
            },
            integration_key_to_entity={_key('insteon:28.5b.c1'): owner},
        )

        self.assertEqual(len(conflicts), 1)
        conflict = conflicts[0]
        self.assertEqual(conflict.upstream_key, _key('motion_sensor_28_5b_c1'))
        self.assertEqual(conflict.owner_entity.id, owner.id)
        self.assertEqual(
            conflict.claim_keys,
            [_key('motion_28_5b_c1_battery'), _key('motion_28_5b_c1_motion')],
        )

    def test_key_moving_between_two_existing_entities_conflicts(self):
        losing = self._create_entity('Keypad A', 'insteon:11.11.11', sensor_names=['switch.button_a'])
        gaining = self._create_entity('Keypad B', 'insteon:22.22.22', sensor_names=['switch.button_b'])

        conflicts = self._find_conflicts(
            upstream_key_to_claim_keys={
                _key('insteon:11.11.11'): set(),
                _key('insteon:22.22.22'): {_key('switch.button_a'), _key('switch.button_b')},
            },
            integration_key_to_entity={
                _key('insteon:11.11.11'): losing,
                _key('insteon:22.22.22'): gaining,
            },
        )

        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0].upstream_key, _key('insteon:22.22.22'))
        self.assertEqual(conflicts[0].owner_entity.id, losing.id)
        self.assertEqual(conflicts[0].claim_keys, [_key('switch.button_a')])

    def test_one_conflict_per_foreign_owner(self):
        self._create_entity('Owner One', 'device_1', sensor_names=['state_1'])
        self._create_entity('Owner Two', 'device_2', controller_names=['state_2'])

        conflicts = self._find_conflicts(
            upstream_key_to_claim_keys={
                _key('merged_device'): {_key('state_1'), _key('state_2')},
            },
            integration_key_to_entity={},
        )

        self.assertEqual(
            sorted(conflict.owner_entity.name for conflict in conflicts),
            ['Owner One', 'Owner Two'],
        )


    def test_claim_key_mapping_catches_components_the_item_no_longer_implies(self):
        """An upstream record reported with fewer attributes implies
        fewer derived components (e.g., an unavailable HA fan loses
        its oscillating/direction substates). Mapping owned components
        to their record's claim key still detects the takeover."""
        owner = self._create_entity(
            'Bedroom Fan', 'insteon:aa.bb.cc',
            controller_names=['fan.bedroom~speed', 'fan.bedroom~oscillating'],
        )

        conflicts = self._find_conflicts(
            upstream_key_to_claim_keys={_key('bedroom_fan'): {_key('fan.bedroom')}},
            integration_key_to_entity={_key('insteon:aa.bb.cc'): owner},
            component_key_to_claim_key=lambda component_key: _key(
                component_key.integration_name.split('~', 1)[0],
            ),
        )

        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0].owner_entity.id, owner.id)
        self.assertEqual(conflicts[0].claim_keys, [_key('fan.bedroom')])

    def test_sensor_and_controller_owners_of_one_key_are_both_reported(self):
        """Keys are unique per component model, so an inconsistent DB
        can hold the same key on a Sensor of one entity and a
        Controller of another; neither owner may be masked."""
        sensor_owner = self._create_entity('Sensor Owner', 'device_1', sensor_names=['switch.shared'])
        controller_owner = self._create_entity(
            'Controller Owner', 'device_2', controller_names=['switch.shared'],
        )

        conflicts = self._find_conflicts(
            upstream_key_to_claim_keys={_key('device_3'): {_key('switch.shared')}},
            integration_key_to_entity={},
        )

        self.assertEqual(
            [conflict.owner_entity.id for conflict in conflicts],
            [sensor_owner.id, controller_owner.id],
        )

    def test_message_for_owner_without_key_points_at_hi_side(self):
        owner = self._create_entity('Broken Row', 'device_1', sensor_names=['switch.x'])
        owner.integration_name = None

        message = IntegrationSyncConflict(
            upstream_key=_key('device_2'),
            owner_entity=owner,
            claim_keys=[_key('switch.x')],
        ).to_message(integration_label=INTEGRATION_LABEL)

        self.assertIn('no valid integration key', message)
        self.assertNotIn(f'resolve this in {INTEGRATION_LABEL}', message)


class ExcludeConflictingItemsTests(_ConflictTestCase):

    def test_conflicting_item_and_owner_dropped_from_both_maps(self):
        owner = self._create_entity(
            'Garage Outer Door', 'insteon:2d.79.55', sensor_names=['binary_sensor.garage_door'],
        )
        bystander = self._create_entity(
            'Porch Light', 'insteon:aa.bb.cc', sensor_names=['light.porch'],
        )
        stale = self._create_entity('Old Keypad', 'insteon:23.d0.86', sensor_names=['light.old_keypad'])

        integration_key_to_upstream = {
            _key('open_close_sensor_2d_79_55'): 'regrouped door',
            _key('insteon:aa.bb.cc'): 'porch light',
        }
        integration_key_to_entity = {
            _key('insteon:2d.79.55'): owner,
            _key('insteon:aa.bb.cc'): bystander,
            _key('insteon:23.d0.86'): stale,
        }
        result = IntegrationSyncResult(title='Sync')

        _ConflictTestSynchronizer().exclude_conflicting_items(
            integration_key_to_upstream=integration_key_to_upstream,
            integration_key_to_entity=integration_key_to_entity,
            upstream_key_to_claim_keys={
                _key('open_close_sensor_2d_79_55'): {_key('binary_sensor.garage_door')},
                _key('insteon:aa.bb.cc'): {_key('light.porch')},
            },
            result=result,
        )

        # Neither the regrouped item is created nor its owner removed;
        # unrelated items (including a genuine removal) are untouched.
        self.assertEqual(list(integration_key_to_upstream), [_key('insteon:aa.bb.cc')])
        self.assertEqual(
            set(integration_key_to_entity),
            {_key('insteon:aa.bb.cc'), _key('insteon:23.d0.86')},
        )
        self.assertEqual(len(result.conflict_list), 1)
        message = result.conflict_list[0]
        for expected in (
                'open_close_sensor_2d_79_55',
                'binary_sensor.garage_door',
                'Garage Outer Door',
                'insteon:2d.79.55',
                INTEGRATION_LABEL,
        ):
            self.assertIn(expected, message)

    def test_owner_still_upstream_is_not_updated_either(self):
        """Key moving between two existing entities: both are left
        out of the update pass, not just the claiming one."""
        losing = self._create_entity('Keypad A', 'insteon:11.11.11', sensor_names=['switch.button_a'])
        gaining = self._create_entity('Keypad B', 'insteon:22.22.22')

        integration_key_to_upstream = {
            _key('insteon:11.11.11'): 'keypad a',
            _key('insteon:22.22.22'): 'keypad b',
        }
        integration_key_to_entity = {
            _key('insteon:11.11.11'): losing,
            _key('insteon:22.22.22'): gaining,
        }
        result = IntegrationSyncResult(title='Sync')

        _ConflictTestSynchronizer().exclude_conflicting_items(
            integration_key_to_upstream=integration_key_to_upstream,
            integration_key_to_entity=integration_key_to_entity,
            upstream_key_to_claim_keys={
                _key('insteon:11.11.11'): set(),
                _key('insteon:22.22.22'): {_key('switch.button_a')},
            },
            result=result,
        )

        self.assertEqual(integration_key_to_upstream, {})
        self.assertEqual(integration_key_to_entity, {})

    def test_no_conflicts_leaves_maps_and_result_unchanged(self):
        entity = self._create_entity('Porch Light', 'insteon:aa.bb.cc', sensor_names=['light.porch'])
        integration_key_to_upstream = {_key('insteon:aa.bb.cc'): 'porch light'}
        integration_key_to_entity = {_key('insteon:aa.bb.cc'): entity}
        result = IntegrationSyncResult(title='Sync')

        _ConflictTestSynchronizer().exclude_conflicting_items(
            integration_key_to_upstream=integration_key_to_upstream,
            integration_key_to_entity=integration_key_to_entity,
            upstream_key_to_claim_keys={_key('insteon:aa.bb.cc'): {_key('light.porch')}},
            result=result,
        )

        self.assertEqual(list(integration_key_to_upstream), [_key('insteon:aa.bb.cc')])
        self.assertEqual(list(integration_key_to_entity), [_key('insteon:aa.bb.cc')])
        self.assertEqual(result.conflict_list, [])
