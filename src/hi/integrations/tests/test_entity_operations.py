"""
Unit tests for EntityIntegrationOperations.

Only covers behavior that encodes real classification / transformation /
graph-traversal logic. The preserve_with_user_data path is already tested
indirectly via test_integration_synchronizer (which exercises
_remove_entity_intelligently).
"""

import logging

from django.test import TestCase

from hi.apps.attribute.enums import AttributeType, AttributeValueType
from hi.apps.entity.models import Entity, EntityAttribute, EntityState, EntityStateDelegation
from hi.integrations.entity_operations import EntityIntegrationOperations

logging.disable(logging.CRITICAL)


class SummarizeForRemovalTests(TestCase):
    """
    summarize_for_removal classifies entities by whether they have
    user-created attributes (attribute_type_str = CUSTOM). This test
    exercises a mixed case — all other cases are subsumed.
    """

    INTEGRATION_ID = 'summary_test'

    def _make_entity(self, name, user_attribute=False, integration_attribute=False):
        entity = Entity.objects.create(
            name=name,
            entity_type_str='LIGHT',
            integration_id=self.INTEGRATION_ID,
            integration_name=f'device_{name}',
        )
        if user_attribute:
            EntityAttribute.objects.create(
                entity=entity,
                name='User Note',
                value='user-supplied',
                value_type_str=str(AttributeValueType.TEXT),
                attribute_type_str=str(AttributeType.CUSTOM),
                # integration_key_str left NULL → classified as user data
            )
        if integration_attribute:
            EntityAttribute.objects.create(
                entity=entity,
                name='Integration Data',
                value='from-integration',
                value_type_str=str(AttributeValueType.TEXT),
                attribute_type_str=str(AttributeType.PREDEFINED),
                integration_key_str=f'{self.INTEGRATION_ID}:device_{name}',
            )
        return entity

    def test_summary_counts_and_mixed_state(self):
        # One integration-only, one user-data, one both, one bare (no attributes)
        self._make_entity('only_integration', integration_attribute=True)
        self._make_entity('only_user', user_attribute=True)
        self._make_entity('both', user_attribute=True, integration_attribute=True)
        self._make_entity('bare')

        # Also create an entity in a DIFFERENT integration to verify filtering.
        Entity.objects.create(
            name='Other Integration',
            entity_type_str='LIGHT',
            integration_id='different_integration',
        )

        summary = EntityIntegrationOperations.summarize_for_removal(
            integration_id=self.INTEGRATION_ID,
        )

        # Total includes only this integration's entities (4, not 5).
        self.assertEqual(summary.total_count, 4)
        # User-data entities are those with at least one CUSTOM-typed attribute.
        # "bare" has no attributes at all → not user-data.
        # "only_integration" has only PREDEFINED attributes → not user-data.
        # "only_user" and "both" have at least one CUSTOM attribute → user-data.
        self.assertEqual(summary.user_data_count, 2)
        self.assertEqual(summary.deletable_count, 2)
        self.assertTrue(summary.has_mixed_state)


