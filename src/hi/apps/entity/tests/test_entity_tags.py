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

    def test_numeric_value_passes_through(self):
        # Temperatures and other numeric values must not get
        # mangled by humanization.
        self.assertEqual( value_label( '72.5' ), '72.5' )

    def test_non_enum_name_value_humanized(self):
        # Free-form wire values that aren't enum members (e.g., HA
        # hvac_action values like 'heating') get humanized into a
        # readable label.
        self.assertEqual( value_label( 'heating' ), 'Heating' )
        self.assertEqual( value_label( 'fan_only' ), 'Fan Only' )

    def test_empty_and_none_pass_through(self):
        self.assertEqual( value_label( '' ), '' )
        self.assertIsNone( value_label( None ) )
