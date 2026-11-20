from dataclasses import dataclass


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

    def is_valid( self, value : str ) -> bool:
        if not isinstance( value, str ):
            return False
        if len( value ) != self.length:
            return False
        return all( c in self.alphabet for c in value )
