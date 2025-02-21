from django import template

from hi.apps.config.settings_mixins import SettingsMixin
from hi.apps.console.enums import DisplayUnits
from hi.apps.console.settings import ConsoleSetting

from hi.units import UnitQuantity, get_display_quantity

register = template.Library()

g_settings_manager = None  # Must be done lazily, else Django init conflicts with DB access.


@register.filter
def format_quantity( quantity : UnitQuantity, fmt = "~H" ):
    """
    Formats a Pint unit quantity using the specified format.
    
    Usage:
    {{ my_quantity|format_pint:"~P" }}
    
    Available formats:
    - "P" (default): Compact human-readable
    - "~P": Removes unit definitions for a clean output (e.g., "10 ft")
    - "L": Latex formatted output
    - "H": HTML formatted output
    - "C": Compact notation
    """

    display_quantity = to_display_quantity( quantity )
    try:
        return f"{display_quantity:{fmt}}"
    except Exception:
        return str(display_quantity)

    
@register.filter
def format_magnitude( quantity : UnitQuantity, decimal_places : int = 1  ):
    if not isinstance( quantity, UnitQuantity ):
        return str(quantity)

    display_quantity = to_display_quantity( quantity )
    try:
        return f"{display_quantity.magnitude:.{decimal_places}f}"
    except Exception:
        return str(display_quantity.magnitude)

    
@register.filter
def format_units( quantity : UnitQuantity, fmt = "~H"  ):
    if not isinstance( quantity, UnitQuantity ):
        return str(quantity)

    display_quantity = to_display_quantity( quantity )
    try:
        return f"{display_quantity.units:{fmt}}"
    except Exception:
        return ""

    
@register.filter
def format_compass( quantity : UnitQuantity ):
    """Converts degrees into a compass direction (N, NE, E, etc.)."""
    if not isinstance( quantity, UnitQuantity ):
        return str(quantity)

    degrees = quantity.to("deg").magnitude % 360  # Normalize 0-360°
    directions = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                  "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    index = round( degrees / 22.5 ) % 16
    return directions[index]


def to_display_quantity( quantity : UnitQuantity ):
    global g_settings_manager
    if not isinstance( quantity, UnitQuantity ):
        return quantity
    if not g_settings_manager:
        g_settings_manager = SettingsMixin().settings_manager()
    display_units_str = g_settings_manager.get_setting_value( ConsoleSetting.DISPLAY_UNITS )
    display_units = DisplayUnits.from_name( display_units_str )
    return get_display_quantity(
        quantity = quantity,
        display_units = display_units,
    )
