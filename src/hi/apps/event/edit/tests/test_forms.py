import logging

from django import forms
from django.http import QueryDict

from hi.apps.entity.models import Entity, EntityState
from hi.apps.event.edit.forms import EventClauseForm
from hi.apps.event.models import EventClause, EventDefinition
from hi.testing.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestEventClauseFormValidation(BaseTestCase):
    """The matcher silently no-ops on non-numeric values under numeric
    operators (LT / LTE / GT / GTE) — without form-time rejection, a
    user could save a clause that never fires. Validate the form-level
    guard so the silent-failure mode can't slip past the UI."""

    def setUp(self):
        super().setUp()
        entity = Entity.objects.create(
            name = 'Test Entity',
            entity_type_str = 'switch',
        )
        self.entity_state = EntityState.objects.create(
            entity = entity,
            name = 'Battery',
            entity_state_type_str = 'battery_level',
        )
        return

    def test_non_numeric_value_with_numeric_operator_is_rejected(self):
        # Cover each numeric operator's narrowing — they all share the
        # parse-and-validate path, but pin every one so adding a fifth
        # to the enum and missing the form guard surfaces here.
        for op_str in ( 'lt', 'lte', 'gt', 'gte' ):
            with self.subTest( op_str = op_str ):
                form = EventClauseForm( data = {
                    'entity_state': str( self.entity_state.id ),
                    'value_operator_str': op_str,
                    'value': 'abc',
                })
                self.assertFalse( form.is_valid() )
                self.assertIn( 'value', form.errors )
            continue
        return

    def test_numeric_value_with_lt_operator_is_accepted(self):
        form = EventClauseForm( data = {
            'entity_state': str( self.entity_state.id ),
            'value_operator_str': 'lt',
            'value': '20.5',
        })
        self.assertTrue( form.is_valid(), msg = form.errors )
        return


