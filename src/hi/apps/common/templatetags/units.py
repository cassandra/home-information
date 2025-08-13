from django import template

from hi.apps.console.console_helper import ConsoleSettingsHelper

from hi.units import UnitQuantity, get_display_quantity

register = template.Library()


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
    if not isinstance( quantity, UnitQuantity ):
        return quantity
    display_units = ConsoleSettingsHelper().get_display_units()
    return get_display_quantity(
        quantity = quantity,
        display_units = display_units,
    )
