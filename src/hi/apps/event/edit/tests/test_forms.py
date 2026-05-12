import logging

from hi.apps.entity.models import Entity, EntityState
from hi.apps.event.edit.forms import EventClauseForm
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

    def test_non_numeric_value_with_lt_operator_is_rejected(self):
        form = EventClauseForm( data = {
            'entity_state': str( self.entity_state.id ),
            'value_operator_str': 'lt',
            'value': 'abc',
        })
        self.assertFalse( form.is_valid() )
        self.assertIn( 'value', form.errors )
        return

    def test_numeric_value_with_lt_operator_is_accepted(self):
        form = EventClauseForm( data = {
            'entity_state': str( self.entity_state.id ),
            'value_operator_str': 'lt',
            'value': '20.5',
        })
        self.assertTrue( form.is_valid(), msg = form.errors )
        return