class TestEventClauseFormDiscreteOperators(BaseTestCase):
    """NEQ and IN operate against discrete string values, not numeric
    thresholds. The form's numeric-value guard must not reject them,
    and IN's multi-select POST must serialize to the model's
    comma-delimited storage shape."""

    def setUp(self):
        super().setUp()
        entity = Entity.objects.create(
            name = 'Test Camera',
            entity_type_str = 'camera',
        )
        self.discrete_state = EntityState.objects.create(
            entity = entity,
            name = 'Object Presence',
            entity_state_type_str = 'object_presence',
        )
        return

    def test_non_numeric_value_with_neq_operator_is_accepted(self):
        form = EventClauseForm( data = {
            'entity_state': str( self.discrete_state.id ),
            'value_operator_str': 'neq',
            'value': 'object_none',
        })
        self.assertTrue( form.is_valid(), msg = form.errors )
        return

    def test_multi_select_values_serialize_to_comma_delimited_for_in(self):
        # Browser POSTs ``<select multiple>`` as repeated entries with
        # the same field name; the form clean reassembles them into
        # the comma-delimited storage shape used by EventClause.value.
        data = QueryDict( '', mutable = True )
        data['entity_state'] = str( self.discrete_state.id )
        data['value_operator_str'] = 'in'
        data.setlist( 'value', [ 'object_person', 'object_car' ] )
        form = EventClauseForm( data = data )
        self.assertTrue( form.is_valid(), msg = form.errors )
        # Sorted+joined for determinism; tests downstream of the
        # matcher don't care about order but assertions need a
        # deterministic value to compare against.
        self.assertEqual(
            form.cleaned_data['value'], 'object_car,object_person',
        )
        return

    def test_in_clause_renders_multi_select_for_discrete_state(self):
        # Form rendered for an existing IN clause on a discrete-choice
        # state should expose a SelectMultiple widget AND pre-populate
        # the initial with the parsed list — so the edit-page load
        # shows the persisted selection without any JS flicker.
        clause = self._make_in_clause( 'object_person,object_car' )
        form = EventClauseForm( instance = clause )
        self.assertIsInstance(
            form.fields['value'].widget, forms.SelectMultiple,
        )
        self.assertEqual(
            sorted( form.initial['value'] ),
            [ 'object_car', 'object_person' ],
        )
        # The widget must carry the entity_state's choices — a
        # regression that strips them or hands a stale list would
        # render an empty (or wrong) multi-select and the initial-
        # list assertion alone wouldn't notice.
        self.assertEqual(
            list( form.fields['value'].widget.choices ),
            list( self.discrete_state.choices() ),
        )
        return

    def test_in_clause_on_free_text_state_stays_text_input(self):
        # IN on an entity_state without discrete choices falls back to
        # a TextInput. The user types comma-delimited values; the
        # matcher splits at evaluation time.
        entity = Entity.objects.create(
            name = 'Free Text Entity',
            entity_type_str = 'other',
        )
        free_text_state = EntityState.objects.create(
            entity = entity,
            name = 'Notes',
            entity_state_type_str = 'multivalued',
        )
        event_definition = EventDefinition.objects.create(
            name = 'Test', event_type_str = 'security',
            event_window_secs = 0, dedupe_window_secs = 0,
        )
        clause = EventClause.objects.create(
            event_definition = event_definition,
            entity_state = free_text_state,
            value = 'foo,bar',
            value_operator_str = 'in',
        )
        form = EventClauseForm( instance = clause )
        self.assertNotIsInstance(
            form.fields['value'].widget, forms.SelectMultiple,
        )
        return

    def test_neq_clause_on_discrete_state_stays_single_select(self):
        # Regression guard: NEQ must NOT trip the IN multi-select
        # promotion. Single-value comparison stays on the entity_state-
        # driven Select.
        event_definition = EventDefinition.objects.create(
            name = 'Test', event_type_str = 'security',
            event_window_secs = 0, dedupe_window_secs = 0,
        )
        clause = EventClause.objects.create(
            event_definition = event_definition,
            entity_state = self.discrete_state,
            value = 'object_none',
            value_operator_str = 'neq',
        )
        form = EventClauseForm( instance = clause )
        self.assertNotIsInstance(
            form.fields['value'].widget, forms.SelectMultiple,
        )
        return

    def test_single_value_in_post_serializes_without_extra_commas(self):
        # The multi-select reassembly path must work uniformly for
        # one, several, or zero selections — single selection is the
        # case where the form-side default-clean (CharField over a
        # list) would otherwise stringify ``['object_person']``.
        data = QueryDict( '', mutable = True )
        data['entity_state'] = str( self.discrete_state.id )
        data['value_operator_str'] = 'in'
        data.setlist( 'value', [ 'object_person' ] )
        form = EventClauseForm( data = data )
        self.assertTrue( form.is_valid(), msg = form.errors )
        self.assertEqual( form.cleaned_data['value'], 'object_person' )
        return

    def test_operator_widget_emits_data_numeric_ops_from_enum(self):
        # The JS widget swap reads this attribute to decide when to
        # promote the value field to a number input. Keeping the list
        # enum-driven (instead of hard-coded JS) prevents drift when
        # the enum gains or loses a numeric operator.
        import json
        form = EventClauseForm( data = {
            'entity_state': str( self.discrete_state.id ),
            'value_operator_str': 'eq',
            'value': 'object_person',
        })
        attr = form.fields['value_operator_str'].widget.attrs.get(
            'data-numeric-ops',
        )
        self.assertIsNotNone( attr )
        self.assertEqual(
            sorted( json.loads( attr )),
            [ 'gt', 'gte', 'lt', 'lte' ],
        )
        return

    def _make_in_clause( self, value : str ):
        event_definition = EventDefinition.objects.create(
            name = 'Test', event_type_str = 'security',
            event_window_secs = 0, dedupe_window_secs = 0,
        )
        return EventClause.objects.create(
            event_definition = event_definition,
            entity_state = self.discrete_state,
            value = value,
            value_operator_str = 'in',
        )
