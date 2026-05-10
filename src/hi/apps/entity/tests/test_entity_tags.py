import logging

from hi.apps.entity.templatetags.entity_tags import value_label
from hi.testing.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestValueLabel(BaseTestCase):
    """``value_label`` resolves a stored EntityStateValue wire string
    (the lowercased enum name) to its human-readable label so
    template-rendered sensor displays show ``"Smoke Detected"``
    rather than ``"smoke_detected"``."""

    def test_resolves_underscore_separated_value(self):
        # The motivating case: multi-word values that look broken
        # in their wire form.
        self.assertEqual( value_label( 'smoke_detected' ), 'Smoke Detected' )

    def test_resolves_single_word_value(self):
        # Pre-existing single-word values (movement / open-close /
        # etc.) get capitalized labels too.
        self.assertEqual( value_label( 'active' ), 'Active' )
        self.assertEqual( value_label( 'closed' ), 'Closed' )

    def test_unknown_value_passes_through(self):
        # Numeric / free-form values (e.g., temperatures, raw
        # device strings) aren't enum members and must not raise.
        self.assertEqual( value_label( '72.5' ), '72.5' )
        self.assertEqual( value_label( 'arbitrary' ), 'arbitrary' )

    def test_empty_and_none_pass_through(self):
        self.assertEqual( value_label( '' ), '' )
        self.assertIsNone( value_label( None ) )
