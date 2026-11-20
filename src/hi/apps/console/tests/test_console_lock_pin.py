import logging
from unittest.mock import Mock, patch

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from hi.apps.console.console_helper import ConsoleSettingsHelper
from hi.apps.console.settings import validate_lock_pin

logging.disable( logging.CRITICAL )


class TestConsoleLockPinLookup( SimpleTestCase ):

    def _helper_with_stored_value( self, value ):
        settings_manager = Mock()
        settings_manager.get_setting_value.return_value = value
        helper = ConsoleSettingsHelper()
        patcher = patch.object( helper, 'settings_manager', return_value = settings_manager )
        patcher.start()
        self.addCleanup( patcher.stop )
        return helper, settings_manager

    def test_valid_stored_pin_is_returned( self ):
        helper, _ = self._helper_with_stored_value( '0429' )
        self.assertEqual( helper.get_console_lock_pin(), '0429' )
        return

    def test_legacy_password_is_treated_as_unset( self ):
        helper, _ = self._helper_with_stored_value( 'hunter2' )
        self.assertIsNone( helper.get_console_lock_pin() )
        return

    def test_blank_is_treated_as_unset( self ):
        helper, _ = self._helper_with_stored_value( '' )
        self.assertIsNone( helper.get_console_lock_pin() )
        return

    def test_set_rejects_invalid_pin( self ):
        helper, settings_manager = self._helper_with_stored_value( '' )
        with self.assertRaises( ValueError ):
            helper.set_console_lock_pin( pin = '12a4' )
        settings_manager.set_setting_value.assert_not_called()
        return


class TestValidateLockPin( SimpleTestCase ):

    def test_blank_and_valid_pin_accepted( self ):
        validate_lock_pin( '' )
        validate_lock_pin( '1234' )
        return

    def test_invalid_values_rejected( self ):
        for value in [ '12a', '123', '12345', 'hunter2' ]:
            with self.subTest( value = value ):
                with self.assertRaises( ValidationError ):
                    validate_lock_pin( value )
        return
