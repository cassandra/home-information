import logging
from unittest.mock import Mock, patch

from django.http import HttpResponse
from django.test import RequestFactory
from django.urls import reverse

from hi.apps.console.constants import ConsoleConstants
from hi.apps.console.middleware import ConsoleLockMiddleware
from hi.testing.base_test_case import BaseTestCase

logging.disable( logging.CRITICAL )


class TestConsoleLockMiddleware( BaseTestCase ):

    def setUp( self ):
        super().setUp()
        self.factory = RequestFactory()
        self.get_response = Mock( return_value = HttpResponse( 'ok' ) )
        self.middleware = ConsoleLockMiddleware( self.get_response )
        return

    def test_new_away_auto_lock_version_locks_console( self ):
        """Middleware auto-locks when a new AWAY auto-lock event is seen."""
        request = self.factory.get( reverse( 'home' ) )
        request.session = {}

        with patch( 'hi.apps.console.middleware.SecurityManager' ) as mock_security_manager, \
             patch( 'hi.apps.console.middleware.ConsoleSettingsHelper' ) as mock_helper, \
             patch( 'hi.apps.console.middleware.ConsoleUnlockView' ) as mock_unlock_view:
            mock_security_manager.return_value.get_console_away_lock_timestamp.return_value = '2'
            mock_helper.return_value.get_console_lock_password.return_value = 'secret'
            mock_unlock_view.return_value.get.return_value = HttpResponse( 'locked', status = 403 )

            response = self.middleware.process_request( request )

            self.assertEqual(
                request.session[ConsoleConstants.CONSOLE_AWAY_LOCK_TIMESTAMP_SESSION_VAR],
                '2',
            )
            self.assertTrue( request.session[ConsoleConstants.CONSOLE_LOCKED_SESSION_VAR] )
            self.assertIsNotNone( response )
        return

    def test_same_auto_lock_version_does_not_relock( self ):
        """Middleware does not relock when the AWAY auto-lock event was already seen."""
        request = self.factory.get( reverse( 'home' ) )
        request.session = {
            ConsoleConstants.CONSOLE_AWAY_LOCK_TIMESTAMP_SESSION_VAR: '2',
            ConsoleConstants.CONSOLE_LOCKED_SESSION_VAR: False,
        }

        with patch( 'hi.apps.console.middleware.SecurityManager' ) as mock_security_manager:
            mock_security_manager.return_value.get_console_away_lock_timestamp.return_value = '2'

            response = self.middleware.process_request( request )

            self.assertIsNone( response )
            self.assertFalse( request.session[ConsoleConstants.CONSOLE_LOCKED_SESSION_VAR] )
        return

    def test_already_locked_records_version_and_respects_unlock_path( self ):
        """Middleware records new event version while allowing excluded unlock path."""
        request = self.factory.get( reverse( 'console_unlock' ) )
        request.session = {
            ConsoleConstants.CONSOLE_AWAY_LOCK_TIMESTAMP_SESSION_VAR: '2',
            ConsoleConstants.CONSOLE_LOCKED_SESSION_VAR: True,
        }

        with patch( 'hi.apps.console.middleware.SecurityManager' ) as mock_security_manager:
            mock_security_manager.return_value.get_console_away_lock_timestamp.return_value = '3'

            response = self.middleware.process_request( request )

            self.assertIsNone( response )
            self.assertEqual(
                request.session[ConsoleConstants.CONSOLE_AWAY_LOCK_TIMESTAMP_SESSION_VAR],
                '3',
            )
            self.assertTrue( request.session[ConsoleConstants.CONSOLE_LOCKED_SESSION_VAR] )
        return

    def test_no_auto_lock_version_does_nothing( self ):
        """Middleware leaves lock state unchanged when there is no AWAY auto-lock event."""
        request = self.factory.get( reverse( 'home' ) )
        request.session = {}

        with patch( 'hi.apps.console.middleware.SecurityManager' ) as mock_security_manager:
            mock_security_manager.return_value.get_console_away_lock_timestamp.return_value = None

            response = self.middleware.process_request( request )

            self.assertIsNone( response )
            self.assertNotIn( ConsoleConstants.CONSOLE_LOCKED_SESSION_VAR, request.session )
        return

    def test_new_auto_lock_version_without_password_does_not_lock( self ):
        """Middleware records event version but does not lock when no password exists."""
        request = self.factory.get( reverse( 'home' ) )
        request.session = {}

        with patch( 'hi.apps.console.middleware.SecurityManager' ) as mock_security_manager, \
             patch( 'hi.apps.console.middleware.ConsoleSettingsHelper' ) as mock_helper:
            mock_security_manager.return_value.get_console_away_lock_timestamp.return_value = '2'
            mock_helper.return_value.get_console_lock_password.return_value = ''

            response = self.middleware.process_request( request )

            self.assertIsNone( response )
            self.assertEqual(
                request.session[ConsoleConstants.CONSOLE_AWAY_LOCK_TIMESTAMP_SESSION_VAR],
                '2',
            )
            self.assertNotIn( ConsoleConstants.CONSOLE_LOCKED_SESSION_VAR, request.session )
        return

    def test_api_status_excluded_when_locked( self ):
        """Locked session does not block api_status path, which must stay pollable."""
        request = self.factory.get( reverse( 'api_status' ) )
        request.session = {
            ConsoleConstants.CONSOLE_AWAY_LOCK_TIMESTAMP_SESSION_VAR: '2',
            ConsoleConstants.CONSOLE_LOCKED_SESSION_VAR: True,
        }

        with patch( 'hi.apps.console.middleware.SecurityManager' ) as mock_security_manager:
            mock_security_manager.return_value.get_console_away_lock_timestamp.return_value = '3'

            response = self.middleware.process_request( request )

            self.assertIsNone( response )
            self.assertEqual(
                request.session[ConsoleConstants.CONSOLE_AWAY_LOCK_TIMESTAMP_SESSION_VAR],
                '3',
            )
            self.assertTrue( request.session[ConsoleConstants.CONSOLE_LOCKED_SESSION_VAR] )
        return
