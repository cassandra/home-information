import logging
from unittest.mock import Mock, patch

from django.urls import reverse

from hi.apps.weather.weather_manager import WeatherManager
from hi.tests.view_test_base import DualModeViewTestCase

logging.disable(logging.CRITICAL)


class TestCurrentConditionsDetailsView(DualModeViewTestCase):
    """
    Tests for CurrentConditionsDetailsView - demonstrates dual-mode view testing.
    HiModalView handles both sync and async requests:
    - Async: Returns JSON with modal HTML content  
    - Sync: Returns full page with modal auto-displayed
    """

    def test_modal_view_async_request(self):
        """Test that modal view returns JSON with modal content when called with AJAX."""
        url = reverse('weather_current_conditions_details')
        response = self.async_get(url)
        
        self.assertSuccessResponse(response)
        self.assertJsonResponse(response)
        self.assertTemplateRendered(response, 'weather/modals/conditions_details.html')
        
        # Should contain modal HTML content in JSON response
        data = response.json()
        self.assertIn('modal', data)

    def test_modal_view_sync_request(self):
        """Test that modal view returns full page with modal setup when called synchronously."""
        url = reverse('weather_current_conditions_details')
        response = self.client.get(url)  # Regular request without AJAX headers
        
        self.assertSuccessResponse(response)
        self.assertHtmlResponse(response)
        
        # Should render both the base page and the modal template
        self.assertTemplateRendered(response, 'pages/main_default.html')
        self.assertTemplateRendered(response, 'weather/modals/conditions_details.html')

    def test_modal_view_json_structure(self):
        """Test that modal view returns properly structured JSON for async requests."""
        url = reverse('weather_current_conditions_details')
        response = self.async_get(url)
        
        self.assertSuccessResponse(response)
        data = response.json()
        
        # Should have the expected JSON structure for modal responses
        self.assertIn('modal', data)
        self.assertIsInstance(data['modal'], str)
        self.assertTrue(len(data['modal']) > 0)  # Should contain rendered content

    def test_current_conditions_context(self):
        """Test that weather conditions data is passed to template context."""
        url = reverse('weather_current_conditions_details')
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        # Verify that weather_conditions_data is present in context
        self.assertIn('weather_conditions_data', response.context)
        # The actual data structure is tested in WeatherManager tests

    def test_post_not_allowed(self):
        """Test that POST requests are not allowed."""
        url = reverse('weather_current_conditions_details')
        response = self.client.post(url)

        self.assertEqual(response.status_code, 405)


class TestTodaysAstronomicalDetailsView(DualModeViewTestCase):
    """
    Tests for TodaysAstronomicalDetailsView - demonstrates astronomical data testing.
    This view shows astronomical data with source attribution.
    """

    def test_get_astronomical_details_sync(self):
        """Test getting astronomical details with synchronous request."""
        url = reverse('weather_todays_astronomical_details')
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        self.assertHtmlResponse(response)
        self.assertTemplateRendered(response, 'weather/modals/astronomical_details.html')

    def test_get_astronomical_details_async(self):
        """Test getting astronomical details with AJAX request."""
        url = reverse('weather_todays_astronomical_details')
        response = self.async_get(url)

        self.assertSuccessResponse(response)
        self.assertJsonResponse(response)
        
        # HiModalView returns JSON with modal content for AJAX requests
        data = response.json()
        self.assertIn('modal', data)

    def test_astronomical_context_general(self):
        """Test general astronomical context - verifies view loads and returns expected context keys."""
        url = reverse('weather_todays_astronomical_details')
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        # Verify that the view returns the expected context keys
        self.assertIn('todays_astronomical_data', response.context)
        self.assertIn('daily_astronomical_data', response.context)
        self.assertIn('has_sunrise_sunset_attribution', response.context)
        self.assertIn('has_usno_attribution', response.context)
        
        # The attribution flags should be boolean values
        self.assertIsInstance(response.context['has_sunrise_sunset_attribution'], bool)
        self.assertIsInstance(response.context['has_usno_attribution'], bool)

    def test_post_not_allowed(self):
        """Test that POST requests are not allowed."""
        url = reverse('weather_todays_astronomical_details')
        response = self.client.post(url)

        self.assertEqual(response.status_code, 405)


