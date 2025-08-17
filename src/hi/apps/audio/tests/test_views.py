import logging

from django.urls import reverse

from hi.tests.view_test_base import DualModeViewTestCase

logging.disable(logging.CRITICAL)


class TestAudioPermissionGuidanceView(DualModeViewTestCase):
    """
    Tests for AudioPermissionGuidanceView - demonstrates simple HiModalView testing.
    This view displays audio permission guidance in a modal.
    """

    def test_get_guidance_sync(self):
        """Test getting audio permission guidance with synchronous request."""
        url = reverse('audio_permission_guidance')
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        self.assertHtmlResponse(response)
        self.assertTemplateRendered(response, 'audio/modals/audio_permission_guidance.html')

    def test_get_guidance_async(self):
        """Test getting audio permission guidance with AJAX request."""
        url = reverse('audio_permission_guidance')
        response = self.async_get(url)

        self.assertSuccessResponse(response)
        self.assertJsonResponse(response)
        
        # HiModalView returns JSON with modal content for AJAX requests
        data = response.json()
        self.assertIn('modal', data)
        self.assertIsInstance(data['modal'], str)
        self.assertTrue(len(data['modal']) > 0)

    def test_post_not_allowed(self):
        """Test that POST requests are not allowed (method not implemented)."""
        url = reverse('audio_permission_guidance')
        response = self.client.post(url)

        # Should return 405 Method Not Allowed
        self.assertEqual(response.status_code, 405)
