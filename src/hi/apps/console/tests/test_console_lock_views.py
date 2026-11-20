import logging

from django.urls import reverse

import hi.apps.common.datetimeproxy as datetimeproxy

from hi.apps.config.settings_manager import SettingsManager
from hi.apps.console.console_helper import ConsoleSettingsHelper
from hi.apps.console.constants import ConsoleConstants
from hi.apps.console.settings import ConsoleSetting
from hi.apps.console.unlock_throttle import UnlockThrottle
from hi.apps.console.views import ConsoleUnlockView
from hi.testing.view_test_base import AsyncViewTestCase, DualModeViewTestCase

logging.disable( logging.CRITICAL )


class LockViewTestBase( AsyncViewTestCase ):

    def setUp( self ):
        super().setUp()
        # Fresh singletons: the helper caches its settings manager.
        for singleton_class in ( SettingsManager, ConsoleSettingsHelper ):
            singleton_class._instance = None
            self.addCleanup( setattr, singleton_class, '_instance', None )
        return

    def set_stored_pin( self, value ):
        """ Stores the raw setting value; may be a legacy non-PIN password. """
        SettingsManager().set_setting_value( ConsoleSetting.CONSOLE_LOCK_PASSWORD, value or '' )
        return

    def stored_pin( self ):
        return ConsoleSettingsHelper().get_console_lock_pin()

    def set_locked( self, is_locked ):
        session = self.client.session
        session[ConsoleConstants.CONSOLE_LOCKED_SESSION_VAR] = is_locked
        session.save()
        return

    def is_locked( self ):
        return self.client.session.get( ConsoleConstants.CONSOLE_LOCKED_SESSION_VAR, False )


class TestConsoleLockView( LockViewTestBase ):

    def test_legacy_password_prompts_to_set_pin( self ):
        self.set_stored_pin( 'hunter2' )
        response = self.async_post( reverse( 'console_lock' ))
        self.assertTemplateRendered( response, 'console/modals/set_lock_pin.html' )
        self.assertFalse( self.is_locked() )
        return

    def test_with_valid_pin_locks_and_prompts_unlock( self ):
        self.set_stored_pin( '1234' )
        response = self.async_post( reverse( 'console_lock' ))
        self.assertTemplateRendered( response, 'console/modals/console_unlock.html' )
        self.assertTrue( self.is_locked() )
        return


class TestSetLockPinView( LockViewTestBase ):

    def test_matching_valid_pin_is_stored_and_locks( self ):
        response = self.async_post( reverse( 'console_set_lock_pin' ),
                                    { 'pin': '0429', 'pin_confirm': '0429' } )
        self.assertEqual( self.stored_pin(), '0429' )
        self.assertTrue( self.is_locked() )
        self.assertTemplateRendered( response, 'console/modals/console_unlock.html' )
        return

    def test_mismatched_confirmation_rerenders_with_error( self ):
        response = self.async_post( reverse( 'console_set_lock_pin' ),
                                    { 'pin': '0429', 'pin_confirm': '0428' } )
        self.assertResponseStatusCode( response, 400 )
        self.assertTemplateRendered( response, 'console/modals/set_lock_pin.html' )
        self.assertIn( 'PINs did not match', response.content.decode() )
        self.assertIsNone( self.stored_pin() )
        self.assertFalse( self.is_locked() )
        return

    def test_invalid_pin_rerenders_with_error( self ):
        response = self.async_post( reverse( 'console_set_lock_pin' ),
                                    { 'pin': '12a4', 'pin_confirm': '12a4' } )
        self.assertResponseStatusCode( response, 400 )
        self.assertIn( 'PIN must be exactly 4 digits', response.content.decode() )
        self.assertIsNone( self.stored_pin() )
        return


