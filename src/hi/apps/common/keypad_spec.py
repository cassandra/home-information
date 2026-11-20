from dataclasses import dataclass
from enum import Enum
from typing import List, Optional


class KeypadAction( Enum ):
    # external_name is what the keypad JS dispatches on.
    CLEAR      = ( 'clear', 'Clear', 'Clear' )
    BACKSPACE  = ( 'backspace', 'Backspace', '\u232b' )

    def __init__( self, external_name : str, label : str, glyph : str ):
        self.external_name = external_name
        self.label = label
        self.glyph = glyph
        return


@dataclass( frozen = True )
class KeypadCell:
    """ One keypad grid cell: either a character key or an action key. """

    span        : int
    key         : Optional[ str ]           = None
    action      : Optional[ KeypadAction ]  = None
    starts_row  : bool                      = False


@dataclass( frozen = True )
class KeypadSpec:
    """
    Describes a fixed-length, fixed-alphabet code entered with the
    on-screen keypad. The alphabet is both the set of valid characters
    and the order the keys are laid out in.
    """

    alphabet     : str
    length       : int
    columns      : int
    auto_submit  : bool = True
    masked       : bool = True

    def __post_init__( self ):
        # Two columns are the minimum to fit CLEAR and BACKSPACE.
        if self.columns < 2:
            raise ValueError( 'KeypadSpec needs at least 2 columns.' )
        if len( set( self.alphabet )) != len( self.alphabet ):
            raise ValueError( 'KeypadSpec alphabet has duplicate characters.' )
        return

    def is_valid( self, value : str ) -> bool:
        if not isinstance( value, str ):
            return False
        if len( value ) != self.length:
            return False
        return all( c in self.alphabet for c in value )

    @property
    def slot_indexes( self ) -> range:
        return range( self.length )

    @property
    def cells( self ) -> List[ KeypadCell ]:
        """
        Keys fill rows of ``columns`` in alphabet order. The last row is
        CLEAR, any leftover keys, then BACKSPACE, with the two actions
        sharing the free columns. If fewer than two columns are free, the
        leftover keys keep their own row and the actions get a new one.
        """
        leftover_count = len( self.alphabet ) % self.columns
        free_columns = self.columns - leftover_count
        if free_columns < 2:
            free_columns = self.columns
            last_row_keys = ''
            grid_keys = self.alphabet
        else:
            split_index = len( self.alphabet ) - leftover_count
            grid_keys = self.alphabet[ :split_index ]
            last_row_keys = self.alphabet[ split_index: ]

        clear_span = free_columns // 2
        backspace_span = free_columns - clear_span

        cells = [ KeypadCell( span = 1, key = c ) for c in grid_keys ]
        cells.append( KeypadCell( span = clear_span, action = KeypadAction.CLEAR, starts_row = True ))
        cells.extend( KeypadCell( span = 1, key = c ) for c in last_row_keys )
        cells.append( KeypadCell( span = backspace_span, action = KeypadAction.BACKSPACE ))
        return cells


@dataclass( frozen = True )
class KeypadField:
    """ One code field filled by the keypad; ``name`` is the POST key. """

    name   : str
    label  : Optional[ str ] = None


@dataclass( frozen = True )
class KeypadEntry:
    """
    Everything the keypad entry template include needs. Fields fill in
    order; with ``auto_submit`` the form submits when the last is full.
    """

    spec           : KeypadSpec
    fields         : List[ KeypadField ]
    error_message  : Optional[ str ] = None
    # Set when the server re-renders the entry in place (antinode replace).
    html_id        : Optional[ str ] = None
    # Seconds the keypad refuses input (e.g., too many wrong attempts).
    disabled_secs  : int = 0
