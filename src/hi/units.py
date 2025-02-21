from pint import UnitRegistry
from hi.apps.console.enums import DisplayUnits

ureg = UnitRegistry()
UnitQuantity = ureg.Quantity

ureg.define('percent = 1 / 100 = % = pct')

IMPERIAL_TO_METRIC_UNITS = {
    ureg.ft: ureg.m,
    ureg.mph: ureg("km/h"),
    ureg.degF: ureg.degC,
    ureg.inHg: ureg.hPa,
    ureg.mi: ureg.km,
    ureg.gal: ureg.L,
    ureg.lb: ureg.kg,
    ureg.BTU: ureg.J,
    ureg.hp: ureg.W,
    ureg("lbf*ft"): ureg("N*m"),
    ureg.lbf: ureg.N,
    ureg("ft/s^2"): ureg("m/s^2"),
    ureg("lb/ft^3"): ureg("kg/m^3"),
    ureg("gal/min"): ureg("L/min"),
    ureg.rpm: ureg("rad/s"),
}

DisplayUnitsConversionMaps = {
    DisplayUnits.METRIC: dict( IMPERIAL_TO_METRIC_UNITS ),
    DisplayUnits.IMPERIAL: { v: k for k, v in IMPERIAL_TO_METRIC_UNITS.items() },
}


def get_display_quantity( quantity : UnitQuantity, display_units : DisplayUnits ):
    global DisplayUnitsConversionMaps
    
    assert isinstance( quantity, UnitQuantity )
    conversion_map = DisplayUnitsConversionMaps.get( display_units, IMPERIAL_TO_METRIC_UNITS )
    current_unit = quantity.units
    if current_unit in conversion_map:
        target_unit = conversion_map[current_unit]
        try:
            return quantity.to( target_unit )
        except Exception:
            pass
    return quantity
    
