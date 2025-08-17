import logging
from unittest.mock import Mock, patch

from django.urls import reverse

from hi.apps.console.console_helper import ConsoleSettingsHelper
from hi.apps.console.constants import ConsoleConstants
from hi.apps.sense.models import Sensor
from hi.apps.sense.sensor_response_manager import SensorResponseManager
from hi.enums import ViewType
from hi.tests.view_test_base import DualModeViewTestCase, SyncViewTestCase

logging.disable(logging.CRITICAL)


class TestSensorVideoStreamView(DualModeViewTestCase):
    """
    Tests for SensorVideoStreamView - demonstrates HiGridView testing for video streams.
    This view displays a video stream from a sensor.
    """

    def setUp(self):
        super().setUp()
        # Create test entity and sensor
        from hi.apps.entity.models import Entity, EntityState
        self.entity = Entity.objects.create(
            name='Video Camera',
            entity_type_str='CAMERA'
        )
        self.entity_state = EntityState.objects.create(
            entity=self.entity,
            name='video_stream',
            entity_state_type_str='TEXT'
        )
        self.sensor = Sensor.objects.create(
            name='Video Stream Sensor',
            entity_state=self.entity_state,
            sensor_type_str='VIDEO_STREAM',
            integration_id='test_camera_01'
        )

    @patch.object(SensorResponseManager, 'get_latest_sensor_responses')
    def test_get_video_stream_sync(self, mock_get_responses):
        """Test getting video stream with synchronous request."""
        mock_response = Mock()
        mock_response.value = 'http://test-stream-url.com/stream'
        mock_get_responses.return_value = {self.sensor: [mock_response]}

        url = reverse('console_sensor_video_stream', kwargs={'sensor_id': self.sensor.id})
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        self.assertHtmlResponse(response)
        self.assertTemplateRendered(response, 'console/panes/sensor_video_stream.html')
        
        # Check that view parameters are set
        session = self.client.session
        self.assertEqual(session.get('view_type'), str(ViewType.VIDEO_STREAM))

    @patch.object(SensorResponseManager, 'get_latest_sensor_responses')
    def test_get_video_stream_async(self, mock_get_responses):
        """Test getting video stream with AJAX request."""
        mock_response = Mock()
        mock_response.value = 'http://test-stream-url.com/stream'
        mock_get_responses.return_value = {self.sensor: [mock_response]}

        url = reverse('console_sensor_video_stream', kwargs={'sensor_id': self.sensor.id})
        response = self.async_get(url)

        self.assertSuccessResponse(response)
        self.assertJsonResponse(response)
        
        # HiGridView returns JSON with insert and pushUrl for AJAX requests
        data = response.json()
        self.assertIn('insert', data)  # Contains the main content
        self.assertIn('pushUrl', data)  # Contains the URL for browser history

    def test_nonexistent_sensor_returns_404(self):
        """Test that accessing nonexistent sensor returns 404."""
        url = reverse('console_sensor_video_stream', kwargs={'sensor_id': 99999})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)

    @patch.object(SensorResponseManager, 'get_latest_sensor_responses')
    def test_no_video_stream_returns_400(self, mock_get_responses):
        """Test that no available video stream returns BadRequest."""
        mock_get_responses.return_value = {}

        url = reverse('console_sensor_video_stream', kwargs={'sensor_id': self.sensor.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 400)

    @patch.object(SensorResponseManager, 'get_latest_sensor_responses')
    def test_sensor_and_response_in_context(self, mock_get_responses):
        """Test that sensor and response are passed to template context."""
        mock_response = Mock()
        mock_response.value = 'http://test-stream-url.com/stream'
        mock_get_responses.return_value = {self.sensor: [mock_response]}

        url = reverse('console_sensor_video_stream', kwargs={'sensor_id': self.sensor.id})
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        self.assertEqual(response.context['sensor'], self.sensor)
        self.assertEqual(response.context['sensor_response'], mock_response)


class TestConsoleLockView(SyncViewTestCase):
    """
    Tests for ConsoleLockView - demonstrates POST-only view testing.
    This view locks the console interface.
    """

    @patch.object(ConsoleSettingsHelper, 'get_console_lock_password')
    def test_lock_with_existing_password(self, mock_get_password):
        """Test locking console when password is already set."""
        mock_get_password.return_value = 'test_password'

        url = reverse('console_lock')
        response = self.client.post(url)

        self.assertSuccessResponse(response)
        # Should set session variable and redirect to unlock view
        self.assertTrue(self.client.session.get(ConsoleConstants.CONSOLE_LOCKED_SESSION_VAR))

    @patch.object(ConsoleSettingsHelper, 'get_console_lock_password')
    def test_lock_without_password_shows_set_password(self, mock_get_password):
        """Test locking console when no password is set shows set password modal."""
        mock_get_password.return_value = None

        url = reverse('console_lock')
        response = self.client.post(url)

        self.assertSuccessResponse(response)
        # Should render set password template
        self.assertTemplateRendered(response, 'console/modals/set_lock_password.html')

    def test_get_not_allowed(self):
        """Test that GET requests are not allowed."""
        url = reverse('console_lock')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 405)


