"""
Unit tests for EventDefinitionOperations.

Pins the integration-scoped deletion semantics: only EventDefinition
rows whose own integration_id matches are removed, even when a
user-owned EventDefinition or one owned by a different integration
references the same EntityState.
"""

import logging

from django.test import TestCase

from hi.apps.entity.models import Entity, EntityState
from hi.apps.event.models import AlarmAction, EventClause, EventDefinition

from hi.integrations.event_definition_operations import EventDefinitionOperations

logging.disable(logging.CRITICAL)


class _FixtureMixin:
    """
    Small builders shared across the test classes. Kept here rather
    than in BaseTestCase because they're only useful to this module.
    """

    INTEGRATION_ID = 'test_integration'
    OTHER_INTEGRATION_ID = 'other_integration'

    def _make_entity(self, name, integration_id=INTEGRATION_ID, integration_name=None):
        return Entity.objects.create(
            name=name,
            entity_type_str='LIGHT',
            integration_id=integration_id,
            integration_name=integration_name or f'device_{name}',
        )

    def _make_state(self, entity, name='state'):
        return EntityState.objects.create(
            entity=entity,
            entity_state_type_str='ON_OFF',
            name=name,
        )

    def _make_event_def(self, name, integration_id=INTEGRATION_ID, integration_name=None):
        return EventDefinition.objects.create(
            name=name,
            event_type_str='SECURITY',
            event_window_secs=60,
            dedupe_window_secs=300,
            integration_id=integration_id,
            integration_name=integration_name,
        )

    def _attach_clause(self, event_def, entity_state, value='on'):
        return EventClause.objects.create(
            event_definition=event_def,
            entity_state=entity_state,
            value=value,
        )


class DeleteForIntegrationTests(_FixtureMixin, TestCase):

    def test_deletes_only_matching_integration(self):
        # Three EventDefinitions: target integration, other integration, user-owned.
        target = self._make_event_def('target', integration_id=self.INTEGRATION_ID)
        other = self._make_event_def('other', integration_id=self.OTHER_INTEGRATION_ID)
        user_owned = self._make_event_def('user', integration_id=None)

        deleted = EventDefinitionOperations.delete_for_integration(self.INTEGRATION_ID)

        self.assertEqual(deleted, 1)
        self.assertFalse(EventDefinition.objects.filter(id=target.id).exists())
        self.assertTrue(EventDefinition.objects.filter(id=other.id).exists())
        self.assertTrue(EventDefinition.objects.filter(id=user_owned.id).exists())

    def test_no_match_returns_zero(self):
        self._make_event_def('user', integration_id=None)
        self.assertEqual(
            EventDefinitionOperations.delete_for_integration(self.INTEGRATION_ID), 0,
        )

    def test_empty_integration_id_returns_zero_without_deleting(self):
        # Defensive: caller passing None/empty must not nuke every user-owned
        # EventDefinition (those have integration_id=NULL and would match a
        # naive filter on integration_id=None).
        user_owned = self._make_event_def('user', integration_id=None)

        deleted = EventDefinitionOperations.delete_for_integration('')
        self.assertEqual(deleted, 0)
        self.assertTrue(EventDefinition.objects.filter(id=user_owned.id).exists())

        deleted = EventDefinitionOperations.delete_for_integration(None)
        self.assertEqual(deleted, 0)
        self.assertTrue(EventDefinition.objects.filter(id=user_owned.id).exists())


class DeleteForEntityTests(_FixtureMixin, TestCase):

    def test_deletes_integration_event_def_referencing_entity(self):
        entity = self._make_entity('cam')
        state = self._make_state(entity)
        event_def = self._make_event_def('cam alarm')
        self._attach_clause(event_def, state)

        deleted = EventDefinitionOperations.delete_for_entity(entity)

        self.assertEqual(deleted, 1)
        self.assertFalse(EventDefinition.objects.filter(id=event_def.id).exists())

    def test_leaves_user_owned_event_def_untouched(self):
        entity = self._make_entity('cam')
        state = self._make_state(entity)
        user_event_def = self._make_event_def('user rule', integration_id=None)
        self._attach_clause(user_event_def, state)

        deleted = EventDefinitionOperations.delete_for_entity(entity)

        self.assertEqual(deleted, 0)
        self.assertTrue(EventDefinition.objects.filter(id=user_event_def.id).exists())

    def test_leaves_other_integration_event_def_untouched(self):
        # An EventDefinition owned by a *different* integration that happens
        # to reference this entity's state must not be deleted by a disconnect
        # of this integration. (Rare in practice, but the predicate must
        # respect ownership.)
        entity = self._make_entity('cam')
        state = self._make_state(entity)
        other_event_def = self._make_event_def('other', integration_id=self.OTHER_INTEGRATION_ID)
        self._attach_clause(other_event_def, state)

        deleted = EventDefinitionOperations.delete_for_entity(entity)

        self.assertEqual(deleted, 0)
        self.assertTrue(EventDefinition.objects.filter(id=other_event_def.id).exists())

    def test_no_op_when_entity_has_no_integration(self):
        # Entity already detached (integration_id NULL): caller can invoke
        # delete_for_entity unconditionally and get a clean no-op.
        entity = Entity.objects.create(name='detached', entity_type_str='LIGHT')
        state = self._make_state(entity)
        event_def = self._make_event_def('orphan-but-integration-owned')
        self._attach_clause(event_def, state)

        deleted = EventDefinitionOperations.delete_for_entity(entity)

        self.assertEqual(deleted, 0)
        self.assertTrue(EventDefinition.objects.filter(id=event_def.id).exists())

    def test_event_def_with_no_matching_clause_untouched(self):
        # Integration-owned EventDefinition whose clauses do NOT reference
        # this entity's states is left alone — delete_for_entity is scoped
        # to entities, not to whole-integration cleanup.
        entity = self._make_entity('cam')
        other_entity = self._make_entity('other_cam')
        other_state = self._make_state(other_entity)
        event_def = self._make_event_def('other rule')
        self._attach_clause(event_def, other_state)

        deleted = EventDefinitionOperations.delete_for_entity(entity)

        self.assertEqual(deleted, 0)
        self.assertTrue(EventDefinition.objects.filter(id=event_def.id).exists())

    def test_cascade_removes_clauses_and_actions(self):
        # Regression: the model-level CASCADE on EventClause/AlarmAction
        # parents should remove children when the parent EventDefinition
        # is deleted by the helper.
        entity = self._make_entity('cam')
        state = self._make_state(entity)
        event_def = self._make_event_def('cam alarm')
        clause = self._attach_clause(event_def, state)
        action = AlarmAction.objects.create(
            event_definition=event_def,
            security_level_str='HIGH',
            alarm_level_str='CRITICAL',
            alarm_lifetime_secs=600,
        )

        EventDefinitionOperations.delete_for_entity(entity)

        self.assertFalse(EventClause.objects.filter(id=clause.id).exists())
        self.assertFalse(AlarmAction.objects.filter(id=action.id).exists())


