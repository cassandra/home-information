import json
import logging
from datetime import datetime, date
from unittest.mock import Mock, patch
import pytz

from hi.apps.weather.weather_sources.sunrise_sunset_org import (
    SunriseSunsetOrg,
    SunriseSunsetStatus,
)
from hi.apps.weather.transient_models import (
    AstronomicalData,
    IntervalAstronomical,
    TimeDataPoint,
    TimeInterval,
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

    @patch('hi.apps.weather.weather_sources.sunrise_sunset_org.SunriseSunsetOrg.get_astronomical_data')
    @patch('hi.apps.common.datetimeproxy.now')
    def test_get_astronomical_data_list_success(self, mock_now, mock_get_astronomical_data):
        """Test successful multi-day astronomical data fetching - HIGH VALUE for new feature."""
        # Mock current time
        mock_today = datetime(2024, 3, 15, 10, 0, 0)
        mock_now.return_value = mock_today
        
        # Mock timezone from superclass
        with patch.object(type(self.sunrise_sunset), 'tz_name',
                          new_callable=lambda: property(lambda self: 'America/Chicago')):
            # Mock successful astronomical data for each day
            mock_astronomical_data = AstronomicalData(
                sunrise = TimeDataPoint(
                    station = Station(
                        source = self.sunrise_sunset.data_point_source,
                        station_id = 'test-station',
                        name = 'Test Station',
                        geo_location = self.test_location,
                    ),
                    source_datetime = mock_today,
                    value = datetime(2024, 3, 15, 12, 30, 0).time(),
                ),
            )
            mock_get_astronomical_data.return_value = mock_astronomical_data
            
            # Test with 3 days instead of default 10 for faster test
            result = self.sunrise_sunset.get_astronomical_data_list(
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
            
            # Verify intervals are properly aligned to local day boundaries
            chicago_tz = pytz.timezone('America/Chicago')
            first_interval = result[0].interval
            
            # First day should start at local midnight
            expected_start_local = chicago_tz.localize(datetime.combine(mock_today.date(),
                                                                        datetime.min.time()))
            expected_start_utc = expected_start_local.astimezone(pytz.UTC)
            self.assertEqual(first_interval.start, expected_start_utc)
        return

    @patch('hi.apps.weather.weather_sources.sunrise_sunset_org.SunriseSunsetOrg.get_astronomical_data')
    @patch('hi.apps.common.datetimeproxy.now')
    def test_get_astronomical_data_list_partial_failures(self, mock_now, mock_get_astronomical_data):
        """Test multi-day fetching with some day failures - HIGH VALUE for error resilience."""
        # Mock current time
        mock_today = datetime(2024, 3, 15, 10, 0, 0)
        mock_now.return_value = mock_today
        
        # Mock timezone from superclass
        with patch.object(type(self.sunrise_sunset), 'tz_name',
                          new_callable=lambda: property(lambda self: 'America/Chicago')):
            # Mock some successes and some failures
            def side_effect(*args, **kwargs):
                target_date = kwargs.get('target_date')
                if target_date == date(2024, 3, 16):  # Second day fails
                    raise Exception("API error for this date")
                return AstronomicalData()  # Other days succeed
                
            mock_get_astronomical_data.side_effect = side_effect
            
            # Test with 3 days
            result = self.sunrise_sunset.get_astronomical_data_list(
                geographic_location = self.test_location,
                days_count = 3
            )
            
            # Should only return successful days
            self.assertIsInstance(result, list)
            self.assertEqual(len(result), 2)  # Only days 1 and 3 succeeded
            
            # Verify get_astronomical_data was called for each day attempt
            self.assertEqual(mock_get_astronomical_data.call_count, 3)
        return

    @patch('hi.apps.weather.weather_sources.sunrise_sunset_org.SunriseSunsetOrg.get_astronomical_data')
    @patch('hi.apps.common.datetimeproxy.now')
    def test_get_astronomical_data_list_timezone_boundaries(self, mock_now, mock_get_astronomical_data):
        """Test timezone-aware interval boundaries - HIGH VALUE for timezone correctness."""
        # Mock current time
        mock_today = datetime(2024, 3, 15, 10, 0, 0)
        mock_now.return_value = mock_today
        
        # Test with different timezones
        timezone_tests = ['America/Chicago', 'America/New_York', 'Europe/London', 'Asia/Tokyo']
        
        for tz_name in timezone_tests:
            with patch.object(type(self.sunrise_sunset), 'tz_name',
                              new_callable=lambda tz=tz_name: property(lambda self: tz)):
                mock_get_astronomical_data.return_value = AstronomicalData()
                
                result = self.sunrise_sunset.get_astronomical_data_list(
                    geographic_location = self.test_location,
                    days_count = 1
                )
                
                # Verify interval boundaries align with local timezone
                local_tz = pytz.timezone(tz_name)
                interval = result[0].interval
                
                # Convert back to local timezone to verify boundaries
                local_start = interval.start.astimezone(local_tz)
                local_end = interval.end.astimezone(local_tz)
                
                # Should be midnight to 23:59:59.999999 in local time
                self.assertEqual(local_start.time(), datetime.min.time())
                self.assertEqual(local_end.time(), datetime.max.time())
                self.assertEqual(local_start.date(), mock_today.date())
                self.assertEqual(local_end.date(), mock_today.date())
        return

    @patch('hi.apps.weather.weather_sources.sunrise_sunset_org.SunriseSunsetOrg.get_astronomical_data')
    @patch('hi.apps.common.datetimeproxy.now')
    def test_get_astronomical_data_list_empty_data_handling(self, mock_now, mock_get_astronomical_data):
        """Test handling when get_astronomical_data returns None - HIGH VALUE for robustness."""
        # Mock current time
        mock_today = datetime(2024, 3, 15, 10, 0, 0)
        mock_now.return_value = mock_today
        
        with patch.object(type(self.sunrise_sunset), 'tz_name',
                          new_callable=lambda: property(lambda self: 'America/Chicago')):
            # Mock returning None (no data available)
            mock_get_astronomical_data.return_value = None
            
            result = self.sunrise_sunset.get_astronomical_data_list(
                geographic_location = self.test_location,
                days_count = 2
            )
            
            # Should return empty list when no data available
            self.assertIsInstance(result, list)
            self.assertEqual(len(result), 0)
        return

    @patch('hi.apps.weather.weather_sources.sunrise_sunset_org.SunriseSunsetOrg.get_astronomical_data_list')
    @patch('hi.apps.weather.weather_sources.sunrise_sunset_org.SunriseSunsetOrg.get_astronomical_data')
    async def test_get_data_calls_multi_day_method(self,
                                                   mock_get_astronomical_data,
                                                   mock_get_astronomical_data_list):
        """Test that get_data calls the new multi-day method - HIGH VALUE for integration."""
        # Mock weather manager
        mock_weather_manager = Mock()
        mock_weather_manager.update_astronomical_data = Mock()
        mock_weather_manager.update_todays_astronomical_data = Mock()
        
        with patch.object(type(self.sunrise_sunset), 'geographic_location',
                          new_callable=lambda: property(lambda instance: self.test_location)), \
             patch.object(self.sunrise_sunset, 'weather_manager_async', return_value=mock_weather_manager):
            
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
            await self.sunrise_sunset.get_data()
            
            # Verify multi-day method was called
            mock_get_astronomical_data_list.assert_called_once_with(
                geographic_location = self.test_location,
                days_count = 10
            )
            
            # Verify weather manager methods were called
            mock_weather_manager.update_astronomical_data.assert_called_once_with(
                data_point_source = self.sunrise_sunset.data_point_source,
                astronomical_data_list = [mock_interval_data]
            )
            
            # Verify today's data is also updated for backwards compatibility
            mock_get_astronomical_data.assert_called_once_with(
                geographic_location = self.test_location
            )
            mock_weather_manager.update_todays_astronomical_data.assert_called_once()
        return

    @patch('hi.apps.weather.weather_sources.sunrise_sunset_org.SunriseSunsetOrg.get_astronomical_data_list')
    @patch('hi.apps.weather.weather_sources.sunrise_sunset_org.SunriseSunsetOrg.get_astronomical_data')
    async def test_get_data_handles_multi_day_failure_gracefully(self,
                                                                 mock_get_astronomical_data,
                                                                 mock_get_astronomical_data_list):
        """Test that failures in multi-day fetch don't affect today's data - HIGH VALUE for isolation."""
        # Mock weather manager
        mock_weather_manager = Mock()
        mock_weather_manager.update_astronomical_data = Mock()
        mock_weather_manager.update_todays_astronomical_data = Mock()
        
        with patch.object(type(self.sunrise_sunset), 'geographic_location',
                          new_callable=lambda: property(lambda instance: self.test_location)), \
             patch.object(self.sunrise_sunset, 'weather_manager_async', return_value=mock_weather_manager):
            
            # Mock multi-day failure but today's data succeeds
            mock_get_astronomical_data_list.side_effect = Exception("Multi-day API error")
            mock_get_astronomical_data.return_value = AstronomicalData()
            
            # Should not raise exception
            await self.sunrise_sunset.get_data()
            
            # Multi-day method should have been attempted
            mock_get_astronomical_data_list.assert_called_once()
            
            # update_astronomical_data should not have been called due to exception
            mock_weather_manager.update_astronomical_data.assert_not_called()
            
            # Today's data should still be updated
            mock_get_astronomical_data.assert_called_once()
            mock_weather_manager.update_todays_astronomical_data.assert_called_once()
        return

    @patch('hi.apps.weather.weather_sources.sunrise_sunset_org.SunriseSunsetOrg.get_astronomical_data_list')
    @patch('hi.apps.weather.weather_sources.sunrise_sunset_org.SunriseSunsetOrg.get_astronomical_data')
    async def test_get_data_handles_todays_data_failure_gracefully(self,
                                                                   mock_get_astronomical_data,
                                                                   mock_get_astronomical_data_list):
        """Test that failures in today's data don't affect multi-day fetch - HIGH VALUE for isolation."""
        # Mock weather manager
        mock_weather_manager = Mock()
        mock_weather_manager.update_astronomical_data = Mock()
        mock_weather_manager.update_todays_astronomical_data = Mock()
        
        with patch.object(type(self.sunrise_sunset), 'geographic_location',
                          new_callable=lambda: property(lambda instance: self.test_location)), \
             patch.object(self.sunrise_sunset, 'weather_manager_async', return_value=mock_weather_manager):
            
            # Mock multi-day success but today's data fails
            mock_interval_data = IntervalAstronomical(
                interval = TimeInterval(
                    start = datetime(2024, 3, 15, 6, 0, 0, tzinfo=pytz.UTC),
                    end = datetime(2024, 3, 15, 23, 59, 59, tzinfo=pytz.UTC)
                ),
                data = AstronomicalData()
            )
            mock_get_astronomical_data_list.return_value = [mock_interval_data]
            mock_get_astronomical_data.side_effect = Exception("Today's data API error")
            
            # Should not raise exception
            await self.sunrise_sunset.get_data()
            
            # Multi-day method should have succeeded
            mock_get_astronomical_data_list.assert_called_once()
            mock_weather_manager.update_astronomical_data.assert_called_once()
            
            # Today's data method should have been attempted
            mock_get_astronomical_data.assert_called_once()
            
            # update_todays_astronomical_data should not have been called due to exception
            mock_weather_manager.update_todays_astronomical_data.assert_not_called()
        return
