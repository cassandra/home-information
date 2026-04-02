import logging
from unittest.mock import Mock, patch

from django.http import HttpResponse
from django.test import RequestFactory
from django.urls import reverse

from hi.apps.console.constants import ConsoleConstants
from hi.apps.console.middleware import ConsoleLockMiddleware
from hi.testing.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestConsoleLockMiddleware(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()
        self.get_response = Mock(return_value=HttpResponse('ok'))
        self.middleware = ConsoleLockMiddleware(self.get_response)

    def test_process_request_new_away_auto_lock_version_locks_console(self):
        """Test middleware auto-locks when a new AWAY auto-lock event is seen."""
        request = self.factory.get('/console/entity/video-stream/1')
        request.session = {}

        with patch('hi.apps.console.middleware.SecurityManager') as mock_security_manager, \
             patch('hi.apps.console.middleware.ConsoleUnlockView') as mock_unlock_view_class:
            mock_security_manager.return_value.get_console_away_auto_lock_version.return_value = '2'

            mock_unlock_view = Mock()
            mock_unlock_response = HttpResponse('locked', status=403)
            mock_unlock_view.get.return_value = mock_unlock_response
            mock_unlock_view_class.return_value = mock_unlock_view

            response = self.middleware.process_request(request)

            self.assertEqual(
                request.session[ConsoleConstants.CONSOLE_AWAY_AUTO_LOCK_VERSION_SESSION_VAR],
                '2',
            )
            self.assertTrue(request.session[ConsoleConstants.CONSOLE_LOCKED_SESSION_VAR])
            mock_unlock_view.get.assert_called_once_with(request)
            self.assertEqual(response, mock_unlock_response)

    def test_process_request_same_auto_lock_version_does_not_relock(self):
        """Test middleware does not relock when the AWAY auto-lock event was already seen."""
        request = self.factory.get('/console/entity/video-stream/1')
        request.session = {
            ConsoleConstants.CONSOLE_AWAY_AUTO_LOCK_VERSION_SESSION_VAR: '2',
            ConsoleConstants.CONSOLE_LOCKED_SESSION_VAR: False,
        }

        with patch('hi.apps.console.middleware.SecurityManager') as mock_security_manager, \
             patch('hi.apps.console.middleware.ConsoleUnlockView') as mock_unlock_view_class:
            mock_security_manager.return_value.get_console_away_auto_lock_version.return_value = '2'

            response = self.middleware.process_request(request)

            self.assertIsNone(response)
            self.assertFalse(request.session[ConsoleConstants.CONSOLE_LOCKED_SESSION_VAR])
            mock_unlock_view_class.assert_not_called()

    def test_process_request_already_locked_marks_new_version_but_respects_unlock_path(self):
        """Test middleware records new event version while allowing excluded unlock path."""
        request = self.factory.get(reverse('console_unlock'))
        request.session = {
            ConsoleConstants.CONSOLE_AWAY_AUTO_LOCK_VERSION_SESSION_VAR: '2',
            ConsoleConstants.CONSOLE_LOCKED_SESSION_VAR: True,
        }

        with patch('hi.apps.console.middleware.SecurityManager') as mock_security_manager, \
             patch('hi.apps.console.middleware.ConsoleUnlockView') as mock_unlock_view_class:
            mock_security_manager.return_value.get_console_away_auto_lock_version.return_value = '3'

            response = self.middleware.process_request(request)

            self.assertIsNone(response)
            self.assertEqual(
                request.session[ConsoleConstants.CONSOLE_AWAY_AUTO_LOCK_VERSION_SESSION_VAR],
                '3',
            )
            self.assertTrue(request.session[ConsoleConstants.CONSOLE_LOCKED_SESSION_VAR])
            mock_unlock_view_class.assert_not_called()

    def test_process_request_without_auto_lock_version_does_nothing(self):
        """Test middleware leaves lock state unchanged when there is no AWAY auto-lock event."""
        request = self.factory.get('/console/entity/video-stream/1')
        request.session = {}

        with patch('hi.apps.console.middleware.SecurityManager') as mock_security_manager, \
             patch('hi.apps.console.middleware.ConsoleUnlockView') as mock_unlock_view_class:
            mock_security_manager.return_value.get_console_away_auto_lock_version.return_value = None

            response = self.middleware.process_request(request)

            self.assertIsNone(response)
            self.assertNotIn(ConsoleConstants.CONSOLE_LOCKED_SESSION_VAR, request.session)
            mock_unlock_view_class.assert_not_called()