class DeleteForEntityClosureTests(_FixtureMixin, TestCase):

    def test_batch_deletes_across_multiple_entities(self):
        entity_a = self._make_entity('a')
        entity_b = self._make_entity('b')
        state_a = self._make_state(entity_a)
        state_b = self._make_state(entity_b)

        ed_a = self._make_event_def('rule a')
        self._attach_clause(ed_a, state_a)
        ed_b = self._make_event_def('rule b')
        self._attach_clause(ed_b, state_b)

        deleted = EventDefinitionOperations.delete_for_entity_closure(
            entity_ids=[entity_a.id, entity_b.id],
            integration_id=self.INTEGRATION_ID,
        )

        self.assertEqual(deleted, 2)
        self.assertFalse(EventDefinition.objects.filter(id__in=[ed_a.id, ed_b.id]).exists())

    def test_distinct_when_event_def_spans_multiple_entities(self):
        # An EventDefinition with clauses on two different entities, both in
        # the closure, must only be counted/deleted once.
        entity_a = self._make_entity('a')
        entity_b = self._make_entity('b')
        state_a = self._make_state(entity_a)
        state_b = self._make_state(entity_b)

        ed = self._make_event_def('multi-clause')
        self._attach_clause(ed, state_a, value='on')
        self._attach_clause(ed, state_b, value='off')

        deleted = EventDefinitionOperations.delete_for_entity_closure(
            entity_ids=[entity_a.id, entity_b.id],
            integration_id=self.INTEGRATION_ID,
        )

        self.assertEqual(deleted, 1)
        self.assertFalse(EventDefinition.objects.filter(id=ed.id).exists())

    def test_partial_closure_still_matches(self):
        # An integration EventDefinition with clauses on two entities where
        # only ONE is in the closure: still deleted (any matching clause
        # qualifies). Consistent with policy — the EventDefinition's purpose
        # was tied to the integration, and one of its referenced states is
        # disappearing.
        entity_a = self._make_entity('a')
        entity_b = self._make_entity('b')
        state_a = self._make_state(entity_a)
        state_b = self._make_state(entity_b)

        ed = self._make_event_def('multi-clause partial')
        self._attach_clause(ed, state_a, value='on')
        self._attach_clause(ed, state_b, value='off')

        deleted = EventDefinitionOperations.delete_for_entity_closure(
            entity_ids=[entity_a.id],
            integration_id=self.INTEGRATION_ID,
        )

        self.assertEqual(deleted, 1)
        self.assertFalse(EventDefinition.objects.filter(id=ed.id).exists())

    def test_empty_inputs_return_zero(self):
        self._make_event_def('user', integration_id=None)

        self.assertEqual(
            EventDefinitionOperations.delete_for_entity_closure(
                entity_ids=[], integration_id=self.INTEGRATION_ID,
            ), 0,
        )
        self.assertEqual(
            EventDefinitionOperations.delete_for_entity_closure(
                entity_ids=[1, 2, 3], integration_id=None,
            ), 0,
        )
        self.assertEqual(
            EventDefinitionOperations.delete_for_entity_closure(
                entity_ids=[1, 2, 3], integration_id='',
            ), 0,
        )

    def test_user_owned_with_clause_on_closure_entity_untouched(self):
        # Symmetric to delete_for_entity's user-owned test: user-owned
        # EventDefinitions are never touched, even when the closure
        # includes the entity their clauses reference.
        entity = self._make_entity('cam')
        state = self._make_state(entity)
        user_event_def = self._make_event_def('user rule', integration_id=None)
        self._attach_clause(user_event_def, state)

        deleted = EventDefinitionOperations.delete_for_entity_closure(
            entity_ids=[entity.id],
            integration_id=self.INTEGRATION_ID,
        )

        self.assertEqual(deleted, 0)
        self.assertTrue(EventDefinition.objects.filter(id=user_event_def.id).exists())
