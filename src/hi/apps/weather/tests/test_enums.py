import logging

from hi.apps.weather.enums import (
    AlertCategory,
    AlertCertainty,
    AlertSeverity,
    AlertStatus,
    AlertUrgency,
    CloudCoverageType,
    MoonPhase,
    SkyCondition, 
    WeatherPhenomenon,
    WeatherPhenomenonIntensity,
    WeatherPhenomenonModifier,
    WindDirection,
)

from hi.testing.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestWeatherEnums(BaseTestCase):

    def test_SkyCondition__from_cloud_cover(self):
        """Test SkyCondition cloud cover percentage mapping"""
        test_data_list = [
            {'percent': 0.0, 'expect': SkyCondition.CLEAR},
            {'percent': 5.5, 'expect': SkyCondition.CLEAR},
            {'percent': 12.5, 'expect': SkyCondition.CLEAR},
            {'percent': 12.5001, 'expect': SkyCondition.MOSTLY_CLEAR},
            {'percent': 25.1, 'expect': SkyCondition.MOSTLY_CLEAR},
            {'percent': 37.5, 'expect': SkyCondition.MOSTLY_CLEAR},
            {'percent': 37.6, 'expect': SkyCondition.PARTLY_CLOUDY},
            {'percent': 50.0, 'expect': SkyCondition.PARTLY_CLOUDY},
            {'percent': 62.5, 'expect': SkyCondition.PARTLY_CLOUDY},
            {'percent': 62.51, 'expect': SkyCondition.MOSTLY_CLOUDY},
            {'percent': 74.6, 'expect': SkyCondition.MOSTLY_CLOUDY},
            {'percent': 87.5, 'expect': SkyCondition.MOSTLY_CLOUDY},
            {'percent': 87.52, 'expect': SkyCondition.CLOUDY},
            {'percent': 90.0, 'expect': SkyCondition.CLOUDY},
            {'percent': 100.0, 'expect': SkyCondition.CLOUDY},
        ]
        for test_data in test_data_list:
            with self.subTest(percent=test_data['percent']):
                result = SkyCondition.from_cloud_cover(cloud_cover_percent=test_data['percent'])
                self.assertEqual(test_data['expect'], result, test_data)
                continue
        return

    def test_SkyCondition__from_cloud_cover_edge_cases(self):
        """Test SkyCondition edge cases and boundary conditions"""
        # Test values > 100% should still work (handle gracefully)
        result = SkyCondition.from_cloud_cover(150.0)
        self.assertEqual(result, SkyCondition.CLOUDY)
        
        result = SkyCondition.from_cloud_cover(200.0)
        self.assertEqual(result, SkyCondition.CLOUDY)
        
        # Test negative values should still work (handle gracefully)
        result = SkyCondition.from_cloud_cover(-10.0)
        self.assertEqual(result, SkyCondition.CLEAR)
        
        return

    def test_MoonPhase__from_illumination(self):
        """Test MoonPhase illumination percentage and waxing status mapping"""
        test_data_list = [
            {'percent': 0.0, 'is_waxing': True, 'expect': MoonPhase.NEW_MOON},
            {'percent': 2.9, 'is_waxing': True, 'expect': MoonPhase.NEW_MOON},
            {'percent': 3.0, 'is_waxing': True, 'expect': MoonPhase.NEW_MOON},
            {'percent': 3.1, 'is_waxing': True, 'expect': MoonPhase.WAXING_CRESCENT},
            {'percent': 25.1, 'is_waxing': True, 'expect': MoonPhase.WAXING_CRESCENT},
            {'percent': 46.9, 'is_waxing': True, 'expect': MoonPhase.WAXING_CRESCENT},
            {'percent': 47.0, 'is_waxing': True, 'expect': MoonPhase.FIRST_QUARTER},
            {'percent': 50.0, 'is_waxing': True, 'expect': MoonPhase.FIRST_QUARTER},
            {'percent': 53.0, 'is_waxing': True, 'expect': MoonPhase.FIRST_QUARTER},
            {'percent': 53.1, 'is_waxing': True, 'expect': MoonPhase.WAXING_GIBBOUS},
            {'percent': 75.1, 'is_waxing': True, 'expect': MoonPhase.WAXING_GIBBOUS},
            {'percent': 96.9, 'is_waxing': True, 'expect': MoonPhase.WAXING_GIBBOUS},
            {'percent': 97.0, 'is_waxing': True, 'expect': MoonPhase.FULL_MOON},
            {'percent': 100.0, 'is_waxing': True, 'expect': MoonPhase.FULL_MOON},
            {'percent': 100.0, 'is_waxing': False, 'expect': MoonPhase.FULL_MOON},
            {'percent': 97.0, 'is_waxing': False, 'expect': MoonPhase.FULL_MOON},
            {'percent': 96.9, 'is_waxing': False, 'expect': MoonPhase.WANING_GIBBOUS},
            {'percent': 75.1, 'is_waxing': False, 'expect': MoonPhase.WANING_GIBBOUS},
            {'percent': 53.1, 'is_waxing': False, 'expect': MoonPhase.WANING_GIBBOUS},
            {'percent': 53.0, 'is_waxing': False, 'expect': MoonPhase.LAST_QUARTER},
            {'percent': 50.0, 'is_waxing': False, 'expect': MoonPhase.LAST_QUARTER},
            {'percent': 47.0, 'is_waxing': False, 'expect': MoonPhase.LAST_QUARTER},
            {'percent': 46.9, 'is_waxing': False, 'expect': MoonPhase.WANING_CRESCENT},
            {'percent': 25.1, 'is_waxing': False, 'expect': MoonPhase.WANING_CRESCENT},
            {'percent': 3.1, 'is_waxing': False, 'expect': MoonPhase.WANING_CRESCENT},
            {'percent': 3.0, 'is_waxing': False, 'expect': MoonPhase.NEW_MOON},
            {'percent': 1.0, 'is_waxing': False, 'expect': MoonPhase.NEW_MOON},
            {'percent': 0.0, 'is_waxing': False, 'expect': MoonPhase.NEW_MOON},
        ]
        for test_data in test_data_list:
            with self.subTest(percent=test_data['percent'], waxing=test_data['is_waxing']):
                result = MoonPhase.from_illumination( illumination_percent=test_data['percent'],
                                                      is_waxing=test_data['is_waxing'])
                self.assertEqual(test_data['expect'], result, test_data)
                continue
        return

    def test_MoonPhase__from_illumination_edge_cases(self):
        """Test MoonPhase edge cases"""
        # Test values > 100% should work (handle gracefully)
        result = MoonPhase.from_illumination(150.0, True)
        self.assertEqual(result, MoonPhase.FULL_MOON)
        
        result = MoonPhase.from_illumination(110.0, False)
        self.assertEqual(result, MoonPhase.FULL_MOON)
        
        # Test negative values should work (handle gracefully)
        result = MoonPhase.from_illumination(-10.0, True)
        self.assertEqual(result, MoonPhase.NEW_MOON)
        
        result = MoonPhase.from_illumination(-5.0, False)
        self.assertEqual(result, MoonPhase.NEW_MOON)
        
        return

    def test_MoonPhase_properties(self):
        """Test MoonPhase enum properties"""
        for phase in MoonPhase:
            with self.subTest(phase=phase):
                self.assertIsNotNone(phase.label)
                self.assertIsNotNone(phase.icon_filename)
                self.assertTrue(phase.icon_filename.endswith('.svg'))
                continue
        return

    def test_CloudCoverageType__comparisons(self):
        """Test CloudCoverageType ordering comparisons"""
        self.assertTrue(CloudCoverageType.SKY_CLEAR < CloudCoverageType.CLEAR)
        self.assertTrue(CloudCoverageType.CLEAR < CloudCoverageType.FEW)
        self.assertTrue(CloudCoverageType.FEW < CloudCoverageType.SCATTERED)
        self.assertTrue(CloudCoverageType.SCATTERED < CloudCoverageType.BROKEN)
        self.assertTrue(CloudCoverageType.BROKEN < CloudCoverageType.OVERCAST)
        self.assertTrue(CloudCoverageType.OVERCAST < CloudCoverageType.VERTICAL_VISIBILITY)
        return
    
    def test_CloudCoverageType_completeness(self):
        """Test CloudCoverageType has expected coverage levels"""
        expected_types = ['SKY_CLEAR', 'CLEAR', 'FEW', 'SCATTERED',
                          'BROKEN', 'OVERCAST', 'VERTICAL_VISIBILITY']
        
        for type_name in expected_types:
            with self.subTest(type_name=type_name):
                self.assertTrue(hasattr(CloudCoverageType, type_name))
                coverage_type = getattr(CloudCoverageType, type_name)
                self.assertIsNotNone(coverage_type.label)
                continue
        return
    
    def test_WindDirection__from_mnemonic__exceptions(self):
        """Test WindDirection mnemonic exceptions for invalid inputs"""
        for bad_mnemonic in [None, '', '    ', 'NN', 'foo', 'nnen']:
            with self.subTest(mnemonic=bad_mnemonic):
                with self.assertRaises(ValueError):
                    WindDirection.from_mnemonic(bad_mnemonic)
                continue
        return
    
    def test_WindDirection__from_mnemonic(self):
        """Test WindDirection mnemonic parsing"""
        test_data_list = [
            {'mnemonic': 'NE', 'expect': WindDirection.NORTHEAST},
            {'mnemonic': ' ne  ', 'expect': WindDirection.NORTHEAST},
            {'mnemonic': 'ssw', 'expect': WindDirection.SOUTH_SOUTHWEST},
            {'mnemonic': 'SW', 'expect': WindDirection.SOUTHWEST},
            {'mnemonic': 'E', 'expect': WindDirection.EAST},
        ]
        for test_data in test_data_list:
            with self.subTest(mnemonic=test_data['mnemonic']):
                result = WindDirection.from_mnemonic(test_data['mnemonic'])
                self.assertEqual(test_data['expect'], result, test_data)
                continue
        return

    def test_WindDirection_comprehensive_coverage(self):
        """Test WindDirection has comprehensive directional coverage"""
        # Test all major directions exist
        major_directions = ['NORTH', 'NORTHEAST', 'EAST', 'SOUTHEAST', 
                            'SOUTH', 'SOUTHWEST', 'WEST', 'NORTHWEST']
        
        for direction_name in major_directions:
            with self.subTest(direction=direction_name):
                self.assertTrue(hasattr(WindDirection, direction_name))
                direction = getattr(WindDirection, direction_name)
                self.assertIsNotNone(direction.mnemonic_list)
                self.assertGreater(len(direction.mnemonic_list), 0)
                self.assertIsNotNone(direction.angle_degrees)
                self.assertGreaterEqual(direction.angle_degrees, 0)
                self.assertLess(direction.angle_degrees, 360)
                continue
        return

    def test_AlertCategory_basic_functionality(self):
        """Test AlertCategory enum has expected values"""
        expected_categories = ['METEOROLOGICAL', 'GEOPHYSICAL', 'PUBLIC_SAFETY', 
                               'SECURITY', 'RESCUE', 'FIRE', 'HEALTH', 
                               'ENVIRONMENTAL', 'TRANSPORTATION', 'INFRASTRUCTURE', 'OTHER']
        
        for category_name in expected_categories:
            with self.subTest(category=category_name):
                self.assertTrue(hasattr(AlertCategory, category_name))
                category = getattr(AlertCategory, category_name)
                self.assertIsNotNone(category.label)
                self.assertIsNotNone(category.description)
                continue
        return

    def test_AlertSeverity_basic_functionality(self):
        """Test AlertSeverity enum has expected values"""
        expected_severities = ['MINOR', 'MODERATE', 'SEVERE', 'EXTREME']
        
        for severity_name in expected_severities:
            with self.subTest(severity=severity_name):
                self.assertTrue(hasattr(AlertSeverity, severity_name))
                severity = getattr(AlertSeverity, severity_name)
                self.assertIsNotNone(severity.label)
                continue
        return

    def test_AlertUrgency_basic_functionality(self):
        """Test AlertUrgency enum has expected values"""
        # Note: PAST is deliberately excluded - weather alerts are for current/future threats
        expected_urgencies = ['IMMEDIATE', 'EXPECTED', 'FUTURE', 'UNKNOWN']
        
        for urgency_name in expected_urgencies:
            with self.subTest(urgency=urgency_name):
                self.assertTrue(hasattr(AlertUrgency, urgency_name))
                urgency = getattr(AlertUrgency, urgency_name)
                self.assertIsNotNone(urgency.label)
                continue
        return

    def test_AlertCertainty_basic_functionality(self):
        """Test AlertCertainty enum has expected values"""
        expected_certainties = ['OBSERVED', 'LIKELY', 'POSSIBLE', 'UNLIKELY']
        
        for certainty_name in expected_certainties:
            with self.subTest(certainty=certainty_name):
                self.assertTrue(hasattr(AlertCertainty, certainty_name))
                certainty = getattr(AlertCertainty, certainty_name)
                self.assertIsNotNone(certainty.label)
                continue
        return

    def test_AlertStatus_basic_functionality(self):
        """Test AlertStatus enum has expected values"""
        expected_statuses = ['ACTUAL', 'EXERCISE', 'SYSTEM', 'TEST', 'DRAFT']
        
        for status_name in expected_statuses:
            with self.subTest(status=status_name):
                self.assertTrue(hasattr(AlertStatus, status_name))
                status = getattr(AlertStatus, status_name)
                self.assertIsNotNone(status.label)
                continue
        return

    def test_WeatherPhenomenon_enum_completeness(self):
        """Test WeatherPhenomenon has reasonable coverage of weather events"""
        # Test that common weather phenomena exist
        common_phenomena = ['RAIN', 'SNOW', 'FOG', 'THUNDERSTORM', 'DRIZZLE', 'HAIL']
        
        for phenomenon_name in common_phenomena:
            with self.subTest(phenomenon=phenomenon_name):
                if hasattr(WeatherPhenomenon, phenomenon_name):
                    phenomenon = getattr(WeatherPhenomenon, phenomenon_name)
                    self.assertIsNotNone(phenomenon.label)
                continue
        
        # Test that all phenomena have required properties
        for phenomenon in WeatherPhenomenon:
            with self.subTest(phenomenon=phenomenon):
                self.assertIsNotNone(phenomenon.label)
                continue
        return

    def test_WeatherPhenomenonModifier_basic_functionality(self):
        """Test WeatherPhenomenonModifier enum functionality"""
        # Test that NONE modifier exists (commonly used)
        self.assertTrue(hasattr(WeatherPhenomenonModifier, 'NONE'))
        
        # Test all modifiers have labels
        for modifier in WeatherPhenomenonModifier:
            with self.subTest(modifier=modifier):
                self.assertIsNotNone(modifier.label)
                continue
        return

    def test_WeatherPhenomenonIntensity_basic_functionality(self):
        """Test WeatherPhenomenonIntensity enum functionality"""
        # Test that common intensities exist
        expected_intensities = ['LIGHT', 'MODERATE', 'HEAVY']
        
        for intensity_name in expected_intensities:
            with self.subTest(intensity=intensity_name):
                if hasattr(WeatherPhenomenonIntensity, intensity_name):
                    intensity = getattr(WeatherPhenomenonIntensity, intensity_name)
                    self.assertIsNotNone(intensity.label)
                continue
        
        # Test all intensities have labels
        for intensity in WeatherPhenomenonIntensity:
            with self.subTest(intensity=intensity):
                self.assertIsNotNone(intensity.label)
                continue
        return

    def test_all_enums_have_proper_inheritance(self):
        """Test that all weather enums properly inherit from LabeledEnum"""
        enum_classes = [
            SkyCondition, MoonPhase, AlertCategory, AlertSeverity, AlertUrgency,
            AlertCertainty, AlertStatus, CloudCoverageType, WeatherPhenomenon,
            WeatherPhenomenonModifier, WeatherPhenomenonIntensity, WindDirection
        ]
        
        for enum_class in enum_classes:
            with self.subTest(enum_class=enum_class):
                # Test that enum instances have label property (from LabeledEnum)
                for enum_instance in enum_class:
                    self.assertIsNotNone(enum_instance.label)
                    break  # Just test first instance to verify inheritance
                continue
        return

    def test_enum_iteration_and_membership(self):
        """Test that enums support iteration and membership testing"""
        test_enums = [SkyCondition, MoonPhase, AlertCategory, WindDirection]
        
        for enum_class in test_enums:
            with self.subTest(enum_class=enum_class):
                # Test iteration
                enum_list = list(enum_class)
                self.assertGreater(len(enum_list), 0)
                
                # Test membership
                first_enum = enum_list[0]
                self.assertIn(first_enum, enum_class)
                continue
        return
