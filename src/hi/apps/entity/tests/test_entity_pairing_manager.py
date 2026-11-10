import logging

from hi.apps.entity.entity_pairing_manager import EntityPairingError, EntityPairingManager
from hi.apps.entity.entity_state_labels import entity_state_short_labels
from hi.apps.entity.enums import EntityPairingType
from hi.apps.entity.models import Entity, EntityState, EntityStateDelegation
from hi.testing.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class PairingTestMixin:

    def _create_principal(self, name, state_names):
        principal = Entity.objects.create(name=name, entity_type_str='IRRIGATION_CONTROLLER')
        states = [
            EntityState.objects.create(entity=principal, entity_state_type_str='ON_OFF', name=state_name)
            for state_name in state_names
        ]
        return principal, states

    def _create_area(self, name):
        return Entity.objects.create(name=name, entity_type_str='AREA')

    def _delegate(self, entity_state, delegate_entity):
        EntityStateDelegation.objects.create(entity_state=entity_state, delegate_entity=delegate_entity)

    def _delegation_pairs(self, principal):
        return set(
            EntityStateDelegation.objects.filter(entity_state__entity=principal)
            .values_list('entity_state_id', 'delegate_entity_id')
        )


class TestSetDelegatedStates(PairingTestMixin, BaseTestCase):

    def setUp(self):
        super().setUp()
        self.principal, self.zones = self._create_principal(
            'Sprinkler', ['EZFlora Front Lawn', 'EZFlora Back Lawn', 'EZFlora Side Yard'],
        )
        self.front = self._create_area('Front')
        self.back = self._create_area('Back')
        self.manager = EntityPairingManager()

    def test_sets_exactly_the_requested_delegations(self):
        # Start from an entity-level pairing: every zone to both areas.
        for zone in self.zones:
            self._delegate(zone, self.front)
            self._delegate(zone, self.back)

        self.manager.set_delegated_states(
            principal_entity=self.principal,
            delegate_entity_id_to_state_ids={
                self.front.id: {self.zones[0].id},
                self.back.id: {self.zones[1].id, self.zones[2].id},
            },
        )

        self.assertEqual(self._delegation_pairs(self.principal), {
            (self.zones[0].id, self.front.id),
            (self.zones[1].id, self.back.id),
            (self.zones[2].id, self.back.id),
        })

    def test_state_may_go_to_several_delegates(self):
        self.manager.set_delegated_states(
            principal_entity=self.principal,
            delegate_entity_id_to_state_ids={
                self.front.id: {self.zones[0].id},
                self.back.id: {self.zones[0].id},
            },
        )

        self.assertEqual(self._delegation_pairs(self.principal), {
            (self.zones[0].id, self.front.id),
            (self.zones[0].id, self.back.id),
        })

    def test_empty_or_absent_delegate_is_unpaired(self):
        self._delegate(self.zones[0], self.front)
        self._delegate(self.zones[1], self.back)

        self.manager.set_delegated_states(
            principal_entity=self.principal,
            delegate_entity_id_to_state_ids={self.front.id: set()},
        )

        self.assertEqual(self._delegation_pairs(self.principal), set())

    def test_other_principals_delegations_are_untouched(self):
        other_principal, other_states = self._create_principal('Motion', ['Motion'])
        self._delegate(other_states[0], self.front)

        self.manager.set_delegated_states(
            principal_entity=self.principal,
            delegate_entity_id_to_state_ids={self.front.id: {self.zones[0].id}},
        )

        self.assertEqual(self._delegation_pairs(other_principal), {(other_states[0].id, self.front.id)})

    def test_rejects_state_of_another_entity_without_changes(self):
        _, other_states = self._create_principal('Motion', ['Motion'])
        self._delegate(self.zones[0], self.front)

        with self.assertRaises(EntityPairingError):
            self.manager.set_delegated_states(
                principal_entity=self.principal,
                delegate_entity_id_to_state_ids={self.back.id: {other_states[0].id}},
            )

        self.assertEqual(self._delegation_pairs(self.principal), {(self.zones[0].id, self.front.id)})

    def test_rejects_delegate_with_its_own_states(self):
        stateful, _ = self._create_principal('Motion', ['Motion'])

        with self.assertRaises(EntityPairingError):
            self.manager.set_delegated_states(
                principal_entity=self.principal,
                delegate_entity_id_to_state_ids={stateful.id: {self.zones[0].id}},
            )

        self.assertEqual(self._delegation_pairs(self.principal), set())


class TestEntityPairingCoverage(PairingTestMixin, BaseTestCase):

    def setUp(self):
        super().setUp()
        self.principal, self.zones = self._create_principal(
            'Sprinkler', ['EZFlora Front Lawn', 'EZFlora Back Lawn', 'EZFlora Side Yard'],
        )
        self.front = self._create_area('Front')
        self.back = self._create_area('Back')
        self._delegate(self.zones[0], self.front)
        for zone in self.zones:
            self._delegate(zone, self.back)
        self.manager = EntityPairingManager()

    def test_principal_side_reports_coverage_per_delegate(self):
        pairings = {
            p.paired_entity: p for p in self.manager.get_entity_pairing_list(entity=self.principal)
        }

        self.assertEqual(pairings[self.front].pairing_type, EntityPairingType.DELEGATE)
        self.assertTrue(pairings[self.front].is_partial)
        self.assertEqual(pairings[self.front].delegated_state_labels, ['Front Lawn'])
        self.assertFalse(pairings[self.back].is_partial)

    def test_delegate_side_reports_received_states(self):
        pairing_list = self.manager.get_entity_pairing_list(entity=self.front)

        self.assertEqual(len(pairing_list), 1)
        pairing = pairing_list[0]
        self.assertEqual(pairing.paired_entity, self.principal)
        self.assertEqual(pairing.pairing_type, EntityPairingType.PRINCIPAL)
        self.assertTrue(pairing.is_partial)
        self.assertEqual(pairing.delegated_state_labels, ['Front Lawn'])


class TestEntityStateShortLabels(PairingTestMixin, BaseTestCase):

    def _labels(self, state_names):
        _, states = self._create_principal('Device', state_names)
        short_labels = entity_state_short_labels(states)
        return [short_labels[state.id] for state in states]

    def test_strips_shared_leading_words(self):
        self.assertEqual(
            self._labels(['EZFlora Front Lawn', 'EZFlora Front Bed', 'EZFlora Side Yard']),
            ['Front Lawn', 'Front Bed', 'Side Yard'],
        )

    def test_does_not_split_a_word(self):
        self.assertEqual(self._labels(['Zone10', 'Zone11']), ['Zone10', 'Zone11'])

    def test_name_equal_to_prefix_keeps_full_name(self):
        self.assertEqual(self._labels(['Fan', 'Fan Speed']), ['Fan', 'Fan Speed'])

    def test_single_state_keeps_full_name(self):
        self.assertEqual(self._labels(['EZFlora Front Lawn']), ['EZFlora Front Lawn'])