class TestSetLockPasswordView(DualModeViewTestCase):
    """
    Tests for SetLockPasswordView - demonstrates HiModalView with form testing.
    This view allows setting a console lock password.
    """

    def test_get_set_password_modal_sync(self):
        """Test getting set password modal with synchronous request."""
        url = reverse('console_set_lock_password')
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        self.assertHtmlResponse(response)
        self.assertTemplateRendered(response, 'console/modals/set_lock_password.html')

    def test_get_set_password_modal_async(self):
        """Test getting set password modal with AJAX request."""
        url = reverse('console_set_lock_password')
        response = self.async_get(url)

        self.assertSuccessResponse(response)
        self.assertJsonResponse(response)
        
        # HiModalView returns JSON with modal content for AJAX requests
        data = response.json()
        self.assertIn('modal', data)

    @patch.object(ConsoleSettingsHelper, 'set_console_lock_password')
    def test_post_valid_password(self, mock_set_password):
        """Test posting valid password."""
        mock_set_password.return_value = None

        url = reverse('console_set_lock_password')
        response = self.client.post(url, {'password': 'new_password'})

        self.assertSuccessResponse(response)
        mock_set_password.assert_called_once_with(password='new_password')
        
        # Should set session variable and show unlock view
        self.assertTrue(self.client.session.get(ConsoleConstants.CONSOLE_LOCKED_SESSION_VAR))

    def test_post_empty_password_returns_400(self):
        """Test posting empty password returns BadRequest."""
        url = reverse('console_set_lock_password')
        response = self.client.post(url, {'password': ''})

        self.assertEqual(response.status_code, 400)

    def test_post_no_password_returns_400(self):
        """Test posting without password field returns BadRequest."""
        url = reverse('console_set_lock_password')
        response = self.client.post(url, {})

        self.assertEqual(response.status_code, 400)


class TestConsoleUnlockView(DualModeViewTestCase):
    """
    Tests for ConsoleUnlockView - demonstrates HiModalView with authentication testing.
    This view allows unlocking the console interface.
    """

    def test_get_unlock_modal_sync(self):
        """Test getting unlock modal with synchronous request."""
        url = reverse('console_unlock')
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        self.assertHtmlResponse(response)
        self.assertTemplateRendered(response, 'console/modals/console_unlock.html')

    def test_get_unlock_modal_async(self):
        """Test getting unlock modal with AJAX request."""
        url = reverse('console_unlock')
        response = self.async_get(url)

        self.assertSuccessResponse(response)
        self.assertJsonResponse(response)
        
        # HiModalView returns JSON with modal content for AJAX requests
        data = response.json()
        self.assertIn('modal', data)

    @patch.object(ConsoleSettingsHelper, 'get_console_lock_password')
    def test_post_valid_password_unlocks(self, mock_get_password):
        """Test posting correct password unlocks console."""
        mock_get_password.return_value = 'correct_password'
        
        # First lock the console
        session = self.client.session
        session[ConsoleConstants.CONSOLE_LOCKED_SESSION_VAR] = True
        session.save()

        url = reverse('console_unlock')
        response = self.client.post(url, {'password': 'correct_password'})

        self.assertSuccessResponse(response)
        # Should unlock console
        self.assertFalse(self.client.session.get(ConsoleConstants.CONSOLE_LOCKED_SESSION_VAR))

    @patch.object(ConsoleSettingsHelper, 'get_console_lock_password')
    def test_post_invalid_password_returns_400(self, mock_get_password):
        """Test posting incorrect password returns BadRequest."""
        mock_get_password.return_value = 'correct_password'

        url = reverse('console_unlock')
        response = self.client.post(url, {'password': 'wrong_password'})

        self.assertEqual(response.status_code, 400)

    def test_post_empty_password_returns_400(self):
        """Test posting empty password returns BadRequest."""
        url = reverse('console_unlock')
        response = self.client.post(url, {'password': ''})

        self.assertEqual(response.status_code, 400)

    def test_post_no_password_returns_400(self):
        """Test posting without password field returns BadRequest."""
        url = reverse('console_unlock')
        response = self.client.post(url, {})

        self.assertEqual(response.status_code, 400)

    @patch.object(ConsoleSettingsHelper, 'get_console_lock_password')
    def test_unlock_without_password_set_succeeds(self, mock_get_password):
        """Test unlocking when no password is set (exceptional case handling)."""
        mock_get_password.return_value = None

        url = reverse('console_unlock')
        response = self.client.post(url, {'password': 'any_password'})

        self.assertSuccessResponse(response)
        # Should unlock console even with no password set
        self.assertFalse(self.client.session.get(ConsoleConstants.CONSOLE_LOCKED_SESSION_VAR))
