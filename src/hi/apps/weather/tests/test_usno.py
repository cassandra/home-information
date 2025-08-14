import json
import logging
from datetime import datetime, date, time
from unittest.mock import Mock, patch
import pytz

from hi.apps.weather.weather_sources.usno import (
    USNO,
)
from hi.apps.weather.transient_models import (
    AstronomicalData,
    IntervalAstronomical,
    TimeDataPoint,
    TimeInterval,
    Station,
    BooleanDataPoint,
    NumericDataPoint,
)
from hi.transient_models import GeographicLocation
from hi.units import UnitQuantity

from hi.tests.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestUSNO(BaseTestCase):
    """Test the US Naval Observatory weather data source."""

    def setUp(self):
        """Set up test data."""
        self.usno = USNO()
        self.test_location = GeographicLocation(
            latitude = 30.2711,
            longitude = -97.7437,
            elevation = UnitQuantity(167.0, 'm')
        )
        return

    def test_initialization(self):
        """Test USNO initialization."""
        self.assertEqual(self.usno.id, 'usno')
        self.assertEqual(self.usno.label, 'US Naval Observatory')
        self.assertEqual(self.usno.priority, 2)  # Higher priority than sunrise-sunset.org
        self.assertIsNotNone(self.usno.data_point_source)
        self.assertEqual(self.usno.data_point_source.id, 'usno')
        self.assertFalse(self.usno.requires_api_key())
        self.assertTrue(self.usno.get_default_enabled_state())
        return

    def test_source_id_consistency(self):
        """Test that SOURCE_ID class variable matches instance id."""
        self.assertEqual(USNO.SOURCE_ID, 'usno')
        self.assertEqual(self.usno.id, USNO.SOURCE_ID)
        return

    @patch('hi.apps.weather.weather_sources.usno.requests.get')
    def test_get_astronomical_api_data_from_api_success(self, mock_get):
        """Test successful API call for astronomical data."""
        # Mock successful API response based on real USNO API response
        mock_response_data = {
            "apiversion": "4.0.1",
            "geometry": {
                "coordinates": [-97.74, 30.27],
                "type": "Point"
            },
            "properties": {
                "data": {
                    "closestphase": {
                        "day": 16,
                        "month": 3,
                        "phase": "First Quarter",
                        "time": "23:11",
                        "year": 2024
                    },
                    "curphase": "Waxing Crescent",
                    "day": 15,
                    "day_of_week": "Friday",
                    "fracillum": "35%",
                    "isdst": False,
                    "moondata": [
                        {"phen": "Set", "time": "00:52"},
                        {"phen": "Rise", "time": "11:11"},
                        {"phen": "Upper Transit", "time": "18:32"}
                    ],
                    "sundata": [
                        {"phen": "Begin Civil Twilight", "time": "07:16"},
                        {"phen": "Rise", "time": "07:40"},
                        {"phen": "Upper Transit", "time": "13:40"},
                        {"phen": "Set", "time": "19:40"},
                        {"phen": "End Civil Twilight", "time": "20:04"}
                    ],
                    "tz": -5.0,
                    "year": 2024
                }
            },
            "type": "Feature"
        }

        mock_response = Mock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        target_date = date(2024, 3, 15)
        result = self.usno._get_astronomical_api_data_from_api(
            geographic_location = self.test_location,
            target_date = target_date
        )

        self.assertIsInstance(result, dict)
        self.assertEqual(result['apiversion'], '4.0.1')
        self.assertIn('properties', result)
        
        # Verify correct URL was called with proper parameters
        mock_get.assert_called_once()
        actual_url = mock_get.call_args[0][0]
        self.assertIn(f'coords={self.test_location.latitude},{self.test_location.longitude}', actual_url)
        self.assertIn(f'date={target_date.isoformat()}', actual_url)
        self.assertIn('tz=', actual_url)
        return

    @patch('hi.apps.weather.weather_sources.usno.requests.get')
    def test_get_astronomical_api_data_from_api_error(self, mock_get):
        """Test API error handling."""
        # Mock HTTP error response
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = Exception("HTTP 404")
        mock_get.return_value = mock_response

        target_date = date(2024, 3, 15)
        with self.assertRaises(Exception):
            self.usno._get_astronomical_api_data_from_api(
                geographic_location = self.test_location,
                target_date = target_date
            )
        return

    def test_parse_astronomical_data_api_error(self):
        """Test parsing with API errors - HIGH VALUE test for API integration."""
        api_data = {
            "error": "Invalid coordinates"
        }
        
        with self.assertRaises(ValueError) as context:
            self.usno._parse_astronomical_data(
                api_data = api_data,
                geographic_location = self.test_location,
                target_date = date(2024, 3, 15)
            )
        
        self.assertIn("USNO API error", str(context.exception))
        return

    def test_parse_astronomical_data_missing_properties(self):
        """Test parsing with missing properties field - HIGH VALUE test for API changes."""
        api_data = {
            "apiversion": "4.0.1",
            "type": "Feature"
            # Missing "properties" field
        }
        
        with self.assertRaises(ValueError) as context:
            self.usno._parse_astronomical_data(
                api_data = api_data,
                geographic_location = self.test_location,
                target_date = date(2024, 3, 15)
            )
        
        self.assertIn('Missing "properties"', str(context.exception))
        return

    def test_parse_astronomical_data_missing_data(self):
        """Test parsing with missing data field - HIGH VALUE test for API changes."""
        api_data = {
            "apiversion": "4.0.1",
            "properties": {
                "data": {}  # Empty data field
            },
            "type": "Feature"
        }
        
        # This should not raise an exception, but should return AstronomicalData with no fields populated
        result = self.usno._parse_astronomical_data(
            api_data = api_data,
            geographic_location = self.test_location,
            target_date = date(2024, 3, 15)
        )
        
        # Should return valid AstronomicalData but with all fields None
        self.assertIsInstance(result, AstronomicalData)
        self.assertIsNone(result.sunrise)
        self.assertIsNone(result.sunset)
        self.assertIsNone(result.moon_illumnination)
        return

    @patch('hi.apps.common.datetimeproxy.now')
    def test_parse_astronomical_data_success(self, mock_now):
        """Test successful parsing of astronomical data - HIGH VALUE for field mapping and moon phase."""
        # Mock current time
        mock_source_datetime = datetime(2024, 3, 15, 14, 30, 0)
        mock_now.return_value = mock_source_datetime

        # Valid API response with all astronomical fields including moon phase data
        api_data = {
            "apiversion": "4.0.1",
            "properties": {
                "data": {
                    "curphase": "Waxing Crescent",
                    "fracillum": "35%",
                    "sundata": [
                        {"phen": "Rise", "time": "07:40"},
                        {"phen": "Set", "time": "19:40"},
                        {"phen": "Upper Transit", "time": "13:40"},
                    ],
                    "moondata": [
                        {"phen": "Rise", "time": "11:11"},
                        {"phen": "Set", "time": "00:52"},
                    ],
                    "tz": -5.0
                }
            }
        }

        target_date = date(2024, 3, 15)
        result = self.usno._parse_astronomical_data(
            api_data = api_data,
            geographic_location = self.test_location,
            target_date = target_date
        )

        # Verify result is AstronomicalData instance
        self.assertIsInstance(result, AstronomicalData)

        # Verify solar fields are populated
        self.assertIsInstance(result.sunrise, TimeDataPoint)
        self.assertEqual(result.sunrise.value, time(7, 40))
        self.assertIsInstance(result.sunset, TimeDataPoint)
        self.assertEqual(result.sunset.value, time(19, 40))
        self.assertIsInstance(result.solar_noon, TimeDataPoint)
        self.assertEqual(result.solar_noon.value, time(13, 40))

        # Verify lunar fields are populated
        self.assertIsInstance(result.moonrise, TimeDataPoint)
        self.assertEqual(result.moonrise.value, time(11, 11))
        self.assertIsInstance(result.moonset, TimeDataPoint)
        self.assertEqual(result.moonset.value, time(0, 52))

        # Verify moon phase data - this is the key new feature
        self.assertIsInstance(result.moon_illumnination, NumericDataPoint)
        self.assertEqual(result.moon_illumnination.quantity.magnitude, 35.0)
        self.assertEqual(result.moon_illumnination.quantity.units, UnitQuantity(1, 'percent').units)
        
        self.assertIsInstance(result.moon_is_waxing, BooleanDataPoint)
        self.assertTrue(result.moon_is_waxing.value)

        # Verify station information
        self.assertIsInstance(result.sunrise.station, Station)
        self.assertEqual(result.sunrise.station.source.id, 'usno')
        self.assertIn('usno:', result.sunrise.station.station_id)
        self.assertIn('USNO', result.sunrise.station.name)
        return

    def test_parse_usno_time_valid_formats(self):
        """Test time parsing with various valid formats - HIGH VALUE for time handling."""
        test_cases = [
            ("07:40", time(7, 40)),
            ("19:40", time(19, 40)),
            ("00:52", time(0, 52)),
            ("23:59", time(23, 59)),
            ("12:00", time(12, 0)),
        ]

        for time_str, expected_time in test_cases:
            result = self.usno._parse_usno_time(time_str)
            self.assertEqual(result, expected_time, f"Failed for time_str: {time_str}")
        return

    def test_parse_usno_time_invalid_formats(self):
        """Test time parsing with invalid formats - HIGH VALUE for robustness."""
        invalid_times = [
            "",
            "invalid",
            "25:00",  # Invalid hour
            "12:60",  # Invalid minute
            "12",     # Missing minute
            "12:30:45",  # Too many parts
            "ab:cd",  # Non-numeric
        ]

        for time_str in invalid_times:
            result = self.usno._parse_usno_time(time_str)
            self.assertIsNone(result, f"Should return None for invalid time: {time_str}")
        return

    def test_determine_moon_waxing_status(self):
        """Test moon phase waxing status determination - HIGH VALUE for moon phase integration."""
        test_cases = [
            ("Waxing Crescent", True),
            ("Waning Crescent", False),
            ("Waxing Gibbous", True),
            ("Waning Gibbous", False),
            ("New Moon", True),
            ("Full Moon", False),
            ("First Quarter", True),
            ("Last Quarter", False),
            ("Third Quarter", False),
            ("Unknown Phase", None),
            ("", None),
        ]

        for phase_name, expected_result in test_cases:
            result = self.usno._determine_moon_waxing_status(phase_name)
            self.assertEqual(result, expected_result, f"Failed for phase: {phase_name}")
        return

    def test_parse_astronomical_data_partial_fields(self):
        """Test parsing with some missing fields - HIGH VALUE for API robustness."""
        # API response with only some fields
        api_data = {
            "properties": {
                "data": {
                    "sundata": [
                        {"phen": "Rise", "time": "07:40"},
                        # "Set" missing - should not crash
                    ],
                    "moondata": [
                        # Empty - should not crash
                    ],
                    "curphase": "Waxing Crescent",
                    # "fracillum" missing - should not crash
                }
            }
        }

        with patch('hi.apps.common.datetimeproxy.now') as mock_now:
            mock_now.return_value = datetime(2024, 3, 15, 14, 30, 0)
            
            result = self.usno._parse_astronomical_data(
                api_data = api_data,
                geographic_location = self.test_location,
                target_date = date(2024, 3, 15)
            )

            # Should have sunrise but not sunset
            self.assertIsInstance(result.sunrise, TimeDataPoint)
            self.assertIsNone(result.sunset)
            
            # Should not have moon phase data without fracillum
            self.assertIsNone(result.moon_illumnination)
            self.assertIsNone(result.moon_is_waxing)
        return

    def test_get_astronomical_data_caching(self):
        """Test Redis caching behavior - HIGH VALUE for performance optimization."""
        target_date = date(2024, 3, 15)
        cache_key = f'ws:usno:astronomical:{self.test_location.latitude:.3f}:{self.test_location.longitude:.3f}:{target_date}'
        
        # Mock cached data
        cached_api_data = {
            "properties": {
                "data": {
                    "sundata": [{"phen": "Rise", "time": "07:40"}],
                    "moondata": [],
                    "curphase": "Waxing Crescent",
                    "fracillum": "35%"
                }
            }
        }
        
        # Mock Redis client to return cached data and the API call
        with patch.object(self.usno, '_redis_client') as mock_redis, \
             patch.object(self.usno, '_get_astronomical_api_data_from_api') as mock_api_call:
            
            mock_redis.get.return_value = json.dumps(cached_api_data)
            
            with patch('hi.apps.common.datetimeproxy.now') as mock_now:
                mock_now.return_value = datetime(2024, 3, 15, 14, 30, 0)
                
                result = self.usno.get_astronomical_data(
                    geographic_location = self.test_location,
                    target_date = target_date
                )
            
            # Verify cache was checked and API was not called
            mock_redis.get.assert_called_once_with(cache_key)
            mock_api_call.assert_not_called()
            self.assertIsInstance(result, AstronomicalData)
        return

    @patch('hi.apps.weather.weather_sources.usno.USNO.get_astronomical_data')
    @patch('hi.apps.common.datetimeproxy.now')
    def test_get_astronomical_data_list_success(self, mock_now, mock_get_astronomical_data):
        """Test successful multi-day astronomical data fetching - HIGH VALUE for new feature."""
        # Mock current time
        mock_today = datetime(2024, 3, 15, 10, 0, 0)
        mock_now.return_value = mock_today
        
        # Mock timezone from superclass using property return value
        with patch.object(type(self.usno), 'tz_name',
                          new_callable=lambda: property(lambda self: 'America/Chicago')):
            # Mock successful astronomical data for each day
            mock_astronomical_data = AstronomicalData(
                sunrise = TimeDataPoint(
                    station = Station(
                        source = self.usno.data_point_source,
                        station_id = 'test-station',
                        name = 'Test Station',
                        geo_location = self.test_location,
                    ),
                    source_datetime = mock_today,
                    value = time(7, 40),
                ),
                moon_illumnination = NumericDataPoint(
                    station = Station(
                        source = self.usno.data_point_source,
                        station_id = 'test-station',
                        name = 'Test Station',
                        geo_location = self.test_location,
                    ),
                    source_datetime = mock_today,
                    quantity_ave = UnitQuantity(35.0, 'percent'),
                ),
            )
            mock_get_astronomical_data.return_value = mock_astronomical_data
            
            # Test with 3 days instead of default 10 for faster test
            result = self.usno.get_astronomical_data_list(
                geographic_location = self.test_location,
                days_count = 3
            )
            
            # Verify result structure
            self.assertIsInstance(result, list)
            self.assertEqual(len(result), 3)
            
            # Verify each item is IntervalAstronomical
            for item in result:
                self.assertIsInstance(item, IntervalAstronomical)
                self.assertIsInstance(item.interval, TimeInterval)
                self.assertIsInstance(item.data, AstronomicalData)
                
            # Verify get_astronomical_data was called for each day
            self.assertEqual(mock_get_astronomical_data.call_count, 3)
        return

    @patch('hi.apps.weather.weather_sources.usno.USNO.get_astronomical_data_list')
    @patch('hi.apps.weather.weather_sources.usno.USNO.get_astronomical_data')
    async def test_get_data_calls_multi_day_method(self,
                                                   mock_get_astronomical_data,
                                                   mock_get_astronomical_data_list):
        """Test that get_data calls the new multi-day method - HIGH VALUE for integration."""
        # Mock weather manager
        mock_weather_manager = Mock()
        mock_weather_manager.update_astronomical_data = Mock()
        mock_weather_manager.update_todays_astronomical_data = Mock()
        
        test_location = self.test_location  # Capture for lambda
        with patch.object(type(self.usno), 'geographic_location',
                          new_callable=lambda: property(lambda self: test_location)), \
             patch.object(self.usno, 'weather_manager_async', return_value=mock_weather_manager):
            
            # Mock successful multi-day data
            mock_interval_data = IntervalAstronomical(
                interval = TimeInterval(
                    start = datetime(2024, 3, 15, 6, 0, 0, tzinfo=pytz.UTC),
                    end = datetime(2024, 3, 15, 23, 59, 59, tzinfo=pytz.UTC)
                ),
                data = AstronomicalData()
            )
            mock_get_astronomical_data_list.return_value = [mock_interval_data]
            
            # Mock today's data
            mock_get_astronomical_data.return_value = AstronomicalData()
            
            # Call get_data
            await self.usno.get_data()
            
            # Verify multi-day method was called
            mock_get_astronomical_data_list.assert_called_once_with(
                geographic_location = self.test_location,
                days_count = 10
            )
            
            # Verify weather manager methods were called
            mock_weather_manager.update_astronomical_data.assert_called_once_with(
                data_point_source = self.usno.data_point_source,
                astronomical_data_list = [mock_interval_data]
            )
            
            # Verify today's data is also updated for backwards compatibility
            mock_get_astronomical_data.assert_called_once_with(
                geographic_location = self.test_location
            )
            mock_weather_manager.update_todays_astronomical_data.assert_called_once()
        return

    def test_astronomical_data_source_introspection(self):
        """Test data source introspection - HIGH VALUE for attribution logic."""
        # Create a minimal AstronomicalData instance with USNO source
        source_datetime = datetime(2024, 3, 15, 14, 30, 0)
        station = Station(
            source = self.usno.data_point_source,
            station_id = 'test-station',
            name = 'Test Station',
            geo_location = self.test_location,
            station_url = None,
            observations_url = None,
            forecast_url = None,
        )

        astronomical_data = AstronomicalData(
            sunrise = TimeDataPoint(
                station = station,
                source_datetime = source_datetime,
                value = time(7, 40),
            ),
            moon_illumnination = NumericDataPoint(
                station = station,
                source_datetime = source_datetime,
                quantity_ave = UnitQuantity(35.0, 'percent'),
            ),
        )

        # Test data_sources property
        data_sources = astronomical_data.data_sources
        self.assertEqual(len(data_sources), 1)
        source = list(data_sources)[0]
        self.assertEqual(source.id, 'usno')

        # Test data_source_counts property
        source_counts = astronomical_data.data_source_counts
        self.assertEqual(len(source_counts), 1)
        self.assertEqual(source_counts[source], 2)  # sunrise + moon_illumnination
        return

    def test_moon_phase_integration(self):
        """Test integration with existing moon phase fields - HIGH VALUE for moon phase feature."""
        # Test that USNO data integrates properly with moon phase calculation
        source_datetime = datetime(2024, 3, 15, 14, 30, 0)
        station = Station(
            source = self.usno.data_point_source,
            station_id = 'test-station',
            name = 'Test Station',
            geo_location = self.test_location,
        )

        # Test various moon phases (based on actual MoonPhase.from_illumination logic)
        test_cases = [
            (2.0, True, "NEW_MOON"),           # New moon - very low illumination (<=3), waxing
            (5.0, True, "WAXING_CRESCENT"),    # Waxing crescent (>3, <47)
            (35.0, True, "WAXING_CRESCENT"),   # Waxing crescent 
            (50.0, True, "FIRST_QUARTER"),     # First quarter (47-53)
            (75.0, True, "WAXING_GIBBOUS"),    # Waxing gibbous (53-97)
            (98.0, True, "FULL_MOON"),         # Full moon - high illumination (>=97)
            (75.0, False, "WANING_GIBBOUS"),   # Waning gibbous (53-97)
            (50.0, False, "LAST_QUARTER"),     # Last quarter (47-53)
            (25.0, False, "WANING_CRESCENT"),  # Waning crescent (3-47)
            (2.0, False, "NEW_MOON"),          # New moon - very low illumination (<=3), waning
        ]

        for illumination, is_waxing, expected_phase_name in test_cases:
            astronomical_data = AstronomicalData(
                moon_illumnination = NumericDataPoint(
                    station = station,
                    source_datetime = source_datetime,
                    quantity_ave = UnitQuantity(illumination, 'percent'),
                ),
                moon_is_waxing = BooleanDataPoint(
                    station = station,
                    source_datetime = source_datetime,
                    value = is_waxing,
                ),
            )

            # Verify moon phase calculation works
            moon_phase = astronomical_data.moon_phase
            self.assertIsNotNone(moon_phase)
            self.assertEqual(moon_phase.name, expected_phase_name,
                             f"Failed for illumination={illumination}, waxing={is_waxing}")
        return
