import logging

from django.urls import reverse

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
