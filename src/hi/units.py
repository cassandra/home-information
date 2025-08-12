from pint import UnitRegistry
from hi.apps.console.enums import DisplayUnits

ureg = UnitRegistry()
UnitQuantity = ureg.Quantity

ureg.define('percent = 1 / 100 = % = pct')
ureg.define('true = 1 = yes = on')
ureg.define('false = 0 = no = off')
ureg.define('probability = 1 = chance = prob')
ureg.define('certain = 1 probability')
ureg.define('impossible = 0 probability')

# Some extras from WMO: https://codes.wmo.int/common/unit
ureg.define('Dimensionless = 1')
ureg.define('astronomic_unit = 149597870.7 * kilometer = AU')
ureg.define('becquerel = 1 / second = Bq')
ureg.define('joules_per_kilogram = 1 joule / kilogram = J_kg')
ureg.define("weber = volt * second = tesla * meter ** 2 = Wb")
ureg.define("dekapascal = 10 * pascal = daPa")
ureg.define('okta = 1 / 8')
ureg.define("dobson_unit = 2.69e16 * molecule / centimeter ** 2 = DU")
ureg.define("centibar_per_12_hours = 100 * pascal / (12 * hour) = cb_per_12h = cb/12h")
ureg.define("geopotential_meter = meter = gpm")
ureg.define("hectopascal_per_3_hours = 100 * pascal / (3 * hour) = hPa_per_3h = hPa/3h")
ureg.define("meter_two_thirds_per_second = meter ** (2/3) / second = m^(2/3)/s = m2/3/s")

IMPERIAL_TO_METRIC_UNITS = {
    ureg('inches'): ureg.mm,
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
    
