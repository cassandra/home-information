from hi.apps.common.enums import LabeledEnum


class SimTemperatureUnit(LabeledEnum):
    """Integration-agnostic temperature unit choice for the
    simulator's runtime override. Each integration's composer maps
    these to its own wire format (e.g., HA uses ``°F`` / ``°C``;
    other integrations may use ``degF`` / ``degC`` or other
    conventions)."""

    FAHRENHEIT = ( 'Fahrenheit', '' )
    CELSIUS    = ( 'Celsius', '' )

    @classmethod
    def default(cls):
        return cls.FAHRENHEIT
