import logging

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from hi.apps.monitor.views import MonitorHealthStatusView
from hi.apps.monitor.enums import MonitorHealthStatusType, ApiSourceHealthStatusType

logger = logging.getLogger(__name__)


class MonitorHealthStatusViewTestCase(TestCase):
    """Test cases for MonitorHealthStatusView."""

    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )

    def test_monitor_health_status_view_get(self):
        """Test GET request to monitor health status view."""
        self.client.force_login(self.user)

        url = reverse('monitor:health_status', kwargs={'monitor_id': 'zoneminder'})
        response = self.client.get(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ZoneMinder Integration Health Status')
        self.assertContains(response, 'Monitor Status:')
        self.assertContains(response, 'API Sources')
        self.assertContains(response, 'ZoneMinder API')

    def test_monitor_health_status_view_weather_monitor(self):
        """Test weather monitor with multiple API sources."""
        self.client.force_login(self.user)

        url = reverse('monitor:health_status', kwargs={'monitor_id': 'weather'})
        response = self.client.get(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Weather Updates Monitor Health Status')
        self.assertContains(response, 'National Weather Service')
        self.assertContains(response, 'OpenWeatherMap API')
        self.assertContains(response, 'WeatherAPI.com')
        self.assertContains(response, 'Weather Underground')

    def test_monitor_health_status_view_error_monitor(self):
        """Test monitor with error status and no API sources."""
        self.client.force_login(self.user)

        url = reverse('monitor:health_status', kwargs={'monitor_id': 'alert'})
        response = self.client.get(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Alert Processing Monitor Health Status')
        self.assertContains(response, 'Monitor has stopped responding')
        # Should not contain API Sources section for this monitor
        self.assertNotContains(response, 'API Sources')

    def test_monitor_health_status_view_unknown_monitor(self):
        """Test fallback for unknown monitor IDs."""
        self.client.force_login(self.user)

        url = reverse('monitor:health_status', kwargs={'monitor_id': 'unknown'})
        response = self.client.get(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Monitor unknown Health Status')
        self.assertContains(response, 'Healthy')

    def test_monitor_health_status_sync_request(self):
        """Test non-AJAX request renders as full page."""
        self.client.force_login(self.user)

        url = reverse('monitor:health_status', kwargs={'monitor_id': 'zoneminder'})
        response = self.client.get(url)  # No AJAX header

        self.assertEqual(response.status_code, 200)
        # Should render full page with modal content embedded
        self.assertContains(response, 'antinode-initial-modal')
        self.assertContains(response, 'ZoneMinder Integration Health Status')

    def test_sample_health_status_data_structure(self):
        """Test the sample data generation produces correct structure."""
        view = MonitorHealthStatusView()

        # Test ZoneMinder monitor
        zm_health = view._get_sample_health_status('zoneminder')
        self.assertEqual(zm_health.status, MonitorHealthStatusType.HEALTHY)
        self.assertTrue(zm_health.has_api_sources)
        self.assertEqual(len(zm_health.api_sources), 1)
        self.assertEqual(zm_health.api_sources[0].status, ApiSourceHealthStatusType.HEALTHY)

        # Test Weather monitor
        weather_health = view._get_sample_health_status('weather')
        self.assertEqual(weather_health.status, MonitorHealthStatusType.WARNING)
        self.assertTrue(weather_health.has_api_sources)
        self.assertEqual(len(weather_health.api_sources), 4)

        # Test Alert monitor (no API sources)
        alert_health = view._get_sample_health_status('alert')
        self.assertEqual(alert_health.status, MonitorHealthStatusType.ERROR)
        self.assertFalse(alert_health.has_api_sources)
        self.assertEqual(len(alert_health.api_sources), 0)

    def test_monitor_label_generation(self):
        """Test monitor label generation from IDs."""
        view = MonitorHealthStatusView()

        self.assertEqual(view._get_monitor_label('zoneminder'), 'ZoneMinder Integration')
        self.assertEqual(view._get_monitor_label('weather'), 'Weather Updates Monitor')
        self.assertEqual(view._get_monitor_label('alert'), 'Alert Processing Monitor')
        self.assertEqual(view._get_monitor_label('unknown'), 'Monitor unknown')
