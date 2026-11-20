import logging

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from hi.apps.config.settings_manager import SettingsManager
from hi.apps.console.console_helper import ConsoleSettingsHelper
from hi.apps.console.settings import ConsoleSetting, validate_lock_pin
from hi.testing.base_test_case import BaseTestCase

logging.disable( logging.CRITICAL )


class TestConsoleLockPinLookup( BaseTestCase ):

    def setUp( self ):
        super().setUp()
        # Fresh singletons: the helper caches its settings manager.
        for singleton_class in ( SettingsManager, ConsoleSettingsHelper ):
            singleton_class._instance = None
            self.addCleanup( setattr, singleton_class, '_instance', None )
        return

    def _store( self, value ):
        SettingsManager().set_setting_value( ConsoleSetting.CONSOLE_LOCK_PASSWORD, value )
        return

    def test_valid_stored_pin_is_returned( self ):
        self._store( '0429' )
        self.assertEqual( ConsoleSettingsHelper().get_console_lock_pin(), '0429' )
        return

    def test_legacy_password_is_treated_as_unset( self ):
        self._store( 'hunter2' )
        self.assertIsNone( ConsoleSettingsHelper().get_console_lock_pin() )
        return

    def test_blank_is_treated_as_unset( self ):
        self._store( '' )
        self.assertIsNone( ConsoleSettingsHelper().get_console_lock_pin() )
        return

    def test_set_rejects_invalid_pin( self ):
        self._store( '0429' )
        with self.assertRaises( ValueError ):
            ConsoleSettingsHelper().set_console_lock_pin( pin = '12a4' )
        self.assertEqual( ConsoleSettingsHelper().get_console_lock_pin(), '0429' )
        return


class TestValidateLockPin( SimpleTestCase ):

    def test_blank_and_valid_pin_accepted( self ):
        validate_lock_pin( '' )
        validate_lock_pin( '1234' )
        return

    def test_invalid_value_rejected( self ):
        with self.assertRaises( ValidationError ):
            validate_lock_pin( 'hunter2' )
        return
