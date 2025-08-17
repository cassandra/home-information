import logging
from datetime import datetime, timezone

from django.urls import reverse

from hi.tests.view_test_base import AsyncViewTestCase

logging.disable(logging.CRITICAL)


class TestStatusView(AsyncViewTestCase):
    """
    Tests for StatusView - demonstrates asynchronous JSON view testing.
    This critical view is called every 3 seconds from clients and provides
    the main payload that drives client-side view updates.
    """

    def test_status_view_returns_json_with_ajax(self):
        """Test that StatusView returns valid JSON when called with AJAX headers."""
        url = reverse('api_status')
        response = self.async_get(url)
        
        self.assertSuccessResponse(response)
        self.assertJsonResponse(response)
        
        data = response.json()
        # Verify required fields in the status response
        self.assertIn('timestamp', data)
        self.assertIn('startTimestamp', data)
        self.assertIn('alertData', data)
        self.assertIn('cssClassUpdateMap', data)
        self.assertIn('idReplaceUpdateMap', data)
        self.assertIn('idReplaceHashMap', data)

    def test_status_view_timestamp_format(self):
        """Test that timestamps in status response are properly formatted."""
        url = reverse('api_status')
        response = self.async_get(url)
        
        self.assertSuccessResponse(response)
        data = response.json()
        
        # Verify timestamps are valid ISO format
        timestamp = data['timestamp']
        start_timestamp = data['startTimestamp']
        
        # Should be able to parse as datetime
        parsed_timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        parsed_start_timestamp = datetime.fromisoformat(start_timestamp.replace('Z', '+00:00'))
        
        self.assertIsInstance(parsed_timestamp, datetime)
        self.assertIsInstance(parsed_start_timestamp, datetime)

    def test_status_view_with_last_timestamp_parameter(self):
        """Test status view handles lastTimestamp query parameter correctly."""
        last_timestamp = datetime.now(timezone.utc).isoformat()
        url = reverse('api_status')
        response = self.async_get(url, {'lastTimestamp': last_timestamp})
        
        self.assertSuccessResponse(response)
        self.assertJsonResponse(response)
        
        data = response.json()
        self.assertIn('timestamp', data)
        # The response should still contain all required fields
        self.assertIn('alertData', data)

    def test_status_view_with_invalid_timestamp_parameter(self):
        """Test status view handles invalid lastTimestamp parameter with error response."""
        url = reverse('api_status')
        response = self.async_get(url, {'lastTimestamp': 'invalid-date'})
        
        # Should return error response for invalid timestamp
        self.assertErrorResponse(response)

    def test_status_view_hash_map_structure(self):
        """Test that idReplaceHashMap contains valid MD5 hashes."""
        url = reverse('api_status')
        response = self.async_get(url)
        
        self.assertSuccessResponse(response)
        data = response.json()
        
        id_replace_map = data['idReplaceUpdateMap']
        id_replace_hash_map = data['idReplaceHashMap']
        
        # Hash map should have entries for each id_replace_map entry
        for element_id in id_replace_map.keys():
            self.assertIn(element_id, id_replace_hash_map)
            # MD5 hashes should be 32 character hex strings
            hash_value = id_replace_hash_map[element_id]
            self.assertEqual(len(hash_value), 32)
            self.assertTrue(all(c in '0123456789abcdef' for c in hash_value.lower()))

    def test_status_view_alert_data_structure(self):
        """Test that alertData has expected structure."""
        url = reverse('api_status')
        response = self.async_get(url)
        
        self.assertSuccessResponse(response)
        data = response.json()
        
        alert_data = data['alertData']
        self.assertIsInstance(alert_data, dict)
        # AlertData should be a dict (specific structure depends on AlertStatusData.to_dict())
