import logging
import unittest
from unittest.mock import Mock, patch

from hi.apps.weather.weather_sources.openmeteo import OpenMeteo
from hi.apps.weather.weather_sources.openmeteo_converters import OpenMeteoConverters
from hi.apps.weather.transient_models import (
    WeatherConditionsData,
    WeatherForecastData,
    WeatherHistoryData,
    IntervalWeatherForecast,
    IntervalWeatherHistory,
)
from hi.transient_models import GeographicLocation
from hi.units import UnitQuantity

from hi.testing.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestOpenMeteo(BaseTestCase):
    """Test the OpenMeteo weather data source."""

    def setUp(self):
        """Set up test data."""
        self.openmeteo = OpenMeteo()
        self.test_location = GeographicLocation(
            latitude = 30.2711286,
            longitude = -97.7436995,
            elevation = UnitQuantity(167.0, 'm')
        )
        return

    def test_openmeteo_initialization(self):
        """Test OpenMeteo initialization."""
        self.assertEqual(self.openmeteo.id, 'openmeteo')
        self.assertEqual(self.openmeteo.label, 'Open-Meteo')
        self.assertEqual(self.openmeteo.priority, 2)
        return

    @patch('hi.apps.weather.weather_sources.openmeteo.requests.get')
    def test_current_weather_api_integration(self, mock_get):
        """Test that OpenMeteo API integration works correctly end-to-end."""
        # Mock realistic OpenMeteo API response
        mock_response_data = {
            "current_weather": {
                "interval": 900,
                "is_day": 1,
                "temperature": 25.5,
                "time": "2024-01-01T12:00",
                "weathercode": 0,
                "winddirection": 180,
                "windspeed": 10.5
            },
            "current_weather_units": {
                "interval": "seconds",
                "is_day": "",
                "temperature": "°C",
                "time": "iso8601",
                "weathercode": "wmo code",
                "winddirection": "°",
                "windspeed": "km/h"
            },
            "elevation": 167.0,
            "hourly": {
                "relativehumidity_2m": [70],
                "time": ["2024-01-01T12:00"]
            },
            "hourly_units": {
                "relativehumidity_2m": "%"
            },
            "latitude": 30.269146,
            "longitude": -97.75338
        }

        mock_response = Mock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        # Test the private method since public method may use caching
        result = self.openmeteo._get_current_weather_data_from_api(
            geographic_location=self.test_location
        )

        # Test actual API integration behavior - proper response handling
        self.assertIsInstance(result, dict)
        self.assertIn('current_weather', result)
        self.assertIn('current_weather_units', result)
        
        # Test data integrity - verify key weather data is present
        current_weather = result['current_weather']
        self.assertEqual(current_weather['temperature'], 25.5)
        self.assertEqual(current_weather['weathercode'], 0)
        self.assertEqual(current_weather['windspeed'], 10.5)
        self.assertEqual(current_weather['winddirection'], 180)
        self.assertEqual(current_weather['is_day'], 1)
        
        # Verify units are properly included
        units = result['current_weather_units']
        self.assertEqual(units['temperature'], '°C')
        self.assertEqual(units['windspeed'], 'km/h')
        
        # Verify HTTP call was made with reasonable parameters
        mock_get.assert_called_once()
        call_url = mock_get.call_args[0][0]
        self.assertIn('api.open-meteo.com', call_url)
        
        return
    
    @patch('hi.apps.weather.weather_sources.openmeteo.OpenMeteo._get_hourly_forecast_data')
    def test_get_forecast_hourly_returns_interval_list(self, mock_get_hourly_data):
        """Test that get_forecast_hourly returns properly parsed forecast intervals."""
        # Mock OpenMeteo API response for hourly forecast
        mock_response_data = {
            "hourly": {
                "time": ["2024-01-01T12:00", "2024-01-01T13:00", "2024-01-01T14:00"],
                "temperature_2m": [25.5, 26.0, 26.5],
                "relativehumidity_2m": [65, 67, 70],
                "weathercode": [0, 1, 2],
                "is_day": [1, 1, 1],
                "windspeed_10m": [10.5, 11.0, 11.5],
                "winddirection_10m": [180, 185, 190]
            },
            "hourly_units": {
                "time": "iso8601",
                "temperature_2m": "°C",
                "relativehumidity_2m": "%",
                "weathercode": "wmo code",
                "is_day": "",
                "windspeed_10m": "km/h",
                "winddirection_10m": "°"
            },
            "latitude": 30.269146,
            "longitude": -97.75338
        }

        # Mock the private data method directly
        mock_get_hourly_data.return_value = mock_response_data

        # Test the public interface
        result = self.openmeteo.get_forecast_hourly(self.test_location)

        # Test the interface contract - verify it returns list of IntervalWeatherForecast
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 3)
        
        # Test first forecast interval
        first_forecast = result[0]
        self.assertIsInstance(first_forecast, IntervalWeatherForecast)
        
        # Verify interval structure
        self.assertIsNotNone(first_forecast.interval)
        self.assertIsNotNone(first_forecast.data)
        
        # Test that weather data is properly parsed
        weather_data = first_forecast.data
        self.assertIsInstance(weather_data, WeatherForecastData)
        
        # Verify temperature conversion and units
        self.assertIsNotNone(weather_data.temperature)
        self.assertEqual(weather_data.temperature.quantity_ave.magnitude, 25.5)
        self.assertEqual(str(weather_data.temperature.quantity_ave.units), 'degree_Celsius')
        
        # Verify humidity data
        self.assertIsNotNone(weather_data.relative_humidity)
        self.assertEqual(weather_data.relative_humidity.quantity_ave.magnitude, 65)
        
        # Verify description conversion from weather code
        self.assertIsNotNone(weather_data.description_short)
        self.assertEqual(weather_data.description_short.value, "Clear sky")
        
        # Note: is_daytime is not included in hourly forecast data from OpenMeteo
        # This field is only available in current weather conditions
        
        mock_get_hourly_data.assert_called_once()
        return
    
    @patch('hi.apps.weather.weather_sources.openmeteo.OpenMeteo._get_current_weather_data')
    def test_openmeteo_data_transformation_integration(self, mock_get_current_data):
        """Test that OpenMeteo properly transforms API data through the entire pipeline."""
        # Mock realistic OpenMeteo API response
        mock_response_data = {
            "current_weather": {
                "temperature": 22.3,
                "time": "2024-01-01T14:30",
                "weathercode": 3,  # Overcast
                "winddirection": 225,
                "windspeed": 15.2,
                "is_day": 0
            },
            "current_weather_units": {
                "temperature": "°C",
                "windspeed": "km/h",
                "winddirection": "°"
            },
            "hourly": {
                "relativehumidity_2m": [78],
                "time": ["2024-01-01T14:00"]
            },
            "hourly_units": {
                "relativehumidity_2m": "%"
            },
            "elevation": 167.0,
            "latitude": 30.269146,
            "longitude": -97.75338
        }

        # Mock the private data method directly
        mock_get_current_data.return_value = mock_response_data

        # Test complete data transformation pipeline
        result = self.openmeteo.get_current_conditions(self.test_location)

        # Verify complex data transformations work correctly
        
        # Test weather code to description conversion (weathercode 3 = Overcast)
        self.assertEqual(result.description_short.value, "Overcast")
        
        # Test unit conversions (OpenMeteo returns km/h, we should handle properly)
        self.assertAlmostEqual(result.windspeed.quantity.magnitude, 15.2, places=1)
        
        # Test is_day boolean conversion (0 = night)
        self.assertFalse(result.is_daytime.value)
        
        # Test wind direction handling
        self.assertEqual(result.wind_direction.quantity.magnitude, 225)
        
        # Test temperature with realistic value
        self.assertAlmostEqual(result.temperature.quantity.magnitude, 22.3, places=1)
        
        # Test that station information is properly set
        self.assertIsNotNone(result.temperature.station)
        self.assertEqual(result.temperature.station.geo_location.latitude, 30.269146)
        self.assertEqual(result.temperature.station.geo_location.longitude, -97.75338)
        
        return
    
    @patch('hi.apps.weather.weather_sources.openmeteo.OpenMeteo._get_current_weather_data')
    def test_openmeteo_error_handling_behavior(self, mock_get_current_data):
        """Test that OpenMeteo properly handles API errors and edge cases."""
        # Test case where API returns None (indicating error)
        mock_get_current_data.return_value = None
        
        # The method should handle None input by raising an exception or failing gracefully
        with self.assertRaises(Exception):
            self.openmeteo.get_current_conditions(self.test_location)
            
        return

    def test_parse_current_weather_data(self):
        """Test parsing current weather data."""
        mock_current_data = {
            "current_weather": {
                "temperature": 25.5,
                "time": "2024-01-01T12:00",
                "weathercode": 0,
                "winddirection": 180,
                "windspeed": 10.5,
                "is_day": 1
            },
            "current_weather_units": {
                "temperature": "°C",
                "windspeed": "km/h"
            },
            "elevation": 167.0,
            "hourly": {
                "relativehumidity_2m": [70],
                "time": ["2024-01-01T12:00"]
            },
            "hourly_units": {
                "relativehumidity_2m": "%"
            },
            "latitude": 30.269146,
            "longitude": -97.75338
        }

        result = self.openmeteo._parse_current_weather_data(
            current_data = mock_current_data,
            geographic_location = self.test_location
        )

        self.assertIsInstance(result, WeatherConditionsData)
        self.assertIsNotNone(result.temperature)
        self.assertEqual(result.temperature.quantity_ave.magnitude, 25.5)
        self.assertEqual(result.temperature.quantity_ave.units, 'degree_Celsius')
        
        self.assertIsNotNone(result.windspeed)
        self.assertEqual(result.windspeed.quantity_ave.magnitude, 10.5)
        
        self.assertIsNotNone(result.wind_direction)
        self.assertEqual(result.wind_direction.quantity_ave.magnitude, 180)
        
        self.assertIsNotNone(result.description_short)
        self.assertEqual(result.description_short.value, "Clear sky")
        
        self.assertIsNotNone(result.is_daytime)
        self.assertTrue(result.is_daytime.value)
        return

    def test_parse_hourly_forecast_data(self):
        """Test parsing hourly forecast data."""
        mock_forecast_data = {
            "hourly": {
                "time": ["2024-01-01T12:00", "2024-01-01T13:00"],
                "temperature_2m": [25.5, 26.0],
                "relativehumidity_2m": [70, 68],
                "windspeed_10m": [10.5, 11.0],
                "winddirection_10m": [180, 185],
                "weathercode": [0, 1]
            },
            "hourly_units": {
                "temperature_2m": "°C",
                "windspeed_10m": "km/h"
            },
            "elevation": 167.0,
            "latitude": 30.269146,
            "longitude": -97.75338
        }

        result = self.openmeteo._parse_hourly_forecast_data(
            forecast_data = mock_forecast_data,
            geographic_location = self.test_location
        )

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        
        first_forecast = result[0]
        self.assertIsInstance(first_forecast, IntervalWeatherForecast)
        self.assertIsNotNone(first_forecast.interval)
        self.assertIsNotNone(first_forecast.data)
        self.assertIsInstance(first_forecast.data, WeatherForecastData)
        self.assertIsNotNone(first_forecast.data.temperature)
        self.assertEqual(first_forecast.data.temperature.quantity_ave.magnitude, 25.5)
        self.assertIsNotNone(first_forecast.data.relative_humidity)
        self.assertEqual(first_forecast.data.relative_humidity.quantity_ave.magnitude, 70)
        return

    def test_parse_daily_forecast_data(self):
        """Test parsing daily forecast data."""
        mock_forecast_data = {
            "daily": {
                "time": ["2024-01-01", "2024-01-02"],
                "temperature_2m_max": [28.0, 29.0],
                "temperature_2m_min": [18.0, 19.0],
                "precipitation_sum": [0.0, 2.5],
                "weathercode": [0, 61]
            },
            "daily_units": {
                "temperature_2m_max": "°C",
                "temperature_2m_min": "°C",
                "precipitation_sum": "mm"
            },
            "elevation": 167.0,
            "latitude": 30.269146,
            "longitude": -97.75338
        }

        result = self.openmeteo._parse_daily_forecast_data(
            forecast_data = mock_forecast_data,
            geographic_location = self.test_location
        )

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        
        first_forecast = result[0]
        self.assertIsInstance(first_forecast, IntervalWeatherForecast)
        self.assertIsNotNone(first_forecast.interval)
        self.assertIsNotNone(first_forecast.data)
        self.assertIsInstance(first_forecast.data, WeatherForecastData)
        self.assertIsNotNone(first_forecast.data.temperature)
        self.assertEqual(first_forecast.data.temperature.quantity_max.magnitude, 28.0)
        self.assertEqual(first_forecast.data.temperature.quantity_min.magnitude, 18.0)
        self.assertIsNotNone(first_forecast.data.description_short)
        self.assertEqual(first_forecast.data.description_short.value, "Clear sky")
        return

    def test_parse_historical_weather_data(self):
        """Test parsing historical weather data."""
        mock_historical_data = {
            "daily": {
                "time": ["2024-01-01", "2024-01-02"],
                "temperature_2m_max": [28.0, 29.0],
                "temperature_2m_min": [18.0, 19.0],
                "precipitation_sum": [0.0, 2.5],
                "weathercode": [0, 61]
            },
            "daily_units": {
                "temperature_2m_max": "°C",
                "temperature_2m_min": "°C",
                "precipitation_sum": "mm"
            },
            "elevation": 167.0,
            "latitude": 30.269146,
            "longitude": -97.75338
        }

        result = self.openmeteo._parse_historical_weather_data(
            historical_data = mock_historical_data,
            geographic_location = self.test_location
        )

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        
        first_interval_history = result[0]
        self.assertIsInstance(first_interval_history, IntervalWeatherHistory)
        
        # Test the interval part
        self.assertIsNotNone(first_interval_history.interval)
        
        # Test the data part
        first_history = first_interval_history.data
        self.assertIsInstance(first_history, WeatherHistoryData)
        self.assertIsNotNone(first_history.temperature)
        # The temperature should have min/max values from the daily data
        self.assertEqual(first_history.temperature.quantity_max.magnitude, 28.0)
        self.assertEqual(first_history.temperature.quantity_min.magnitude, 18.0)
        return


