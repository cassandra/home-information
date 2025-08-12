import json
import logging
from datetime import datetime, date
import unittest
from unittest.mock import Mock, patch

import hi.apps.common.datetimeproxy as datetimeproxy
from hi.apps.weather.weather_sources.sunrise_sunset_org import (
    SunriseSunsetOrg,
    SunriseSunsetStatus,
)
from hi.apps.weather.transient_models import (
    AstronomicalData,
    TimeDataPoint,
    Station,
)
from hi.transient_models import GeographicLocation
from hi.units import UnitQuantity

from hi.tests.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestSunriseSunsetOrg(BaseTestCase):
    """Test the Sunrise-Sunset.org weather data source."""

    def setUp(self):
        """Set up test data."""
        self.sunrise_sunset = SunriseSunsetOrg()
        self.test_location = GeographicLocation(
            latitude = 30.2711,
            longitude = -97.7437,
            elevation = UnitQuantity(167.0, 'm')
        )
        return

    def test_initialization(self):
        """Test SunriseSunsetOrg initialization."""
        self.assertEqual(self.sunrise_sunset.id, 'sunrise-sunset-org')
        self.assertEqual(self.sunrise_sunset.label, 'Sunrise-Sunset.org')
        self.assertEqual(self.sunrise_sunset.priority, 3)
        self.assertIsNotNone(self.sunrise_sunset.data_point_source)
        self.assertEqual(self.sunrise_sunset.data_point_source.id, 'sunrise-sunset-org')
        self.assertFalse(self.sunrise_sunset.requires_api_key())
        self.assertTrue(self.sunrise_sunset.get_default_enabled_state())
        return

    def test_source_id_consistency(self):
        """Test that SOURCE_ID class variable matches instance id."""
        self.assertEqual(SunriseSunsetOrg.SOURCE_ID, 'sunrise-sunset-org')
        self.assertEqual(self.sunrise_sunset.id, SunriseSunsetOrg.SOURCE_ID)
        return

    @patch('hi.apps.weather.weather_sources.sunrise_sunset_org.requests.get')
    def test_get_astronomical_api_data_from_api_success(self, mock_get):
        """Test successful API call for astronomical data."""
        # Mock successful API response based on sunrise-sunset.org documentation
        mock_response_data = {
            "results": {
                "sunrise": "2024-03-15T12:30:00+00:00",
                "sunset": "2024-03-16T01:15:00+00:00", 
                "solar_noon": "2024-03-15T18:52:30+00:00",
                "day_length": "12:45:00",
                "civil_twilight_begin": "2024-03-15T12:05:00+00:00",
                "civil_twilight_end": "2024-03-16T01:40:00+00:00",
                "nautical_twilight_begin": "2024-03-15T11:35:00+00:00",
                "nautical_twilight_end": "2024-03-16T02:10:00+00:00",
                "astronomical_twilight_begin": "2024-03-15T11:05:00+00:00",
                "astronomical_twilight_end": "2024-03-16T02:40:00+00:00"
            },
            "status": "OK"
        }

        mock_response = Mock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        target_date = date(2024, 3, 15)
        result = self.sunrise_sunset._get_astronomical_api_data_from_api(
            geographic_location = self.test_location,
            target_date = target_date
        )

        self.assertIsInstance(result, dict)
        self.assertEqual(result['status'], 'OK')
        self.assertIn('results', result)
        
        # Verify correct URL was called with proper parameters
        mock_get.assert_called_once()
        actual_url = mock_get.call_args[0][0]
        self.assertIn(f'lat={self.test_location.latitude}', actual_url)
        self.assertIn(f'lng={self.test_location.longitude}', actual_url)
        self.assertIn(f'date={target_date.isoformat()}', actual_url)
        self.assertIn('formatted=0', actual_url)
        return

    @patch('hi.apps.weather.weather_sources.sunrise_sunset_org.requests.get')
    def test_get_astronomical_api_data_from_api_error(self, mock_get):
        """Test API error handling."""
        # Mock HTTP error response
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = Exception("HTTP 404")
        mock_get.return_value = mock_response

        target_date = date(2024, 3, 15)
        with self.assertRaises(Exception):
            self.sunrise_sunset._get_astronomical_api_data_from_api(
                geographic_location = self.test_location,
                target_date = target_date
            )
        return

    def test_parse_astronomical_data_status_error(self):
        """Test parsing with API status errors - HIGH VALUE test for API integration."""
        test_error_statuses = [
            SunriseSunsetStatus.INVALID_REQUEST.value,
            SunriseSunsetStatus.INVALID_DATE.value,
            SunriseSunsetStatus.UNKNOWN_ERROR.value,
            SunriseSunsetStatus.INVALID_TZID.value,
        ]

        for error_status in test_error_statuses:
            api_data = {
                "status": error_status,
                "results": {}
            }
            
            with self.assertRaises(ValueError) as context:
                self.sunrise_sunset._parse_astronomical_data(
                    api_data = api_data,
                    geographic_location = self.test_location,
                    target_date = date(2024, 3, 15)
                )
            
            self.assertIn(error_status, str(context.exception))
            continue
        return

    def test_parse_astronomical_data_missing_results(self):
        """Test parsing with missing results field - HIGH VALUE test for API changes."""
        api_data = {
            "status": "OK"
            # Missing "results" field
        }
        
        with self.assertRaises(ValueError) as context:
            self.sunrise_sunset._parse_astronomical_data(
                api_data = api_data,
                geographic_location = self.test_location,
                target_date = date(2024, 3, 15)
            )
        
        self.assertIn('Missing "results"', str(context.exception))
        return

    @patch('hi.apps.common.datetimeproxy.now')
    def test_parse_astronomical_data_success(self, mock_now):
        """Test successful parsing of astronomical data - HIGH VALUE for field mapping."""
        # Mock current time
        mock_source_datetime = datetime(2024, 3, 15, 14, 30, 0)
        mock_now.return_value = mock_source_datetime

        # No need to mock datetime.fromisoformat - it handles timezone-aware strings natively

        # Valid API response with all astronomical fields
        api_data = {
            "results": {
                "sunrise": "2024-03-15T12:30:00+00:00",
                "sunset": "2024-03-16T01:15:00+00:00",
                "solar_noon": "2024-03-15T18:52:30+00:00",
                "civil_twilight_begin": "2024-03-15T12:05:00+00:00",
                "civil_twilight_end": "2024-03-16T01:40:00+00:00",
                "nautical_twilight_begin": "2024-03-15T11:35:00+00:00",
                "nautical_twilight_end": "2024-03-16T02:10:00+00:00",
                "astronomical_twilight_begin": "2024-03-15T11:05:00+00:00",
                "astronomical_twilight_end": "2024-03-16T02:40:00+00:00"
            },
            "status": "OK"
        }

        target_date = date(2024, 3, 15)
        result = self.sunrise_sunset._parse_astronomical_data(
            api_data = api_data,
            geographic_location = self.test_location,
            target_date = target_date
        )

        # Verify result is AstronomicalData instance
        self.assertIsInstance(result, AstronomicalData)

        # Verify all expected fields are populated with TimeDataPoint instances
        astronomical_fields = [
            'sunrise', 'sunset', 'solar_noon',
            'civil_twilight_begin', 'civil_twilight_end',
            'nautical_twilight_begin', 'nautical_twilight_end',
            'astronomical_twilight_begin', 'astronomical_twilight_end'
        ]

        for field_name in astronomical_fields:
            field_value = getattr(result, field_name)
            self.assertIsInstance(field_value, TimeDataPoint, f'Field {field_name} should be TimeDataPoint')
            self.assertIsNotNone(field_value.value, f'Field {field_name} should have value')
            self.assertEqual(field_value.source_datetime, mock_source_datetime)
            continue

        # Verify station information
        self.assertIsInstance(result.sunrise.station, Station)
        self.assertEqual(result.sunrise.station.source.id, 'sunrise-sunset-org')
        self.assertIn('sunrise-sunset-org:', result.sunrise.station.station_id)
        self.assertIn('Sunrise-Sunset.org', result.sunrise.station.name)
        return

    def test_parse_astronomical_data_partial_fields(self):
        """Test parsing with some missing time fields - HIGH VALUE for API robustness."""
        # API response with only some fields (sunset missing)
        api_data = {
            "results": {
                "sunrise": "2024-03-15T12:30:00+00:00",
                # "sunset" missing - should not crash
                "solar_noon": "2024-03-15T18:52:30+00:00",
            },
            "status": "OK"
        }

        with patch('hi.apps.common.datetimeproxy.now') as mock_now:
            mock_now.return_value = datetime(2024, 3, 15, 14, 30, 0)
            
            result = self.sunrise_sunset._parse_astronomical_data(
                api_data = api_data,
                geographic_location = self.test_location,
                target_date = date(2024, 3, 15)
            )

            # Should have sunrise and solar_noon, but not sunset
            self.assertIsInstance(result.sunrise, TimeDataPoint)
            self.assertIsInstance(result.solar_noon, TimeDataPoint)
            self.assertIsNone(result.sunset)
        return

    def test_parse_astronomical_data_invalid_time_format(self):
        """Test handling of invalid time formats - HIGH VALUE for API changes."""
        api_data = {
            "results": {
                "sunrise": "invalid-time-format",
                "sunset": "2024-03-16T01:15:00+00:00",
            },
            "status": "OK"
        }

        with patch('hi.apps.common.datetimeproxy.now') as mock_now:
            mock_now.return_value = datetime(2024, 3, 15, 14, 30, 0)
            
            # Should not crash, just skip invalid fields
            result = self.sunrise_sunset._parse_astronomical_data(
                api_data = api_data,
                geographic_location = self.test_location,
                target_date = date(2024, 3, 15)
            )

            # Should have sunset but not sunrise due to parsing error
            self.assertIsNone(result.sunrise)
            self.assertIsInstance(result.sunset, TimeDataPoint)
        return

    def test_get_astronomical_data_caching(self):
        """Test Redis caching behavior - HIGH VALUE for performance optimization."""
        target_date = date(2024, 3, 15)
        cache_key = f'ws:sunrise-sunset-org:astronomical:{self.test_location.latitude:.3f}:{self.test_location.longitude:.3f}:{target_date}'
        
        # Mock cached data
        cached_api_data = {
            "results": {"sunrise": "2024-03-15T12:30:00+00:00"},
            "status": "OK"
        }
        
        # Mock Redis client to return cached data and the API call
        with patch.object(self.sunrise_sunset, '_redis_client') as mock_redis, \
             patch.object(self.sunrise_sunset, '_get_astronomical_api_data_from_api') as mock_api_call:
            
            mock_redis.get.return_value = json.dumps(cached_api_data)
            
            with patch('hi.apps.common.datetimeproxy.now') as mock_now:
                mock_now.return_value = datetime(2024, 3, 15, 14, 30, 0)
                
                result = self.sunrise_sunset.get_astronomical_data(
                    geographic_location = self.test_location,
                    target_date = target_date
                )
            
            # Verify cache was checked and API was not called
            mock_redis.get.assert_called_once_with(cache_key)
            mock_api_call.assert_not_called()
            self.assertIsInstance(result, AstronomicalData)
        return

    @patch('hi.apps.weather.weather_sources.sunrise_sunset_org.SunriseSunsetOrg._get_astronomical_api_data_from_api')
    def test_get_astronomical_data_cache_miss(self, mock_api_call):
        """Test cache miss behavior - HIGH VALUE for cache integration."""
        target_date = date(2024, 3, 15)
        cache_key = f'ws:sunrise-sunset-org:astronomical:{self.test_location.latitude:.3f}:{self.test_location.longitude:.3f}:{target_date}'
        
        # Mock API response
        api_data = {
            "results": {"sunrise": "2024-03-15T12:30:00+00:00"},
            "status": "OK"
        }
        mock_api_call.return_value = api_data
        
        # Mock Redis client - cache miss, then set
        with patch.object(self.sunrise_sunset, '_redis_client') as mock_redis:
            mock_redis.get.return_value = None  # Cache miss
            
            result = self.sunrise_sunset.get_astronomical_data(
                geographic_location = self.test_location,
                target_date = target_date
            )
            
            # Verify cache miss, API call, and cache set
            mock_redis.get.assert_called_once_with(cache_key)
            mock_api_call.assert_called_once()
            mock_redis.set.assert_called_once_with(
                cache_key,
                json.dumps(api_data),
                ex = self.sunrise_sunset.ASTRONOMICAL_DATA_CACHE_EXPIRY_SECS
            )
            self.assertIsInstance(result, AstronomicalData)
        return

    def test_astronomical_data_source_introspection(self):
        """Test data source introspection - HIGH VALUE for attribution logic."""
        # Create a minimal AstronomicalData instance with sunrise-sunset-org source
        source_datetime = datetime(2024, 3, 15, 14, 30, 0)
        station = Station(
            source = self.sunrise_sunset.data_point_source,
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
                value = datetime(2024, 3, 15, 12, 30, 0).time(),
            ),
            sunset = TimeDataPoint(
                station = station,
                source_datetime = source_datetime,
                value = datetime(2024, 3, 16, 1, 15, 0).time(),
            ),
        )

        # Test data_sources property
        data_sources = astronomical_data.data_sources
        self.assertEqual(len(data_sources), 1)
        source = list(data_sources)[0]
        self.assertEqual(source.id, 'sunrise-sunset-org')

        # Test data_source_counts property
        source_counts = astronomical_data.data_source_counts
        self.assertEqual(len(source_counts), 1)
        self.assertEqual(source_counts[source], 2)  # sunrise + sunset
        return

    def test_enum_completeness(self):
        """Test that all documented API status codes are covered - HIGH VALUE for API changes."""
        # According to sunrise-sunset.org API docs, these are all possible status codes
        documented_statuses = {'OK', 'INVALID_REQUEST', 'INVALID_DATE', 'UNKNOWN_ERROR', 'INVALID_TZID'}
        
        # Get all status values from our enum
        enum_statuses = {status.value for status in SunriseSunsetStatus}
        
        # Verify our enum covers all documented statuses
        self.assertEqual(documented_statuses, enum_statuses, 
                        "SunriseSunsetStatus enum should cover all documented API status codes")
        return