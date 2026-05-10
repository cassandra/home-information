from typing import Optional

from hi.apps.common.singleton import Singleton

from .enums import SimTemperatureUnit


class SimulatorRuntimeSettings( Singleton ):
    """Process-wide, in-memory settings that affect simulator
    behavior at runtime without touching persistent state.

    These are dev-tool toggles intended to make it easy to flex
    the HI translation layers (e.g., flip what unit a simulated
    integration reports temperatures in) without re-seeding
    profiles. Resets to defaults on process restart by design —
    nothing here is persisted.

    Today the only setting is ``temperature_unit_override``: None
    means profiles use their own per-entity unit; otherwise a
    ``SimTemperatureUnit`` value forces every emitted temperature
    to that unit (with magnitudes converted so the physical
    temperature stays constant). Each integration's composer is
    responsible for mapping the enum to its own wire format.

    Add new toggles here as needed; the API is intentionally
    integration-agnostic.
    """

    def __init_singleton__(self):
        self._temperature_unit_override : Optional[SimTemperatureUnit] = None
        return

    @property
    def temperature_unit_override(self) -> Optional[SimTemperatureUnit]:
        return self._temperature_unit_override

    def set_temperature_unit_override(
            self, value : Optional[SimTemperatureUnit] ):
        if value is not None and not isinstance( value, SimTemperatureUnit ):
            raise ValueError(
                f'Invalid temperature_unit_override: {value!r}'
            )
        self._temperature_unit_override = value
        return