class CollectRemovalClosureTests(TestCase):
    """
    Pure graph-traversal tests for collect_removal_closure.

    Each test constructs a small entity / state / delegation fixture and
    asserts which entities end up in the closure given a seed set. The
    function is integration-agnostic, so these tests work on raw IDs
    rather than going through summarize_for_removal.
    """

    def _make_entity(self, label):
        return Entity.objects.create(
            name=label,
            entity_type_str='LIGHT',
        )

    def _make_state(self, entity):
        return EntityState.objects.create(
            entity=entity,
            entity_state_type_str='DISCRETE',
            name=f'{entity.name} State',
        )

    def _delegate(self, principal_state, delegate_entity):
        return EntityStateDelegation.objects.create(
            entity_state=principal_state,
            delegate_entity=delegate_entity,
        )

    def test_empty_seed_returns_empty_closure(self):
        result = EntityIntegrationOperations.collect_removal_closure(set())
        self.assertEqual(result, set())

    def test_seed_with_no_delegations_is_unchanged(self):
        a = self._make_entity('A')
        b = self._make_entity('B')
        result = EntityIntegrationOperations.collect_removal_closure({a.id, b.id})
        self.assertEqual(result, {a.id, b.id})

    def test_orphanable_delegate_is_added(self):
        """Single principal whose state delegates to a delegate not pointed at by anyone else."""
        principal = self._make_entity('Principal')
        principal_state = self._make_state(principal)
        delegate = self._make_entity('Delegate')
        self._delegate(principal_state, delegate)

        result = EntityIntegrationOperations.collect_removal_closure({principal.id})
        self.assertEqual(result, {principal.id, delegate.id})

    def test_shared_delegate_not_added_when_other_principal_remains(self):
        """Delegate has two principals; only one is in the seed; delegate must remain."""
        seeded_principal = self._make_entity('Seeded')
        seeded_state = self._make_state(seeded_principal)
        other_principal = self._make_entity('Other')
        other_state = self._make_state(other_principal)
        delegate = self._make_entity('SharedDelegate')
        self._delegate(seeded_state, delegate)
        self._delegate(other_state, delegate)

        result = EntityIntegrationOperations.collect_removal_closure({seeded_principal.id})
        self.assertEqual(result, {seeded_principal.id})
        self.assertNotIn(delegate.id, result)

    def test_shared_delegate_added_when_all_principals_in_seed(self):
        """Delegate has two principals; both are in the seed; delegate is included."""
        principal_a = self._make_entity('A')
        state_a = self._make_state(principal_a)
        principal_b = self._make_entity('B')
        state_b = self._make_state(principal_b)
        delegate = self._make_entity('Delegate')
        self._delegate(state_a, delegate)
        self._delegate(state_b, delegate)

        result = EntityIntegrationOperations.collect_removal_closure({principal_a.id, principal_b.id})
        self.assertEqual(result, {principal_a.id, principal_b.id, delegate.id})

    def test_chained_delegations_are_walked(self):
        """A's state delegates to B; B's state delegates to C — closure includes all three."""
        a = self._make_entity('A')
        a_state = self._make_state(a)
        b = self._make_entity('B')
        b_state = self._make_state(b)
        c = self._make_entity('C')
        self._delegate(a_state, b)
        self._delegate(b_state, c)

        result = EntityIntegrationOperations.collect_removal_closure({a.id})
        self.assertEqual(result, {a.id, b.id, c.id})

    def test_diamond_shape_is_walked(self):
        """A delegates to B and C; both B and C delegate to D; closure is all four."""
        a = self._make_entity('A')
        a_state_left = self._make_state(a)
        a_state_right = EntityState.objects.create(
            entity=a, entity_state_type_str='DISCRETE', name='A Right State'
        )
        b = self._make_entity('B')
        b_state = self._make_state(b)
        c = self._make_entity('C')
        c_state = self._make_state(c)
        d = self._make_entity('D')
        self._delegate(a_state_left, b)
        self._delegate(a_state_right, c)
        self._delegate(b_state, d)
        self._delegate(c_state, d)

        result = EntityIntegrationOperations.collect_removal_closure({a.id})
        self.assertEqual(result, {a.id, b.id, c.id, d.id})

    def test_chained_delegate_blocked_by_external_principal(self):
        """A → B → C, but X also delegates to C — C must remain because X is outside the seed."""
        a = self._make_entity('A')
        a_state = self._make_state(a)
        b = self._make_entity('B')
        b_state = self._make_state(b)
        c = self._make_entity('C')
        x = self._make_entity('X')
        x_state = self._make_state(x)
        self._delegate(a_state, b)
        self._delegate(b_state, c)
        self._delegate(x_state, c)

        result = EntityIntegrationOperations.collect_removal_closure({a.id})
        # B has only A as principal → orphan-able. C has B and X as principals;
        # X is not in seed → C must remain.
        self.assertEqual(result, {a.id, b.id})

    def test_cycle_is_handled(self):
        """A's state delegates to B; B's state delegates to A. Seed {A} → closure {A, B}."""
        a = self._make_entity('A')
        a_state = self._make_state(a)
        b = self._make_entity('B')
        b_state = self._make_state(b)
        self._delegate(a_state, b)
        self._delegate(b_state, a)

        result = EntityIntegrationOperations.collect_removal_closure({a.id})
        self.assertEqual(result, {a.id, b.id})


