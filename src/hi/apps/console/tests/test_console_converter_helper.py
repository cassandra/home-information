import logging
from unittest.mock import MagicMock, patch

from hi.apps.console.console_converter_helper import (
    ConsoleConverterHelper,
    DisplayValue,
)
from hi.apps.console.enums import DisplayUnits
from hi.testing.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestDisplayValue(BaseTestCase):

    def test_str_combines_magnitude_and_unit(self):
        # ``DisplayValue.__str__`` is the contract that templates
        # rely on for ``{{ value|as_display_value:entity_state }}`` to
        # produce combined text directly.
        self.assertEqual(
            str( DisplayValue( magnitude = '69.8', unit_symbol = '°F' ) ),
            '69.8°F',
        )

    def test_str_with_empty_unit_is_just_magnitude(self):
        self.assertEqual(
            str( DisplayValue( magnitude = '50' ) ), '50',
        )

    def test_str_inserts_space_for_alphabetic_unit(self):
        # Alphabetic SI-style abbreviations (lx, kg, Pa, Hz, ...)
        # render with a space; symbol-style units (°F, %) attach
        # directly per the test above.
        self.assertEqual(
            str( DisplayValue( magnitude = '120', unit_symbol = 'lx' ) ),
            '120 lx',
        )

    def test_default_construction_is_empty(self):
        # Used as the no-value sentinel from ``from_entity_state_value``.
        self.assertEqual( str( DisplayValue() ), '' )


def _entity_state_with_units( units ):
    """Build a minimal EntityState-shaped object — the helper only
    reads ``.units`` and ``.id``, so a MagicMock is sufficient and
    avoids per-test DB setup."""
    state = MagicMock()
    state.units = units
    state.id = 1
    return state


def _patch_user_display_units( display_units ):
    return patch(
        'hi.apps.console.console_converter_helper.ConsoleSettingsHelper',
        return_value = MagicMock( get_display_units = MagicMock(
            return_value = display_units,
        )),
    )


class TestToEntityStateValue(BaseTestCase):
    """Inbound: HTML/JS form value (in user's display unit) →
    EntityState's stored unit."""

    def test_converts_imperial_user_input_to_celsius_state(self):
        # User submitted "70" in their °F display preference; the
        # entity stores °C — helper converts.
        state = _entity_state_with_units( '°C' )
        with _patch_user_display_units( DisplayUnits.IMPERIAL ):
            result = ConsoleConverterHelper.to_entity_state_value(
                display_value = '70',
                entity_state = state,
            )
        self.assertAlmostEqual( float( result ), 21.111, places = 2 )

    def test_passthrough_when_user_unit_matches_state_unit(self):
        # Metric user, °C entity — no conversion needed; original
        # string returned unchanged so downstream string handling
        # is preserved.
        state = _entity_state_with_units( '°C' )
        with _patch_user_display_units( DisplayUnits.METRIC ):
            result = ConsoleConverterHelper.to_entity_state_value(
                display_value = '22',
                entity_state = state,
            )
        self.assertEqual( result, '22' )

    def test_passthrough_when_state_has_no_units(self):
        # Hue / saturation / on-off / etc. — original string
        # returned unchanged, no Pint hop attempted.
        state = _entity_state_with_units( None )
        with _patch_user_display_units( DisplayUnits.IMPERIAL ):
            result = ConsoleConverterHelper.to_entity_state_value(
                display_value = '180',
                entity_state = state,
            )
        self.assertEqual( result, '180' )

    def test_non_numeric_input_passes_through(self):
        # User submission of a non-numeric value for a unit-bearing
        # state must not raise — downstream validation owns the
        # rejection. The value passes through unchanged so callers
        # see the original string they can validate.
        state = _entity_state_with_units( '°C' )
        with _patch_user_display_units( DisplayUnits.IMPERIAL ):
            result = ConsoleConverterHelper.to_entity_state_value(
                display_value = 'not-a-number',
                entity_state = state,
            )
        self.assertEqual( result, 'not-a-number' )


class TestFromEntityStateValue(BaseTestCase):
    """Outbound: EntityState's stored unit → user's display unit.
    Returns DisplayValue (magnitude + unit_symbol)."""

    def test_imperial_user_sees_celsius_state_in_fahrenheit(self):
        state = _entity_state_with_units( '°C' )
        with _patch_user_display_units( DisplayUnits.IMPERIAL ):
            display = ConsoleConverterHelper.from_entity_state_value(
                entity_state_value = 22.0,
                entity_state = state,
            )
        self.assertEqual( display.unit_symbol, '°F' )
        self.assertAlmostEqual( float( display.magnitude ), 71.6, places = 1 )

    def test_metric_user_sees_celsius_state_unchanged(self):
        state = _entity_state_with_units( '°C' )
        with _patch_user_display_units( DisplayUnits.METRIC ):
            display = ConsoleConverterHelper.from_entity_state_value(
                entity_state_value = 22.5,
                entity_state = state,
            )
        self.assertEqual( display.unit_symbol, '°C' )
        self.assertAlmostEqual( float( display.magnitude ), 22.5 )

    def test_no_units_returns_passthrough_display_value(self):
        # Unit-less states (hue, percent) return DisplayValue with
        # the value as magnitude and empty unit_symbol — preserves
        # the safe-to-call-uniformly contract.
        state = _entity_state_with_units( None )
        with _patch_user_display_units( DisplayUnits.IMPERIAL ):
            display = ConsoleConverterHelper.from_entity_state_value(
                entity_state_value = 50,
                entity_state = state,
            )
        self.assertEqual( display.unit_symbol, '' )
        self.assertEqual( display.magnitude, '50' )

    def test_none_value_returns_empty_display_value(self):
        state = _entity_state_with_units( '°C' )
        with _patch_user_display_units( DisplayUnits.METRIC ):
            display = ConsoleConverterHelper.from_entity_state_value(
                entity_state_value = None,
                entity_state = state,
            )
        self.assertEqual( str( display ), '' )

    def test_round_trip_with_to_entity_state_value(self):
        # User submits 70°F → stored canonical °C → rendered back
        # as 70°F. Within float precision after two Pint hops.
        state = _entity_state_with_units( '°C' )
        with _patch_user_display_units( DisplayUnits.IMPERIAL ):
            stored = ConsoleConverterHelper.to_entity_state_value(
                display_value = '70',
                entity_state = state,
            )
            display = ConsoleConverterHelper.from_entity_state_value(
                entity_state_value = float( stored ),
                entity_state = state,
            )
        self.assertEqual( display.unit_symbol, '°F' )
        self.assertAlmostEqual( float( display.magnitude ), 70.0, places = 1 )
