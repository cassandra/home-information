import logging

from hi.tests.base_test_case import BaseTestCase
from hi.units import UnitQuantity

from hi.apps.weather.wmo_units import WmoUnits

logging.disable(logging.CRITICAL)


class TestWmoUnits( BaseTestCase ):

    def test_normalize_unit(self):

        for wmo_unit_def in WmoUnits.UNIT_DEFINITIONS:
            for wmo_unit in [ wmo_unit_def.get( 'wmoAbbrev' ),
                              wmo_unit_def.get( 'wmoAbbrev2' ) ]:
                if not wmo_unit:
                    continue
                for prefix in [ '', 'wmoUnit:', 'wmo:', 'unit:' ]:
                    unit_str = '%s%s' % ( prefix, wmo_unit )
                    norm_str = WmoUnits.normalize_unit( wmo_unit )
                    try:
                        _ = UnitQuantity( 1, norm_str )
                    except Exception as e:
                        self.fail( f'WMO unit parse failure: {e} : unit = "{unit_str} <- {wmo_unit}"' )
                    continue
                continue
            continue
        return