class TestConsoleUnlockView( LockViewTestBase ):

    def test_correct_pin_unlocks( self ):
        self.set_stored_pin( '1234' )
        self.set_locked( True )
        self.async_post( reverse( 'console_unlock' ), { 'pin': '1234' } )
        self.assertFalse( self.is_locked() )
        return

    def test_wrong_pin_rerenders_keypad_in_place_and_stays_locked( self ):
        self.set_stored_pin( '1234' )
        self.set_locked( True )
        response = self.async_post( reverse( 'console_unlock' ), { 'pin': '4321' } )
        self.assertResponseStatusCode( response, 400 )
        replace_map = response.json()['replace']
        self.assertEqual( list( replace_map.keys() ), [ ConsoleUnlockView.KEYPAD_HTML_ID ] )
        self.assertIn( f'id="{ConsoleUnlockView.KEYPAD_HTML_ID}"', replace_map[ConsoleUnlockView.KEYPAD_HTML_ID] )
        self.assertIn( 'Incorrect PIN', replace_map[ConsoleUnlockView.KEYPAD_HTML_ID] )
        self.assertTrue( self.is_locked() )
        return

    def test_legacy_password_any_entry_unlocks( self ):
        self.set_stored_pin( 'hunter2' )
        self.set_locked( True )
        self.async_post( reverse( 'console_unlock' ), { 'pin': '0000' } )
        self.assertFalse( self.is_locked() )
        return


class TestConsoleUnlockThrottle( LockViewTestBase ):

    def setUp( self ):
        super().setUp()
        datetimeproxy.reset()
        self.addCleanup( datetimeproxy.reset )
        self.set_stored_pin( '1234' )
        self.set_locked( True )
        return

    def post_pin( self, pin ):
        return self.async_post( reverse( 'console_unlock' ), { 'pin': pin } )

    def keypad_html( self, response ):
        return response.json()['replace'][ConsoleUnlockView.KEYPAD_HTML_ID]

    def test_max_wrong_pins_disable_keypad( self ):
        for _ in range( UnlockThrottle.MAX_FAILURES - 1 ):
            self.assertResponseStatusCode( self.post_pin( '0000' ), 400 )
        response = self.post_pin( '0000' )
        self.assertResponseStatusCode( response, 429 )
        self.assertIn( f'data-disabled-secs="{UnlockThrottle.LOCKOUT_SECS}"', self.keypad_html( response ))
        return

    def test_correct_pin_refused_during_lockout( self ):
        for _ in range( UnlockThrottle.MAX_FAILURES ):
            self.post_pin( '0000' )
        response = self.post_pin( '1234' )
        self.assertResponseStatusCode( response, 429 )
        self.assertIn( 'data-disabled-secs=', self.keypad_html( response ))
        self.assertTrue( self.is_locked() )
        return

    def test_unlock_allowed_after_lockout_expires( self ):
        for _ in range( UnlockThrottle.MAX_FAILURES ):
            self.post_pin( '0000' )
        datetimeproxy.increment( seconds = UnlockThrottle.LOCKOUT_SECS )
        self.post_pin( '1234' )
        self.assertFalse( self.is_locked() )
        return

    def test_success_resets_failure_count( self ):
        for _ in range( UnlockThrottle.MAX_FAILURES - 1 ):
            self.post_pin( '0000' )
        self.post_pin( '1234' )
        self.set_locked( True )
        response = self.post_pin( '0000' )
        self.assertResponseStatusCode( response, 400 )
        return

    def test_unlock_prompt_shows_lockout( self ):
        for _ in range( UnlockThrottle.MAX_FAILURES ):
            self.post_pin( '0000' )
        response = self.async_get( reverse( 'console_unlock' ))
        self.assertIn( 'data-disabled-secs=', response.json()['modal'] )
        return


class TestConsoleUnlockModalProtection( DualModeViewTestCase ):
    """ Protected (not dismissible) only when it is the whole page. """

    def setUp( self ):
        super().setUp()
        session = self.client.session
        session[ConsoleConstants.CONSOLE_LOCKED_SESSION_VAR] = True
        session.save()
        return

    def test_full_page_load_is_protected( self ):
        response = self.client.get( reverse( 'console_unlock' ))
        content = response.content.decode()
        self.assertIn( 'data-modal-protected="true"', content )
        self.assertNotIn( 'id="modal_dismiss_x"', content )
        return

    def test_async_open_is_dismissible( self ):
        response = self.async_get( reverse( 'console_unlock' ))
        content = response.json()['modal']
        self.assertNotIn( 'data-modal-protected', content )
        self.assertIn( 'id="modal_dismiss_x"', content )
        return
