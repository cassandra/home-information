import logging

from django.urls import reverse

from hi.apps.entity.models import Entity, EntityState
from hi.apps.sense.models import Sensor, SensorHistory
from hi.testing.view_test_base import DualModeViewTestCase

logging.disable(logging.CRITICAL)


class TestSensorHistoryView(DualModeViewTestCase):
    """
    Tests for SensorHistoryView - demonstrates HiModalView with pagination testing.
    This view displays the history of sensor readings.
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
            name='temperature',
            entity_state_type_str='NUMERIC'
        )
        self.sensor = Sensor.objects.create(
            entity_state=self.entity_state,
            sensor_type_str='TEMPERATURE',
            integration_payload='{"device_id": "temp_01"}'
        )
        
        # Create test sensor history entries
        for i in range(5):
            SensorHistory.objects.create(
                sensor=self.sensor,
                value=f'{20 + i}.5',
                response_datetime=f'2023-01-0{i+1}T12:00:00Z'
            )

    def test_get_sensor_history_sync(self):
        """Test getting sensor history with synchronous request."""
        url = reverse('sense_sensor_history', kwargs={'sensor_id': self.sensor.id})
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        self.assertHtmlResponse(response)
        self.assertTemplateRendered(response, 'sense/modals/sensor_history.html')

    def test_get_sensor_history_async(self):
        """Test getting sensor history with AJAX request."""
        url = reverse('sense_sensor_history', kwargs={'sensor_id': self.sensor.id})
        response = self.async_get(url)

        self.assertSuccessResponse(response)
        self.assertJsonResponse(response)
        
        # HiModalView returns JSON with modal content for AJAX requests
        data = response.json()
        self.assertIn('modal', data)

    def test_sensor_and_history_in_context(self):
        """Test that sensor and history are passed to template context."""
        url = reverse('sense_sensor_history', kwargs={'sensor_id': self.sensor.id})
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        self.assertEqual(response.context['sensor'], self.sensor)
        self.assertIn('sensor_history_list', response.context)
        self.assertIn('pagination', response.context)
        
        # Should have our test entries
        history_list = response.context['sensor_history_list']
        self.assertEqual(len(history_list), 5)

    def test_pagination_context(self):
        """Test that pagination is properly configured."""
        url = reverse('sense_sensor_history', kwargs={'sensor_id': self.sensor.id})
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        pagination = response.context['pagination']
        self.assertIsNotNone(pagination)
        # Should have base URL for sensor history
        self.assertIn(str(self.sensor.id), pagination.base_url)

    def test_history_filtered_by_sensor(self):
        """Test that history is filtered to only this sensor."""
        # Create another sensor with history
        other_entity = Entity.objects.create(
            name='Other Sensor',
            entity_type_str='SENSOR'
        )
        other_entity_state = EntityState.objects.create(
            entity=other_entity,
            name='humidity',
            entity_state_type_str='NUMERIC'
        )
        other_sensor = Sensor.objects.create(
            entity_state=other_entity_state,
            sensor_type_str='HUMIDITY',
            integration_payload='{"device_id": "hum_01"}'
        )
        SensorHistory.objects.create(
            sensor=other_sensor,
            value='45.0',
            response_datetime='2023-01-10T12:00:00Z'
        )

        url = reverse('sense_sensor_history', kwargs={'sensor_id': self.sensor.id})
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        history_list = response.context['sensor_history_list']
        
        # All history entries should belong to our sensor
        for history_entry in history_list:
            self.assertEqual(history_entry.sensor, self.sensor)

    def test_pagination_with_many_entries(self):
        """Test pagination when there are many sensor history entries."""
        # Create many more history entries to test pagination
        for i in range(50):
            SensorHistory.objects.create(
                sensor=self.sensor,
                value=f'{30 + i}.0',
                response_datetime=f'2023-02-{(i % 28) + 1:02d}T12:00:00Z'
            )

        url = reverse('sense_sensor_history', kwargs={'sensor_id': self.sensor.id})
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        history_list = response.context['sensor_history_list']
        
        # Should be limited by page size (25)
        self.assertLessEqual(len(history_list), 25)

    def test_pagination_page_size_constant(self):
        """Test that the page size constant is used correctly."""
        from hi.apps.sense.views import SensorHistoryView
        self.assertEqual(SensorHistoryView.SENSOR_HISTORY_PAGE_SIZE, 25)

    def test_empty_sensor_history_list(self):
        """Test page displays correctly when no sensor history exists."""
        # Delete all sensor history
        SensorHistory.objects.all().delete()
        
        url = reverse('sense_sensor_history', kwargs={'sensor_id': self.sensor.id})
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        history_list = response.context['sensor_history_list']
        self.assertEqual(len(history_list), 0)

    def test_pagination_with_page_parameter(self):
        """Test pagination with specific page parameter."""
        # Create enough entries to have multiple pages
        for i in range(30):
            SensorHistory.objects.create(
                sensor=self.sensor,
                value=f'{40 + i}.0',
                response_datetime=f'2023-03-{(i % 28) + 1:02d}T12:00:00Z'
            )

        url = reverse('sense_sensor_history', kwargs={'sensor_id': self.sensor.id})
        response = self.client.get(url, {'page': '2'})

        self.assertSuccessResponse(response)
        # Should still return valid response for page 2
        self.assertIn('sensor_history_list', response.context)

    def test_nonexistent_sensor_returns_404(self):
        """Test that accessing nonexistent sensor returns 404."""
        url = reverse('sense_sensor_history', kwargs={'sensor_id': 99999})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)

    def test_post_not_allowed(self):
        """Test that POST requests are not allowed."""
        url = reverse('sense_sensor_history', kwargs={'sensor_id': self.sensor.id})
        response = self.client.post(url)

        self.assertEqual(response.status_code, 405)


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
        
