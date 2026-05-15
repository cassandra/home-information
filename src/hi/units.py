from pint import UnitRegistry
from hi.apps.console.enums import DisplayUnits

ureg = UnitRegistry()
UnitQuantity = ureg.Quantity


# HI-wide canonical unit choices. Integration converters that import
# unit-bearing values normalize to the canonical at the boundary;
# downstream code reads ``EntityState.units`` (set from these
# canonicals at creation time) rather than re-asserting the canonical.
# Adding a new canonical here makes it available cross-integration so
# multiple integrations don't duplicate the choice.
CANONICAL_TEMPERATURE_UNIT = '°C'

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


# Keys/values must be pint ``Unit`` objects so dict lookups against a
# ``Quantity.units`` match. ``ureg("km/h")`` returns a ``Quantity``
# (magnitude 1 + unit) whose hash differs from the equivalent ``Unit``,
# so we route compound expressions through ``ureg.parse_units`` to land
# on a ``Unit`` consistently.
def _unit( expr ):
    return ureg.parse_units( expr )


IMPERIAL_TO_METRIC_UNITS = {
    _unit('inch'): ureg.mm,
    ureg.ft: ureg.m,
    ureg.mph: _unit('km/h'),
    ureg.degF: ureg.degC,
    ureg.inHg: ureg.hPa,
    ureg.mi: ureg.km,
    ureg.gal: ureg.L,
    ureg.lb: ureg.kg,
    ureg.BTU: ureg.J,
    ureg.hp: ureg.W,
    _unit('lbf*ft'): _unit('N*m'),
    ureg.lbf: ureg.N,
    _unit('ft/s^2'): _unit('m/s^2'),
    _unit('lb/ft^3'): _unit('kg/m^3'),
    _unit('gal/min'): _unit('L/min'),
    ureg.rpm: _unit('rad/s'),
}

DisplayUnitsConversionMaps = {
    DisplayUnits.METRIC: dict( IMPERIAL_TO_METRIC_UNITS ),
    DisplayUnits.IMPERIAL: { v: k for k, v in IMPERIAL_TO_METRIC_UNITS.items() },
}


def get_display_quantity( quantity : UnitQuantity, display_units : DisplayUnits ):
    
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
    
