import logging

from hi.apps.weather.enums import (
    CloudCoverageType,
    MoonPhase,
    SkyCondition, 
    WindDirection,
)

from hi.tests.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestWeatherEnums( BaseTestCase ):

    def test_SkyCondition__from_cloud_cover(self):
        test_data_list = [
            { 'percent': 0.0     , 'expect': SkyCondition.CLEAR },
            { 'percent': 5.5     , 'expect': SkyCondition.CLEAR },
            { 'percent': 12.5    , 'expect': SkyCondition.CLEAR },
            { 'percent': 12.5001 , 'expect': SkyCondition.MOSTLY_CLEAR },
            { 'percent': 25.1    , 'expect': SkyCondition.MOSTLY_CLEAR },
            { 'percent': 37.5    , 'expect': SkyCondition.MOSTLY_CLEAR },
            { 'percent': 37.6    , 'expect': SkyCondition.PARTLY_CLOUDY },
            { 'percent': 50.0    , 'expect': SkyCondition.PARTLY_CLOUDY },
            { 'percent': 62.5    , 'expect': SkyCondition.PARTLY_CLOUDY },
            { 'percent': 62.51   , 'expect': SkyCondition.MOSTLY_CLOUDY },
            { 'percent': 74.6    , 'expect': SkyCondition.MOSTLY_CLOUDY },
            { 'percent': 87.5    , 'expect': SkyCondition.MOSTLY_CLOUDY },
            { 'percent': 87.52   , 'expect': SkyCondition.CLOUDY },
            { 'percent': 90.0    , 'expect': SkyCondition.CLOUDY },
            { 'percent': 100.0   , 'expect': SkyCondition.CLOUDY },
        ]
        for test_data in test_data_list:
            result = SkyCondition.from_cloud_cover( cloud_cover_percent = test_data['percent'] )
            self.assertEqual( test_data['expect'], result, test_data )
            continue
        return

    def test_MoonPhase__from_illumination(self):
        test_data_list = [
            { 'percent': 0.0, 'is_waxing'  : True , 'expect': MoonPhase.NEW_MOON },
            { 'percent': 2.9, 'is_waxing'  : True , 'expect': MoonPhase.NEW_MOON },
            { 'percent': 3.0, 'is_waxing'  : True , 'expect': MoonPhase.NEW_MOON },
            { 'percent': 3.1, 'is_waxing' : True , 'expect': MoonPhase.WAXING_CRESCENT },
            { 'percent': 25.1, 'is_waxing': True , 'expect': MoonPhase.WAXING_CRESCENT },
            { 'percent': 46.9, 'is_waxing': True , 'expect': MoonPhase.WAXING_CRESCENT },
            { 'percent': 47.0, 'is_waxing' : True , 'expect': MoonPhase.FIRST_QUARTER },
            { 'percent': 50.0, 'is_waxing' : True , 'expect': MoonPhase.FIRST_QUARTER },
            { 'percent': 53.0, 'is_waxing' : True , 'expect': MoonPhase.FIRST_QUARTER },
            { 'percent': 53.1, 'is_waxing' : True , 'expect': MoonPhase.WAXING_GIBBOUS },
            { 'percent': 75.1, 'is_waxing' : True , 'expect': MoonPhase.WAXING_GIBBOUS },
            { 'percent': 96.9, 'is_waxing' : True , 'expect': MoonPhase.WAXING_GIBBOUS },
            { 'percent': 97.0, 'is_waxing' : True , 'expect': MoonPhase.FULL_MOON },
            { 'percent': 100.0, 'is_waxing': True, 'expect': MoonPhase.FULL_MOON },
            { 'percent': 100.0, 'is_waxing': False, 'expect': MoonPhase.FULL_MOON },
            { 'percent': 97.0, 'is_waxing': False, 'expect': MoonPhase.FULL_MOON },
            { 'percent': 96.9, 'is_waxing' : False, 'expect': MoonPhase.WANING_GIBBOUS },
            { 'percent': 75.1, 'is_waxing' : False, 'expect': MoonPhase.WANING_GIBBOUS },
            { 'percent': 53.1, 'is_waxing' : False, 'expect': MoonPhase.WANING_GIBBOUS },
            { 'percent': 53.0, 'is_waxing': False, 'expect': MoonPhase.LAST_QUARTER },
            { 'percent': 50.0, 'is_waxing': False, 'expect': MoonPhase.LAST_QUARTER },
            { 'percent': 47.0, 'is_waxing' : False, 'expect': MoonPhase.LAST_QUARTER },
            { 'percent': 46.9, 'is_waxing': False, 'expect': MoonPhase.WANING_CRESCENT },
            { 'percent': 25.1, 'is_waxing': False, 'expect': MoonPhase.WANING_CRESCENT },
            { 'percent': 3.1, 'is_waxing': False, 'expect': MoonPhase.WANING_CRESCENT },
            { 'percent': 3.0, 'is_waxing': False, 'expect': MoonPhase.NEW_MOON },
            { 'percent': 1.0, 'is_waxing': False, 'expect': MoonPhase.NEW_MOON },
            { 'percent': 0.0, 'is_waxing': False, 'expect': MoonPhase.NEW_MOON },
        ]
        for test_data in test_data_list:
            result = MoonPhase.from_illumination( illumination_percent = test_data['percent'],
                                                  is_waxing = test_data['is_waxing'] )
            self.assertEqual( test_data['expect'], result, test_data )
            continue
        return

    def test_CloudCoverageType__comparisons(self):
        self.assertTrue( CloudCoverageType.SKY_CLEAR < CloudCoverageType.CLEAR )
        self.assertTrue( CloudCoverageType.CLEAR < CloudCoverageType.FEW )
        self.assertTrue( CloudCoverageType.FEW < CloudCoverageType.SCATTERED )
        self.assertTrue( CloudCoverageType.SCATTERED < CloudCoverageType.BROKEN )
        self.assertTrue( CloudCoverageType.BROKEN < CloudCoverageType.OVERCAST )
        self.assertTrue( CloudCoverageType.OVERCAST < CloudCoverageType.VERTICAL_VISIBILITY )
        return
    
    def test_WindDirection__from_menomic__exceptions(self):
        for bad_mnemonic in [ None, '', '    ', 'NN', 'foo', 'nnen' ]:
            with self.assertRaises( ValueError ):
                WindDirection.from_menomic( bad_mnemonic )
            continue
        return
    
    def test_WindDirection__from_menomic(self):
        test_data_list = [
            { 'mnemonic': 'NE'     , 'expect': WindDirection.NORTHEAST },
            { 'mnemonic': ' ne  '     , 'expect': WindDirection.NORTHEAST },
            { 'mnemonic': 'ssw'    , 'expect': WindDirection.SOUTH_SOUTHWEST },
            { 'mnemonic': 'SW' , 'expect': WindDirection.SOUTHWEST },
            { 'mnemonic': 'E'    , 'expect': WindDirection.EAST },
        ]
        for test_data in test_data_list:
            result = WindDirection.from_menomic( test_data['mnemonic'] )
            self.assertEqual( test_data['expect'], result, test_data )
            continue
        return