class TestForecastView(DualModeViewTestCase):
    """
    Tests for ForecastView - demonstrates weather forecast testing.
    This view displays hourly and daily weather forecasts.
    """

    @patch.object(WeatherManager, 'get_hourly_forecast')
    @patch.object(WeatherManager, 'get_daily_forecast')
    def test_get_forecast_sync(self, mock_get_daily, mock_get_hourly):
        """Test getting weather forecast with synchronous request."""
        mock_hourly_forecast = Mock()
        mock_hourly_forecast.data_list = ['hourly1', 'hourly2']
        mock_daily_forecast = Mock()
        mock_daily_forecast.data_list = ['daily1', 'daily2']
        
        mock_get_hourly.return_value = mock_hourly_forecast
        mock_get_daily.return_value = mock_daily_forecast

        url = reverse('weather_forecast')
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        self.assertHtmlResponse(response)
        self.assertTemplateRendered(response, 'weather/modals/forecast.html')

    @patch.object(WeatherManager, 'get_hourly_forecast')
    @patch.object(WeatherManager, 'get_daily_forecast')
    def test_get_forecast_async(self, mock_get_daily, mock_get_hourly):
        """Test getting weather forecast with AJAX request."""
        mock_hourly_forecast = Mock()
        mock_hourly_forecast.data_list = []
        mock_daily_forecast = Mock()
        mock_daily_forecast.data_list = []
        
        mock_get_hourly.return_value = mock_hourly_forecast
        mock_get_daily.return_value = mock_daily_forecast

        url = reverse('weather_forecast')
        response = self.async_get(url)

        self.assertSuccessResponse(response)
        self.assertJsonResponse(response)
        
        # HiModalView returns JSON with modal content for AJAX requests
        data = response.json()
        self.assertIn('modal', data)

    @patch.object(WeatherManager, 'get_hourly_forecast')
    @patch.object(WeatherManager, 'get_daily_forecast')
    def test_forecast_context_data(self, mock_get_daily, mock_get_hourly):
        """Test that forecast data is passed to template context."""
        mock_hourly_forecast = Mock()
        mock_hourly_forecast.data_list = ['hourly_item1', 'hourly_item2']
        mock_daily_forecast = Mock()
        mock_daily_forecast.data_list = ['daily_item1', 'daily_item2']
        
        mock_get_hourly.return_value = mock_hourly_forecast
        mock_get_daily.return_value = mock_daily_forecast

        url = reverse('weather_forecast')
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        self.assertEqual(response.context['interval_hourly_forecast_list'], mock_hourly_forecast.data_list)
        self.assertEqual(response.context['interval_daily_forecast_list'], mock_daily_forecast.data_list)
        
        mock_get_hourly.assert_called_once()
        mock_get_daily.assert_called_once()

    @patch.object(WeatherManager, 'get_hourly_forecast')
    @patch.object(WeatherManager, 'get_daily_forecast')
    def test_forecast_empty_data(self, mock_get_daily, mock_get_hourly):
        """Test forecast view with empty data lists."""
        mock_hourly_forecast = Mock()
        mock_hourly_forecast.data_list = []
        mock_daily_forecast = Mock()
        mock_daily_forecast.data_list = []
        
        mock_get_hourly.return_value = mock_hourly_forecast
        mock_get_daily.return_value = mock_daily_forecast

        url = reverse('weather_forecast')
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        self.assertEqual(len(response.context['interval_hourly_forecast_list']), 0)
        self.assertEqual(len(response.context['interval_daily_forecast_list']), 0)

    def test_post_not_allowed(self):
        """Test that POST requests are not allowed."""
        url = reverse('weather_forecast')
        response = self.client.post(url)

        self.assertEqual(response.status_code, 405)


class TestRadarView(DualModeViewTestCase):
    """
    Tests for RadarView - demonstrates simple modal view testing.
    This view displays weather radar information.
    """

    def test_get_radar_sync(self):
        """Test getting weather radar with synchronous request."""
        url = reverse('weather_radar')
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        self.assertHtmlResponse(response)
        self.assertTemplateRendered(response, 'weather/modals/radar.html')

    def test_get_radar_async(self):
        """Test getting weather radar with AJAX request."""
        url = reverse('weather_radar')
        response = self.async_get(url)

        self.assertSuccessResponse(response)
        self.assertJsonResponse(response)
        
        # HiModalView returns JSON with modal content for AJAX requests
        data = response.json()
        self.assertIn('modal', data)

    def test_radar_context_empty(self):
        """Test that radar view has empty context."""
        url = reverse('weather_radar')
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        # Radar view has minimal context - just checks that it renders correctly

    def test_post_not_allowed(self):
        """Test that POST requests are not allowed."""
        url = reverse('weather_radar')
        response = self.client.post(url)

        self.assertEqual(response.status_code, 405)


class TestHistoryView(DualModeViewTestCase):
    """
    Tests for HistoryView - demonstrates weather history testing.
    This view displays historical weather data.
    """

    @patch.object(WeatherManager, 'get_daily_history')
    def test_get_history_sync(self, mock_get_history):
        """Test getting weather history with synchronous request."""
        mock_daily_history = Mock()
        mock_daily_history.data_list = ['history1', 'history2', 'history3']
        mock_get_history.return_value = mock_daily_history

        url = reverse('weather_history')
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        self.assertHtmlResponse(response)
        self.assertTemplateRendered(response, 'weather/modals/history.html')

    @patch.object(WeatherManager, 'get_daily_history')
    def test_get_history_async(self, mock_get_history):
        """Test getting weather history with AJAX request."""
        mock_daily_history = Mock()
        mock_daily_history.data_list = []
        mock_get_history.return_value = mock_daily_history

        url = reverse('weather_history')
        response = self.async_get(url)

        self.assertSuccessResponse(response)
        self.assertJsonResponse(response)
        
        # HiModalView returns JSON with modal content for AJAX requests
        data = response.json()
        self.assertIn('modal', data)

    @patch.object(WeatherManager, 'get_daily_history')
    def test_history_context_data(self, mock_get_history):
        """Test that history data is passed to template context."""
        mock_daily_history = Mock()
        mock_daily_history.data_list = ['day1_data', 'day2_data', 'day3_data']
        mock_get_history.return_value = mock_daily_history

        url = reverse('weather_history')
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        self.assertEqual(response.context['interval_daily_history_list'], mock_daily_history.data_list)
        mock_get_history.assert_called_once()

    @patch.object(WeatherManager, 'get_daily_history')
    def test_history_empty_data(self, mock_get_history):
        """Test history view with empty data list."""
        mock_daily_history = Mock()
        mock_daily_history.data_list = []
        mock_get_history.return_value = mock_daily_history

        url = reverse('weather_history')
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        self.assertEqual(len(response.context['interval_daily_history_list']), 0)

    def test_post_not_allowed(self):
        """Test that POST requests are not allowed."""
        url = reverse('weather_history')
        response = self.client.post(url)

        self.assertEqual(response.status_code, 405)
