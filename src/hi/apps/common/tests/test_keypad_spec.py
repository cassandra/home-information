import logging

from django.test import SimpleTestCase

from hi.apps.common.keypad_spec import KeypadSpec

logging.disable( logging.CRITICAL )


class TestKeypadSpecIsValid( SimpleTestCase ):

    def setUp( self ):
        self.spec = KeypadSpec( alphabet = '1234567890', length = 4, columns = 3 )
        return

    def test_exact_length_in_alphabet_is_valid( self ):
        self.assertTrue( self.spec.is_valid( '0429' ) )
        return

    def test_wrong_length_is_invalid( self ):
        self.assertFalse( self.spec.is_valid( '123' ) )
        self.assertFalse( self.spec.is_valid( '12345' ) )
        self.assertFalse( self.spec.is_valid( '' ) )
        return

    def test_character_outside_alphabet_is_invalid( self ):
        self.assertFalse( self.spec.is_valid( '12a4' ) )
        self.assertFalse( self.spec.is_valid( '12 4' ) )
        return

    def test_non_string_is_invalid( self ):
        self.assertFalse( self.spec.is_valid( None ) )
        self.assertFalse( self.spec.is_valid( 1234 ) )
        return
