import logging

from django.test import SimpleTestCase

from hi.apps.common.keypad_spec import KeypadAction, KeypadSpec

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


class TestKeypadSpecCells( SimpleTestCase ):

    def _describe( self, spec ):
        """ Compact form: key char, 'C'/'B' for actions, with span and row start. """
        result = []
        for cell in spec.cells:
            if cell.key:
                result.append( cell.key )
            else:
                label = 'C' if cell.action == KeypadAction.CLEAR else 'B'
                result.append( f'{label}{cell.span}{"^" if cell.starts_row else ""}' )
        return result

    def test_one_leftover_key_sits_between_actions( self ):
        spec = KeypadSpec( alphabet = '1234567890', length = 4, columns = 3 )
        self.assertEqual( self._describe( spec ),
                          list( '123456789' ) + [ 'C1^', '0', 'B1' ] )
        return

    def test_full_rows_split_last_row_between_actions( self ):
        spec = KeypadSpec( alphabet = 'abcdefhkpqrstwxy', length = 6, columns = 4 )
        self.assertEqual( self._describe( spec ),
                          list( 'abcdefhkpqrstwxy' ) + [ 'C2^', 'B2' ] )
        return

    def test_full_rows_with_odd_columns_give_backspace_the_extra( self ):
        spec = KeypadSpec( alphabet = '123456789', length = 4, columns = 3 )
        self.assertEqual( self._describe( spec ),
                          list( '123456789' ) + [ 'C1^', 'B2' ] )
        return

    def test_actions_get_own_row_when_one_column_is_free( self ):
        spec = KeypadSpec( alphabet = '1234567890a', length = 4, columns = 3 )
        self.assertEqual( self._describe( spec ),
                          list( '1234567890a' ) + [ 'C1^', 'B2' ] )
        return

    def test_invalid_specs_rejected( self ):
        with self.assertRaises( ValueError ):
            KeypadSpec( alphabet = '12', length = 4, columns = 1 )
        with self.assertRaises( ValueError ):
            KeypadSpec( alphabet = '112', length = 4, columns = 3 )
        return