class TestOpenMeteoConverters(BaseTestCase):
    """Test the OpenMeteo converters."""

    def test_weather_code_to_description(self):
        """Test weather code to description conversion."""
        # Test known weather codes
        self.assertEqual(OpenMeteoConverters.weather_code_to_description(0), "Clear sky")
        self.assertEqual(OpenMeteoConverters.weather_code_to_description(3), "Overcast")
        self.assertEqual(OpenMeteoConverters.weather_code_to_description(61), "Slight rain")
        self.assertEqual(OpenMeteoConverters.weather_code_to_description(95), "Thunderstorm")
        
        # Test unknown weather code
        with self.assertRaises(ValueError):
            OpenMeteoConverters.weather_code_to_description(999)
        return

    def test_normalize_temperature_unit(self):
        """Test temperature unit normalization."""
        self.assertEqual(OpenMeteoConverters.normalize_temperature_unit('°C'), 'degC')
        self.assertEqual(OpenMeteoConverters.normalize_temperature_unit('°F'), 'degF')
        self.assertEqual(OpenMeteoConverters.normalize_temperature_unit('K'), 'K')
        self.assertEqual(OpenMeteoConverters.normalize_temperature_unit('unknown'), 'degC')
        return

    def test_normalize_wind_unit(self):
        """Test wind unit normalization."""
        self.assertEqual(OpenMeteoConverters.normalize_wind_unit('km/h'), 'km/h')
        self.assertEqual(OpenMeteoConverters.normalize_wind_unit('m/s'), 'm/s')
        self.assertEqual(OpenMeteoConverters.normalize_wind_unit('mph'), 'mph')
        self.assertEqual(OpenMeteoConverters.normalize_wind_unit('kn'), 'knot')
        self.assertEqual(OpenMeteoConverters.normalize_wind_unit('unknown'), 'km/h')
        return

    def test_normalize_precipitation_unit(self):
        """Test precipitation unit normalization."""
        self.assertEqual(OpenMeteoConverters.normalize_precipitation_unit('mm'), 'mm')
        self.assertEqual(OpenMeteoConverters.normalize_precipitation_unit('inch'), 'inch')
        self.assertEqual(OpenMeteoConverters.normalize_precipitation_unit('unknown'), 'mm')
        return

    def test_normalize_pressure_unit(self):
        """Test pressure unit normalization."""
        self.assertEqual(OpenMeteoConverters.normalize_pressure_unit('hPa'), 'hPa')
        self.assertEqual(OpenMeteoConverters.normalize_pressure_unit('Pa'), 'Pa')
        self.assertEqual(OpenMeteoConverters.normalize_pressure_unit('inHg'), 'inHg')
        self.assertEqual(OpenMeteoConverters.normalize_pressure_unit('unknown'), 'hPa')
        return

    def test_weather_code_checks(self):
        """Test weather code classification methods."""
        # Test precipitation codes
        self.assertTrue(OpenMeteoConverters.is_weather_code_precipitation(61))  # Rain
        self.assertTrue(OpenMeteoConverters.is_weather_code_precipitation(71))  # Snow
        self.assertTrue(OpenMeteoConverters.is_weather_code_precipitation(95))  # Thunderstorm
        self.assertFalse(OpenMeteoConverters.is_weather_code_precipitation(0))  # Clear
        
        # Test clear codes
        self.assertTrue(OpenMeteoConverters.is_weather_code_clear(0))    # Clear sky
        self.assertTrue(OpenMeteoConverters.is_weather_code_clear(1))    # Mainly clear
        self.assertFalse(OpenMeteoConverters.is_weather_code_clear(61))  # Rain
        
        # Test severity
        self.assertEqual(OpenMeteoConverters.get_weather_code_severity(0), 'clear')
        self.assertEqual(OpenMeteoConverters.get_weather_code_severity(61), 'light')
        self.assertEqual(OpenMeteoConverters.get_weather_code_severity(63), 'moderate')
        self.assertEqual(OpenMeteoConverters.get_weather_code_severity(65), 'heavy')
        self.assertEqual(OpenMeteoConverters.get_weather_code_severity(95), 'severe')
        return


if __name__ == '__main__':
    unittest.main()