class PreserveWithUserDataFlagTests(TestCase):
    """
    Behavior the disconnected entity must satisfy after preservation:
    user-management flags are restored so the entity behaves like any
    other user-defined entity (deletable, can add custom attributes).
    Integration converters initialize these flags to False to lock down
    integration-managed entities; once disconnected, that lockdown no
    longer applies.
    """

    def test_disconnected_entity_is_user_manageable(self):
        entity = Entity.objects.create(
            name='Locked Down',
            entity_type_str='LIGHT',
            integration_id='test_integration',
            integration_name='locked_device',
            can_user_delete=False,
            can_add_custom_attributes=False,
        )
        # Has user data so it qualifies for preservation.
        EntityAttribute.objects.create(
            entity=entity,
            name='User Note',
            value='keep me',
            value_type_str=str(AttributeValueType.TEXT),
            attribute_type_str=str(AttributeType.CUSTOM),
        )

        EntityIntegrationOperations.preserve_with_user_data(
            entity=entity,
            integration_name='test_integration',
        )

        entity.refresh_from_db()
        self.assertIsNone(entity.integration_id)
        self.assertTrue(entity.can_user_delete)
        self.assertTrue(entity.can_add_custom_attributes)

    def test_disconnected_entity_capabilities_are_suppressed(self):
        """
        After preservation, integration-backed capability flags are turned
        off and the general is_disabled gate is set. This keeps the entity
        out of capability-driven enumerations (e.g., the Cameras sidebar)
        while the per-entity views still respect the raw flags.
        """
        entity = Entity.objects.create(
            name='Camera With Notes',
            entity_type_str='CAMERA',
            integration_id='test_integration',
            integration_name='camera_device',
            has_video_stream=True,
            is_disabled=False,
        )
        EntityAttribute.objects.create(
            entity=entity,
            name='User Note',
            value='lens type X',
            value_type_str=str(AttributeValueType.TEXT),
            attribute_type_str=str(AttributeType.CUSTOM),
        )

        EntityIntegrationOperations.preserve_with_user_data(
            entity=entity,
            integration_name='test_integration',
        )

        entity.refresh_from_db()
        self.assertFalse(entity.has_video_stream)
        self.assertTrue(entity.is_disabled)

    def test_preserve_records_previous_integration_identity(self):
        """
        On disconnect via preservation, the entity's pre-disconnect
        integration identity is captured into previous_integration_id /
        previous_integration_name. This is the signal the
        auto-reconnect path (Issue #281) reads to recognize
        previously-disconnected entities when the same upstream key
        reappears later.
        """
        entity = Entity.objects.create(
            name='Reconnectable',
            entity_type_str='LIGHT',
            integration_id='hass',
            integration_name='light.kitchen',
        )
        EntityAttribute.objects.create(
            entity=entity,
            name='User Note',
            value='keep me',
            value_type_str=str(AttributeValueType.TEXT),
            attribute_type_str=str(AttributeType.CUSTOM),
        )

        EntityIntegrationOperations.preserve_with_user_data(
            entity=entity,
            integration_name='hass',
        )

        entity.refresh_from_db()
        # Active identity is cleared (existing contract).
        self.assertIsNone(entity.integration_id)
        self.assertIsNone(entity.integration_name)
        # Previous identity captures what was cleared (new contract).
        self.assertEqual(entity.previous_integration_id, 'hass')
        self.assertEqual(entity.previous_integration_name, 'light.kitchen')


