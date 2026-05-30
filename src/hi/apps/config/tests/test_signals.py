"""Tests for ``SettingsInitializer._coerce_value_range_str``.

Pins the type-coercion contract that bridges
``SettingDefinition.value_range`` (Python-typed input) to
``AttributeModel.value_range_str`` (string-stored DB column).
"""

from hi.apps.config.signals import SettingsInitializer
from hi.testing.base_test_case import BaseTestCase


class TestCoerceValueRangeStr(BaseTestCase):

    def setUp(self):
        super().setUp()
        self._initializer = SettingsInitializer()

    def test_none_becomes_empty_string(self):
        """``None`` -> ``''`` so the model's ``not self.value_range_str``
        early-out fires. Must NOT become the literal string ``'null'``."""
        self.assertEqual(self._initializer._coerce_value_range_str(None), '')

    def test_str_passes_through_unchanged(self):
        """PredefinedValueRanges identifier strings carry across the
        boundary untouched -- they're consumed by
        ``PredefinedValueRanges.get_choices`` later."""
        self.assertEqual(
            self._initializer._coerce_value_range_str(
                'hi.apps.attribute.value_ranges.timezone'
            ),
            'hi.apps.attribute.value_ranges.timezone',
        )

    def test_list_is_json_encoded(self):
        """Inline numeric ranges round-trip through JSON. The model's
        ``value_range_int`` / ``value_range`` parsers expect this
        format."""
        self.assertEqual(
            self._initializer._coerce_value_range_str([1, 100]),
            '[1, 100]',
        )

    def test_dict_is_json_encoded(self):
        """Inline enum choice maps also round-trip through JSON."""
        self.assertEqual(
            self._initializer._coerce_value_range_str({'on': 'On', 'off': 'Off'}),
            '{"on": "On", "off": "Off"}',
        )

    def test_unsupported_type_raises_type_error(self):
        """A miswritten SettingDefinition (e.g., a stray tuple, set, or
        object) must fail loudly at app boot rather than silently
        corrupting the DB with an un-roundtrippable payload."""
        with self.assertRaises(TypeError):
            self._initializer._coerce_value_range_str((1, 100))
        with self.assertRaises(TypeError):
            self._initializer._coerce_value_range_str({1, 2, 3})
        with self.assertRaises(TypeError):
            self._initializer._coerce_value_range_str(42)
