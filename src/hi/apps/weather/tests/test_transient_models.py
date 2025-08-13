import logging
from datetime import datetime, time, timedelta

from hi.apps.weather.transient_models import (
    AstronomicalData,
    BooleanDataPoint,
    CommonWeatherData,
    DataPointList,
    DataPointSource,
    NotablePhenomenon,
    NumericDataPoint,
    Station,
    StringDataPoint,
    TimeDataPoint,
    TimeInterval,
    WeatherAlert,
    WeatherConditionsData,
    WeatherOverviewData,
)
from hi.apps.weather.enums import (
    AlertCategory,
    AlertCertainty,
    AlertSeverity,
    AlertStatus,
    AlertUrgency,
    MoonPhase,
    SkyCondition,
    WeatherEventType,
    WeatherPhenomenon,
    WeatherPhenomenonIntensity,
    WeatherPhenomenonModifier,
)
from hi.transient_models import GeographicLocation
from hi.units import UnitQuantity

from hi.tests.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestWeatherTransientModels(BaseTestCase):

    def setUp(self):
        """Set up common test data"""
        self.test_source = DataPointSource(
            id='test_source',
            label='Test Weather Source',
            abbreviation='TEST',
            priority=1
        )
        
        self.test_geo_location = GeographicLocation(
            latitude=UnitQuantity(40.7128, 'degree'),
            longitude=UnitQuantity(-74.0060, 'degree'),
            elevation=UnitQuantity(10, 'meter')
        )
        
        self.test_station = Station(
            source=self.test_source,
            station_id='TEST001',
            name='Test Station',
            geo_location=self.test_geo_location,
            station_url='https://test.example/station',
            observations_url='https://test.example/obs',
            forecast_url='https://test.example/forecast'
        )
        
        self.test_datetime = datetime(2024, 1, 15, 12, 0, 0)

    # DataPointSource Tests
    def test_DataPointSource_creation(self):
        """Test DataPointSource creation and properties"""
        source = DataPointSource(id='nws', label='National Weather Service', abbreviation='NWS', priority=1)
        
        self.assertEqual(source.id, 'nws')
        self.assertEqual(source.label, 'National Weather Service')
        self.assertEqual(source.priority, 1)

    def test_DataPointSource_equality_and_hash(self):
        """Test DataPointSource equality and hash methods"""
        source1 = DataPointSource(id='nws', label='National Weather Service', abbreviation='NWS', priority=1)
        source2 = DataPointSource(id='nws', label='Different Label', abbreviation='NWS', priority=2)
        source3 = DataPointSource(id='owm', label='OpenWeatherMap', abbreviation='OWM', priority=1)
        
        # Same ID should be equal
        self.assertEqual(source1, source2)
        self.assertEqual(hash(source1), hash(source2))
        
        # Different ID should not be equal
        self.assertNotEqual(source1, source3)
        self.assertNotEqual(hash(source1), hash(source3))
        
        # Should not equal non-DataPointSource objects
        self.assertNotEqual(source1, "not_a_source")

    # Station Tests
    def test_Station_creation_and_properties(self):
        """Test Station creation and derived properties"""
        station = self.test_station
        
        self.assertEqual(station.source, self.test_source)
        self.assertEqual(station.station_id, 'TEST001')
        self.assertEqual(station.name, 'Test Station')
        self.assertEqual(station.geo_location, self.test_geo_location)
        self.assertEqual(station.elevation, self.test_geo_location.elevation)
        self.assertEqual(station.key, f'{self.test_source}:TEST001')

    def test_Station_equality_and_hash(self):
        """Test Station equality and hash methods"""
        station1 = Station(source=self.test_source, station_id='TEST001')
        station2 = Station(source=self.test_source, station_id='TEST001', name='Different Name')
        station3 = Station(source=self.test_source, station_id='TEST002')
        
        # Same source and station_id should be equal
        self.assertEqual(station1, station2)
        self.assertEqual(hash(station1), hash(station2))
        
        # Different station_id should not be equal
        self.assertNotEqual(station1, station3)

    def test_Station_without_geo_location(self):
        """Test Station without geographic location"""
        station = Station(source=self.test_source, station_id='TEST001')
        self.assertIsNone(station.elevation)

    # DataPoint Base Class Tests
    def test_DataPoint_base_properties(self):
        """Test DataPoint base class properties"""
        dp = NumericDataPoint(
            station=self.test_station,
            source_datetime=self.test_datetime,
            quantity_ave=UnitQuantity(25.0, 'celsius')
        )
        
        self.assertEqual(dp.station, self.test_station)
        self.assertEqual(dp.source_datetime, self.test_datetime)
        self.assertEqual(dp.elevation, self.test_geo_location.elevation)
        self.assertEqual(dp.source, self.test_source)

    def test_DataPoint_without_station(self):
        """Test DataPoint behavior with None station"""
        dp = NumericDataPoint(
            station=None,
            source_datetime=self.test_datetime,
            quantity_ave=UnitQuantity(25.0, 'celsius')
        )
        
        self.assertIsNone(dp.elevation)
        self.assertIsNone(dp.source)

    # NumericDataPoint Tests
    def test_NumericDataPoint_quantity_calculations(self):
        """Test NumericDataPoint quantity property calculations"""
        test_cases = [
            # min, max, ave, expected_quantity
            (None, None, 25.0, 25.0),  # ave only
            (20.0, None, None, 20.0),  # min only
            (None, 30.0, None, 30.0),  # max only
            (20.0, 30.0, None, 25.0),  # min/max average
            (20.0, None, 25.0, 25.0),  # ave takes precedence
            (None, 30.0, 25.0, 25.0),  # ave takes precedence
            (20.0, 30.0, 25.0, 25.0),  # ave takes precedence
        ]
        
        for min_val, max_val, ave_val, expected in test_cases:
            with self.subTest(min=min_val, max=max_val, ave=ave_val):
                kwargs = {
                    'station': self.test_station,
                    'source_datetime': self.test_datetime,
                }
                if min_val is not None:
                    kwargs['quantity_min'] = UnitQuantity(min_val, 'celsius')
                if max_val is not None:
                    kwargs['quantity_max'] = UnitQuantity(max_val, 'celsius')
                if ave_val is not None:
                    kwargs['quantity_ave'] = UnitQuantity(ave_val, 'celsius')
                
                dp = NumericDataPoint(**kwargs)
                self.assertAlmostEqual(dp.quantity.magnitude, expected, places=1)

    def test_NumericDataPoint_post_init_filling(self):
        """Test that __post_init__ fills missing values correctly"""
        # Test ave fills min/max
        dp = NumericDataPoint(
            station=self.test_station,
            source_datetime=self.test_datetime,
            quantity_ave=UnitQuantity(25.0, 'celsius')
        )
        self.assertEqual(dp.quantity_min.magnitude, 25.0)
        self.assertEqual(dp.quantity_max.magnitude, 25.0)
        
        # Test min fills ave/max
        dp = NumericDataPoint(
            station=self.test_station,
            source_datetime=self.test_datetime,
            quantity_min=UnitQuantity(20.0, 'celsius')
        )
        self.assertEqual(dp.quantity_ave.magnitude, 20.0)
        self.assertEqual(dp.quantity_max.magnitude, 20.0)

    def test_NumericDataPoint_validation_error(self):
        """Test NumericDataPoint raises error when no values provided"""
        with self.assertRaises(ValueError):
            NumericDataPoint(
                station=self.test_station,
                source_datetime=self.test_datetime
            )

    # BooleanDataPoint Tests
    def test_BooleanDataPoint(self):
        """Test BooleanDataPoint creation and properties"""
        dp = BooleanDataPoint(
            station=self.test_station,
            source_datetime=self.test_datetime,
            value=True
        )
        
        self.assertTrue(dp.value)
        self.assertEqual(dp.station, self.test_station)

    # StringDataPoint Tests
    def test_StringDataPoint(self):
        """Test StringDataPoint creation and properties"""
        dp = StringDataPoint(
            station=self.test_station,
            source_datetime=self.test_datetime,
            value="Partly Cloudy"
        )
        
        self.assertEqual(dp.value, "Partly Cloudy")
        self.assertEqual(dp.station, self.test_station)

    # TimeDataPoint Tests
    def test_TimeDataPoint(self):
        """Test TimeDataPoint creation and properties"""
        test_time = time(6, 30, 0)
        dp = TimeDataPoint(
            station=self.test_station,
            source_datetime=self.test_datetime,
            value=test_time
        )
        
        self.assertEqual(dp.value, test_time)
        self.assertEqual(dp.station, self.test_station)

    # TimeInterval Tests
    def test_TimeInterval_creation_and_properties(self):
        """Test TimeInterval creation and properties"""
        start = datetime(2024, 1, 15, 12, 0)
        end = datetime(2024, 1, 15, 18, 0)
        name_dp = StringDataPoint(
            station=self.test_station,
            source_datetime=self.test_datetime,
            value="Afternoon"
        )
        
        interval = TimeInterval(start=start, end=end, name=name_dp)
        
        self.assertEqual(interval.start, start)
        self.assertEqual(interval.end, end)
        self.assertEqual(interval.name, name_dp)
        self.assertEqual(interval.interval_period, timedelta(hours=6))

    def test_TimeInterval_validation(self):
        """Test TimeInterval validation of start < end"""
        start = datetime(2024, 1, 15, 18, 0)
        end = datetime(2024, 1, 15, 12, 0)  # End before start
        
        with self.assertRaises(AssertionError):
            TimeInterval(start=start, end=end)

    def test_TimeInterval_overlaps(self):
        """Test TimeInterval overlap detection"""
        interval1 = TimeInterval(
            start=datetime(2024, 1, 15, 12, 0),
            end=datetime(2024, 1, 15, 18, 0)
        )
        interval2 = TimeInterval(
            start=datetime(2024, 1, 15, 15, 0),
            end=datetime(2024, 1, 15, 21, 0)
        )
        interval3 = TimeInterval(
            start=datetime(2024, 1, 15, 19, 0),
            end=datetime(2024, 1, 15, 22, 0)
        )
        
        # Should overlap
        self.assertTrue(interval1.overlaps(interval2))
        self.assertTrue(interval2.overlaps(interval1))
        
        # Should not overlap
        self.assertFalse(interval1.overlaps(interval3))
        self.assertFalse(interval3.overlaps(interval1))

    def test_TimeInterval_overlap_seconds(self):
        """Test TimeInterval overlap duration calculation"""
        interval1 = TimeInterval(
            start=datetime(2024, 1, 15, 12, 0),
            end=datetime(2024, 1, 15, 18, 0)
        )
        interval2 = TimeInterval(
            start=datetime(2024, 1, 15, 15, 0),
            end=datetime(2024, 1, 15, 21, 0)
        )
        
        overlap_seconds = interval1.overlap_seconds(interval2)
        self.assertEqual(overlap_seconds, 3 * 3600)  # 3 hours in seconds

    def test_TimeInterval_comparison(self):
        """Test TimeInterval comparison operators"""
        interval1 = TimeInterval(
            start=datetime(2024, 1, 15, 12, 0),
            end=datetime(2024, 1, 15, 18, 0)
        )
        interval2 = TimeInterval(
            start=datetime(2024, 1, 15, 15, 0),
            end=datetime(2024, 1, 15, 21, 0)
        )
        interval3 = TimeInterval(
            start=datetime(2024, 1, 15, 12, 0),
            end=datetime(2024, 1, 15, 18, 0)
        )
        
        self.assertTrue(interval1 < interval2)
        self.assertFalse(interval2 < interval1)
        self.assertEqual(interval1, interval3)
        self.assertEqual(hash(interval1), hash(interval3))

    # CommonWeatherData Tests
    def test_CommonWeatherData_sky_condition(self):
        """Test sky condition calculation from cloud cover"""
        test_cases = [
            (0, SkyCondition.CLEAR),
            (10, SkyCondition.CLEAR),
            (15, SkyCondition.MOSTLY_CLEAR),
            (35, SkyCondition.MOSTLY_CLEAR),
            (40, SkyCondition.PARTLY_CLOUDY),
            (60, SkyCondition.PARTLY_CLOUDY),
            (65, SkyCondition.MOSTLY_CLOUDY),
            (85, SkyCondition.MOSTLY_CLOUDY),
            (90, SkyCondition.CLOUDY),
            (100, SkyCondition.CLOUDY),
        ]
        
        for cloud_cover_percent, expected_condition in test_cases:
            with self.subTest(cloud_cover=cloud_cover_percent):
                weather_data = CommonWeatherData(
                    cloud_cover=NumericDataPoint(
                        station=self.test_station,
                        source_datetime=self.test_datetime,
                        quantity_ave=UnitQuantity(cloud_cover_percent, 'percent')
                    )
                )
                
                self.assertEqual(weather_data.sky_condition, expected_condition)

    def test_CommonWeatherData_sky_condition_no_cloud_cover(self):
        """Test sky condition when cloud cover is None"""
        weather_data = CommonWeatherData()
        self.assertIsNone(weather_data.sky_condition)

    # WeatherConditionsData Tests
    def test_WeatherConditionsData_has_precipitation(self):
        """Test precipitation detection"""
        # No precipitation data
        weather_data = WeatherConditionsData()
        self.assertFalse(weather_data.has_precipitation)
        
        # With precipitation data
        weather_data = WeatherConditionsData(
            precipitation_last_hour=NumericDataPoint(
                station=self.test_station,
                source_datetime=self.test_datetime,
                quantity_ave=UnitQuantity(2.5, 'mm')
            )
        )
        self.assertTrue(weather_data.has_precipitation)

    # AstronomicalData Tests
    def test_AstronomicalData_moon_phase_calculation(self):
        """Test moon phase calculation from illumination and waxing status"""
        test_cases = [
            (0, True, MoonPhase.NEW_MOON),
            (25, True, MoonPhase.WAXING_CRESCENT),
            (50, True, MoonPhase.FIRST_QUARTER),
            (75, True, MoonPhase.WAXING_GIBBOUS),
            (100, True, MoonPhase.FULL_MOON),
            (75, False, MoonPhase.WANING_GIBBOUS),
            (50, False, MoonPhase.LAST_QUARTER),
            (25, False, MoonPhase.WANING_CRESCENT),
        ]
        
        for illumination, is_waxing, expected_phase in test_cases:
            with self.subTest(illumination=illumination, waxing=is_waxing):
                astro_data = AstronomicalData(
                    moon_illumnination=NumericDataPoint(
                        station=self.test_station,
                        source_datetime=self.test_datetime,
                        quantity_ave=UnitQuantity(illumination, 'percent')
                    ),
                    moon_is_waxing=BooleanDataPoint(
                        station=self.test_station,
                        source_datetime=self.test_datetime,
                        value=is_waxing
                    )
                )
                
                self.assertEqual(astro_data.moon_phase, expected_phase)

    def test_AstronomicalData_moon_phase_missing_data(self):
        """Test moon phase when illumination or waxing data is missing"""
        # Missing illumination
        astro_data = AstronomicalData(
            moon_is_waxing=BooleanDataPoint(
                station=self.test_station,
                source_datetime=self.test_datetime,
                value=True
            )
        )
        self.assertIsNone(astro_data.moon_phase)
        
        # Missing waxing status
        astro_data = AstronomicalData(
            moon_illumnination=NumericDataPoint(
                station=self.test_station,
                source_datetime=self.test_datetime,
                quantity_ave=UnitQuantity(50, 'percent')
            )
        )
        self.assertIsNone(astro_data.moon_phase)

    def test_AstronomicalData_days_until_full_moon(self):
        """Test days until full moon calculation"""
        test_data_list = [
            {'percent': 0.0, 'is_waxing': True, 'expect': 15},
            {'percent': 25.0, 'is_waxing': True, 'expect': 11},
            {'percent': 50.0, 'is_waxing': True, 'expect': 7},
            {'percent': 75.0, 'is_waxing': True, 'expect': 4},
            {'percent': 100.0, 'is_waxing': True, 'expect': 0},
            {'percent': 100.0, 'is_waxing': False, 'expect': 0},
            {'percent': 75.0, 'is_waxing': False, 'expect': 26},
            {'percent': 50.0, 'is_waxing': False, 'expect': 22},
            {'percent': 25.0, 'is_waxing': False, 'expect': 19},
            {'percent': 0.0, 'is_waxing': False, 'expect': 15},
        ]
        
        for test_data in test_data_list:
            with self.subTest(test_data=test_data):
                astro_data = AstronomicalData(
                    moon_illumnination=NumericDataPoint(
                        station=self.test_station,
                        source_datetime=self.test_datetime,
                        quantity_ave=UnitQuantity(test_data['percent'], 'percent')
                    ),
                    moon_is_waxing=BooleanDataPoint(
                        station=self.test_station,
                        source_datetime=self.test_datetime,
                        value=test_data['is_waxing']
                    )
                )
                
                self.assertAlmostEqual(
                    astro_data.days_until_full_moon,
                    test_data['expect'],
                    delta=1  # Allow 1 day tolerance
                )

    def test_AstronomicalData_days_until_new_moon(self):
        """Test days until new moon calculation"""
        test_data_list = [
            {'percent': 0.0, 'is_waxing': True, 'expect': 0},
            {'percent': 25.0, 'is_waxing': True, 'expect': 26},
            {'percent': 50.0, 'is_waxing': True, 'expect': 22},
            {'percent': 75.0, 'is_waxing': True, 'expect': 19},
            {'percent': 100.0, 'is_waxing': True, 'expect': 15},
            {'percent': 100.0, 'is_waxing': False, 'expect': 15},
            {'percent': 75.0, 'is_waxing': False, 'expect': 11},
            {'percent': 50.0, 'is_waxing': False, 'expect': 7},
            {'percent': 25.0, 'is_waxing': False, 'expect': 4},
            {'percent': 0.0, 'is_waxing': False, 'expect': 0},
        ]
        
        for test_data in test_data_list:
            with self.subTest(test_data=test_data):
                astro_data = AstronomicalData(
                    moon_illumnination=NumericDataPoint(
                        station=self.test_station,
                        source_datetime=self.test_datetime,
                        quantity_ave=UnitQuantity(test_data['percent'], 'percent')
                    ),
                    moon_is_waxing=BooleanDataPoint(
                        station=self.test_station,
                        source_datetime=self.test_datetime,
                        value=test_data['is_waxing']
                    )
                )
                
                self.assertAlmostEqual(
                    astro_data.days_until_new_moon,
                    test_data['expect'],
                    delta=1  # Allow 1 day tolerance
                )

    # NotablePhenomenon Tests
    def test_NotablePhenomenon_string_representation(self):
        """Test NotablePhenomenon string formatting"""
        # Test normal phenomenon
        phenomenon = NotablePhenomenon(
            weather_phenomenon=WeatherPhenomenon.RAIN,
            weather_phenomenon_modifier=WeatherPhenomenonModifier.NONE,
            weather_phenomenon_intensity=WeatherPhenomenonIntensity.LIGHT,
            in_vicinity=False
        )
        
        expected = f"{WeatherPhenomenon.RAIN.label} ({WeatherPhenomenonIntensity.LIGHT.label})"
        self.assertEqual(str(phenomenon), expected)
        
        # Test vicinity phenomenon
        phenomenon_vicinity = NotablePhenomenon(
            weather_phenomenon=WeatherPhenomenon.RAIN,
            weather_phenomenon_modifier=WeatherPhenomenonModifier.NONE,
            weather_phenomenon_intensity=WeatherPhenomenonIntensity.MODERATE,
            in_vicinity=True
        )
        
        expected_vicinity = f"Nearby: {WeatherPhenomenon.RAIN.label} ({WeatherPhenomenonIntensity.MODERATE.label})"
        self.assertEqual(str(phenomenon_vicinity), expected_vicinity)

    # WeatherAlert Tests
    def test_WeatherAlert_creation(self):
        """Test WeatherAlert creation with all required fields"""
        alert = WeatherAlert(
            event_type=WeatherEventType.WINTER_STORM,
            event="Winter Storm Warning",
            status=AlertStatus.ACTUAL,
            category=AlertCategory.METEOROLOGICAL,
            headline="Winter Storm Warning issued",
            description="Heavy snow expected",
            instruction="Avoid travel",
            affected_areas="Northern counties",
            effective=datetime(2024, 1, 15, 6, 0),
            onset=datetime(2024, 1, 15, 12, 0),
            expires=datetime(2024, 1, 16, 6, 0),
            ends=datetime(2024, 1, 16, 0, 0),
            severity=AlertSeverity.SEVERE,
            certainty=AlertCertainty.LIKELY,
            urgency=AlertUrgency.EXPECTED
        )
        
        self.assertEqual(alert.event, "Winter Storm Warning")
        self.assertEqual(alert.severity, AlertSeverity.SEVERE)
        self.assertEqual(alert.urgency, AlertUrgency.EXPECTED)

    # EnvironmentalData Tests
    def test_EnvironmentalData_stations_property(self):
        """Test stations property extracts unique stations from data points"""
        # Create another station for testing
        other_source = DataPointSource(id='other', label='Other Source', abbreviation='OTHER', priority=2)
        other_station = Station(source=other_source, station_id='OTHER001')
        
        weather_data = CommonWeatherData(
            temperature=NumericDataPoint(
                station=self.test_station,
                source_datetime=self.test_datetime,
                quantity_ave=UnitQuantity(25.0, 'celsius')
            ),
            relative_humidity=NumericDataPoint(
                station=self.test_station,  # Same station
                source_datetime=self.test_datetime,
                quantity_ave=UnitQuantity(60, 'percent')
            ),
            windspeed=NumericDataPoint(
                station=other_station,  # Different station
                source_datetime=self.test_datetime,
                quantity_ave=UnitQuantity(10, 'km/h')
            )
        )
        
        stations = weather_data.stations
        self.assertEqual(len(stations), 2)  # Should have unique stations
        station_keys = {station.key for station in stations}
        self.assertIn(self.test_station.key, station_keys)
        self.assertIn(other_station.key, station_keys)

    # DataPointList Tests
    def test_DataPointList(self):
        """Test DataPointList creation and properties"""
        phenomena = [
            NotablePhenomenon(
                weather_phenomenon=WeatherPhenomenon.RAIN,
                weather_phenomenon_modifier=WeatherPhenomenonModifier.NONE,
                weather_phenomenon_intensity=WeatherPhenomenonIntensity.LIGHT,
                in_vicinity=False
            ),
            NotablePhenomenon(
                weather_phenomenon=WeatherPhenomenon.SNOW,
                weather_phenomenon_modifier=WeatherPhenomenonModifier.NONE,
                weather_phenomenon_intensity=WeatherPhenomenonIntensity.HEAVY,
                in_vicinity=True
            )
        ]
        
        dp_list = DataPointList(
            station=self.test_station,
            source_datetime=self.test_datetime,
            list_value=phenomena
        )
        
        self.assertEqual(len(dp_list.list_value), 2)
        self.assertEqual(dp_list.list_value[0], phenomena[0])
        self.assertEqual(dp_list.list_value[1], phenomena[1])

    # WeatherOverviewData Tests
    def test_WeatherOverviewData(self):
        """Test WeatherOverviewData creation"""
        current_conditions = WeatherConditionsData(
            temperature=NumericDataPoint(
                station=self.test_station,
                source_datetime=self.test_datetime,
                quantity_ave=UnitQuantity(25.0, 'celsius')
            )
        )
        
        astronomical = AstronomicalData(
            sunrise=TimeDataPoint(
                station=self.test_station,
                source_datetime=self.test_datetime,
                value=time(6, 30)
            )
        )
        
        overview = WeatherOverviewData(
            current_conditions_data=current_conditions,
            todays_astronomical_data=astronomical
        )
        
        self.assertEqual(overview.current_conditions_data, current_conditions)
        self.assertEqual(overview.todays_astronomical_data, astronomical)

    # Integration Tests for Bug Fixes
    def test_bug_fix_DataPointSource_equality(self):
        """Test the bug fix for DataPointSource.__eq__ method"""
        source1 = DataPointSource(id='test', label='Test', abbreviation='TEST', priority=1)
        source2 = DataPointSource(id='test', label='Test', abbreviation='TEST', priority=1)
        station = Station(source=source1, station_id='TEST001')
        
        # This should not raise an error now
        self.assertEqual(source1, source2)
        self.assertNotEqual(source1, station)  # Different types
        self.assertNotEqual(source1, "not_a_source")  # Different types

    def test_bug_fix_moon_phase_null_safety(self):
        """Test the bug fix for moon_phase null safety"""
        # Test with missing moon_is_waxing
        astro_data = AstronomicalData(
            moon_illumnination=NumericDataPoint(
                station=self.test_station,
                source_datetime=self.test_datetime,
                quantity_ave=UnitQuantity(50, 'percent')
            ),
            moon_is_waxing=None  # This should not cause an error
        )
        
        # Should return None safely, not crash
        self.assertIsNone(astro_data.moon_phase)
        
        # Test with missing moon_illumnination
        astro_data2 = AstronomicalData(
            moon_illumnination=None,
            moon_is_waxing=BooleanDataPoint(
                station=self.test_station,
                source_datetime=self.test_datetime,
                value=True
            )
        )
        
        # Should return None safely
        self.assertIsNone(astro_data2.moon_phase)