class FindReconnectCandidatesTests(TestCase):
    """
    find_reconnect_candidates (Issue #281): given the upstream
    IntegrationKeys the synchronizer's primary-match step did not
    match, return a map of upstream_key → matching disconnected
    entity for every key with a unique previous-identity match.
    Ambiguous matches are dropped and noted via result.info_list.
    """

    INTEGRATION_ID = 'hass'

    def _disconnected_entity(self, name, previous_integration_name):
        """Create an entity in the disconnected state — active
        integration_id NULL, previous_integration_id populated."""
        return Entity.objects.create(
            name = name,
            entity_type_str = 'LIGHT',
            previous_integration_id = self.INTEGRATION_ID,
            previous_integration_name = previous_integration_name,
        )

    def _make_upstream_key(self, integration_name, integration_id=None):
        from hi.integrations.transient_models import IntegrationKey
        return IntegrationKey(
            integration_id = integration_id or self.INTEGRATION_ID,
            integration_name = integration_name,
        )

    def test_returns_match_for_unique_secondary(self):
        entity = self._disconnected_entity(
            name = '[Disconnected] Kitchen Light',
            previous_integration_name = 'light.kitchen',
        )
        upstream_key = self._make_upstream_key('light.kitchen')

        candidates = EntityIntegrationOperations.find_reconnect_candidates(
            integration_id = self.INTEGRATION_ID,
            upstream_keys = [ upstream_key ],
        )

        self.assertEqual(candidates, {upstream_key: entity})

    def test_ambiguous_match_is_dropped_and_noted(self):
        """Two disconnected entities sharing the same previous
        identity → upstream_key absent from result map; operator
        breadcrumb in result.info_list."""
        self._disconnected_entity(
            name = '[Disconnected] Kitchen Light A',
            previous_integration_name = 'light.kitchen',
        )
        self._disconnected_entity(
            name = '[Disconnected] Kitchen Light B',
            previous_integration_name = 'light.kitchen',
        )
        upstream_key = self._make_upstream_key('light.kitchen')

        from hi.integrations.sync_result import IntegrationSyncResult
        result = IntegrationSyncResult(title='Test')

        candidates = EntityIntegrationOperations.find_reconnect_candidates(
            integration_id = self.INTEGRATION_ID,
            upstream_keys = [ upstream_key ],
            result = result,
        )

        self.assertEqual(candidates, {})
        self.assertTrue(any('share that previous identity' in note
                            for note in result.info_list))

    def test_does_not_match_across_integrations(self):
        """An entity disconnected from HASS must not match an upstream
        key from ZM, even if the integration_name coincides."""
        self._disconnected_entity(
            name = '[Disconnected] foo',
            previous_integration_name = 'foo',
        )
        zm_upstream_key = self._make_upstream_key('foo', integration_id='zoneminder')

        candidates = EntityIntegrationOperations.find_reconnect_candidates(
            integration_id = 'zoneminder',
            upstream_keys = [ zm_upstream_key ],
        )

        self.assertEqual(candidates, {})

    def test_no_match_returns_empty_dict(self):
        upstream_key = self._make_upstream_key('light.unknown')

        candidates = EntityIntegrationOperations.find_reconnect_candidates(
            integration_id = self.INTEGRATION_ID,
            upstream_keys = [ upstream_key ],
        )

        self.assertEqual(candidates, {})

    def test_empty_upstream_set_short_circuits_without_db_query(self):
        with self.assertNumQueries(0):
            candidates = EntityIntegrationOperations.find_reconnect_candidates(
                integration_id = self.INTEGRATION_ID,
                upstream_keys = [],
            )

        self.assertEqual(candidates, {})

    def test_secondary_lookup_is_a_single_batched_query(self):
        """Many upstream keys → one DB query for the candidate scan,
        regardless of how many keys are passed."""
        for i in range(5):
            self._disconnected_entity(
                name = f'[Disconnected] light_{i}',
                previous_integration_name = f'light.{i}',
            )
        upstream_keys = [ self._make_upstream_key(f'light.{i}') for i in range(5) ]

        with self.assertNumQueries(1):
            candidates = EntityIntegrationOperations.find_reconnect_candidates(
                integration_id = self.INTEGRATION_ID,
                upstream_keys = upstream_keys,
            )

        self.assertEqual(len(candidates), 5)


class PreserveWithUserDataNamePreservationTests(TestCase):
    """
    Disconnect (preserve_with_user_data) signals the detached state
    structurally — via the previous_integration_* columns — and does
    NOT mutate the entity name. This pins the contract: any name the
    operator sees post-detach is the name the entity had before
    detach.
    """

    def test_disconnect_does_not_mutate_entity_name(self):
        entity = Entity.objects.create(
            name='User Edited Name',
            entity_type_str='LIGHT',
            integration_id='hass',
            integration_name='light.kitchen',
        )
        EntityAttribute.objects.create(
            entity=entity,
            name='Custom Note',
            value='retain me',
            value_type_str=str(AttributeValueType.TEXT),
            attribute_type_str=str(AttributeType.CUSTOM),
        )

        EntityIntegrationOperations.preserve_with_user_data(
            entity=entity,
            integration_name='hass',
        )

        entity.refresh_from_db()
        self.assertEqual(entity.name, 'User Edited Name')
        # Detached state is signaled by the previous_integration_* columns.
        self.assertEqual(entity.previous_integration_id, 'hass')
        self.assertIsNone(entity.integration_id)
