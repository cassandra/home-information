import logging

from django.urls import reverse

from hi.apps.entity.models import Entity, EntityState
from hi.apps.sense.models import Sensor, SensorHistory
from hi.testing.view_test_base import DualModeViewTestCase

logging.disable(logging.CRITICAL)


class TestSensorHistoryDetailsView(DualModeViewTestCase):
    """
    Tests for SensorHistoryDetailsView - demonstrates sensor history detail testing.
    This view displays detailed information about a specific sensor history entry.
    """

    def setUp(self):
        super().setUp()
        # Create test entity and sensor
        self.entity = Entity.objects.create(
            name='Test Sensor Entity',
            entity_type_str='SENSOR'
        )
        self.entity_state = EntityState.objects.create(
            entity=self.entity,
            name='pressure',
            entity_state_type_str='NUMERIC'
        )
        self.sensor = Sensor.objects.create(
            entity_state=self.entity_state,
            sensor_type_str='PRESSURE',
            integration_payload='{"device_id": "press_01"}'
        )

        # Create test sensor history entry
        self.sensor_history = SensorHistory.objects.create(
            sensor=self.sensor,
            value='1013.25',
            response_datetime='2023-01-15T14:30:00Z'
        )

    def test_get_sensor_history_details_sync(self):
        """Test getting sensor history details with synchronous request."""
        url = reverse('sense_sensor_history_details', kwargs={'sensor_history_id': self.sensor_history.id})
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        self.assertHtmlResponse(response)
        self.assertTemplateRendered(response, 'sense/modals/sensor_history_details.html')

    def test_get_sensor_history_details_async(self):
        """Test getting sensor history details with AJAX request."""
        url = reverse('sense_sensor_history_details', kwargs={'sensor_history_id': self.sensor_history.id})
        response = self.async_get(url)

        self.assertSuccessResponse(response)
        self.assertJsonResponse(response)

        # HiModalView returns JSON with modal content for AJAX requests
        data = response.json()
        self.assertIn('modal', data)

    def test_sensor_history_in_context(self):
        """Test that sensor history is passed to template context."""
        url = reverse('sense_sensor_history_details', kwargs={'sensor_history_id': self.sensor_history.id})
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        self.assertEqual(response.context['sensor_history'], self.sensor_history)

    def test_sensor_history_details_content(self):
        """Test that sensor history details contain expected information."""
        url = reverse('sense_sensor_history_details', kwargs={'sensor_history_id': self.sensor_history.id})
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        # Should have access to the sensor history entry with all its data
        history = response.context['sensor_history']
        self.assertEqual(history.value, '1013.25')
        self.assertEqual(history.sensor, self.sensor)

    def test_nonexistent_sensor_history_returns_404(self):
        """Test that accessing nonexistent sensor history returns 404."""
        url = reverse('sense_sensor_history_details', kwargs={'sensor_history_id': 99999})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)

    def test_post_not_allowed(self):
        """Test that POST requests are not allowed."""
        url = reverse('sense_sensor_history_details', kwargs={'sensor_history_id': self.sensor_history.id})
        response = self.client.post(url)

        self.assertEqual(response.status_code, 405)

    def test_different_sensor_history_entries(self):
        """Test accessing different sensor history entries."""
        # Create another sensor history entry
        other_history = SensorHistory.objects.create(
            sensor=self.sensor,
            value='1020.50',
            response_datetime='2023-01-16T09:15:00Z'
        )

        url = reverse('sense_sensor_history_details', kwargs={'sensor_history_id': other_history.id})
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        self.assertEqual(response.context['sensor_history'], other_history)
        self.assertNotEqual(response.context['sensor_history'], self.sensor_history)
