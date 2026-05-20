"""Temperature unit translation for the HA simulator.

Maps the integration-agnostic ``SimTemperatureUnit`` runtime
override (set globally in ``SimulatorRuntimeSettings``) to HA's
wire-format unit symbols (``°F`` / ``°C``), and provides a small
F↔C conversion helper used on both the outbound (composer) and
inbound (dispatcher) sides of the simulator's HA boundary.

When the runtime override is set, the simulator emits all
temperature values in the override unit (with magnitudes converted
so the physical temperature stays constant) and accepts incoming
HA service calls in that same unit. Internal SimState storage
remains in each profile's per-entity unit; conversion happens
purely at this boundary.
"""
from typing import Optional

from hi.simulator.settings.enums import SimTemperatureUnit
from hi.simulator.settings.runtime_settings import SimulatorRuntimeSettings


class UnitTranslationHelper:
    """Namespace for HA-simulator temperature-unit translation."""

    SIM_TEMPERATURE_UNIT_TO_HA_WIRE = {
        SimTemperatureUnit.FAHRENHEIT: '°F',
        SimTemperatureUnit.CELSIUS: '°C',
    }

    @classmethod
    def emitted_temperature_unit(
            cls, profile_unit : Optional[str] ) -> Optional[str]:
        """The wire-format temperature unit the simulator should
        emit, applying the runtime override if set; otherwise the
        profile's own unit passes through unchanged."""
        override = SimulatorRuntimeSettings().temperature_unit_override
        if override is None:
            return profile_unit
        return cls.SIM_TEMPERATURE_UNIT_TO_HA_WIRE.get(
            override, profile_unit,
        )

    @staticmethod
    def convert_temperature_value(
            value,
            from_unit : Optional[str],
            to_unit   : Optional[str],
    ):
        """F↔C conversion. Pass-through when units match, either
        side is unset, or the value can't be coerced to float."""
        if value is None or not from_unit or not to_unit:
            return value
        if from_unit == to_unit:
            return value
        try:
            magnitude = float( value )
        except ( TypeError, ValueError ):
            return value
        if from_unit == '°F' and to_unit == '°C':
            return ( magnitude - 32.0 ) * 5.0 / 9.0
        if from_unit == '°C' and to_unit == '°F':
            return magnitude * 9.0 / 5.0 + 32.0
        return value
