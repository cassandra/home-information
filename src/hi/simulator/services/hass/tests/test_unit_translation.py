import logging
from unittest.mock import patch

from django.test import TestCase

from hi.simulator.settings.enums import SimTemperatureUnit
from hi.simulator.services.hass.unit_translation import UnitTranslationHelper

logging.disable(logging.CRITICAL)


def _override_context():
    """Patch the SimulatorRuntimeSettings singleton accessed by the
    helper so tests can dictate the temperature_unit_override
    without touching real process-wide state."""
    return patch(
        'hi.simulator.services.hass.unit_translation'
        '.SimulatorRuntimeSettings',
    )


class TestEmittedTemperatureUnit(TestCase):
    """Resolves the wire-format unit the simulator should emit:
    profile-default when no override, override-mapped to HA wire
    symbol otherwise."""

    def test_no_override_returns_profile_unit(self):
        with _override_context() as mock_singleton:
            mock_singleton.return_value.temperature_unit_override = None
            self.assertEqual(
                UnitTranslationHelper.emitted_temperature_unit( '°F' ),
                '°F',
            )

    def test_override_celsius_returns_ha_celsius_symbol(self):
        with _override_context() as mock_singleton:
            mock_singleton.return_value.temperature_unit_override = (
                SimTemperatureUnit.CELSIUS
            )
            self.assertEqual(
                UnitTranslationHelper.emitted_temperature_unit( '°F' ),
                '°C',
            )

    def test_override_fahrenheit_returns_ha_fahrenheit_symbol(self):
        with _override_context() as mock_singleton:
            mock_singleton.return_value.temperature_unit_override = (
                SimTemperatureUnit.FAHRENHEIT
            )
            self.assertEqual(
                UnitTranslationHelper.emitted_temperature_unit( '°C' ),
                '°F',
            )


class TestConvertTemperatureValue(TestCase):
    """F↔C conversion with defensive pass-through. The simulator
    relies on this both at the composer (profile-unit → emitted
    wire-unit) and at the dispatcher (incoming-wire-unit →
    profile-unit) boundaries."""

    def test_fahrenheit_to_celsius_freezing_point(self):
        result = UnitTranslationHelper.convert_temperature_value(
            32, from_unit = '°F', to_unit = '°C',
        )
        self.assertAlmostEqual( result, 0.0, places = 6 )

    def test_celsius_to_fahrenheit_boiling_point(self):
        result = UnitTranslationHelper.convert_temperature_value(
            100, from_unit = '°C', to_unit = '°F',
        )
        self.assertAlmostEqual( result, 212.0, places = 6 )

    def test_fahrenheit_to_celsius_room_temperature(self):
        # 70°F → 21.111°C — the canonical conversion in the
        # simulator's seed default for °F-native thermostats.
        result = UnitTranslationHelper.convert_temperature_value(
            70, from_unit = '°F', to_unit = '°C',
        )
        self.assertAlmostEqual( result, 21.111, places = 2 )

    def test_units_match_returns_value_unchanged(self):
        # Passes through the value identically without a Pint hop.
        result = UnitTranslationHelper.convert_temperature_value(
            22.5, from_unit = '°C', to_unit = '°C',
        )
        self.assertEqual( result, 22.5 )

    def test_missing_units_passthrough(self):
        # Defensive: if either side is unset (e.g., HA reports a
        # state without temperature_unit), the helper must not
        # raise — pass the value through.
        self.assertEqual(
            UnitTranslationHelper.convert_temperature_value(
                70, from_unit = None, to_unit = '°C',
            ),
            70,
        )
        self.assertEqual(
            UnitTranslationHelper.convert_temperature_value(
                70, from_unit = '°F', to_unit = None,
            ),
            70,
        )

    def test_non_numeric_value_passes_through(self):
        # Non-numeric input shouldn't break the boundary — the
        # simulator's composer / dispatcher rely on this for
        # graceful behavior on malformed values.
        self.assertEqual(
            UnitTranslationHelper.convert_temperature_value(
                'oops', from_unit = '°F', to_unit = '°C',
            ),
            'oops',
        )

    def test_none_value_passes_through(self):
        result = UnitTranslationHelper.convert_temperature_value(
            None, from_unit = '°F', to_unit = '°C',
        )
        self.assertIsNone( result )

    def test_round_trip_preserves_value_within_float_precision(self):
        # The simulator uses the same conversion at composer (out)
        # and dispatcher (in) — round-trip must preserve the
        # physical temperature.
        celsius = UnitTranslationHelper.convert_temperature_value(
            72.0, from_unit = '°F', to_unit = '°C',
        )
        fahrenheit = UnitTranslationHelper.convert_temperature_value(
            celsius, from_unit = '°C', to_unit = '°F',
        )
        self.assertAlmostEqual( fahrenheit, 72.0, places = 6 )
