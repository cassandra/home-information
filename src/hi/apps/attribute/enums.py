from hi.apps.common.enums import LabeledEnum


class AttributeType(LabeledEnum):

    PREDEFINED  = ('Predefined', '' )
    CUSTOM = ('Custom', '' )

    
class AttributeValueType(LabeledEnum):

    def __init__( self,
                  label        : str,
                  description  : str,
                  is_file      : bool    = False ):
        super().__init__( label, description )
        self.is_file = is_file
        return
    
    TEXT      = ('Text', '' )
    STRING    = ('String', '' )
    PDF       = ('PDF', '', True )  # relative filename of MEDIA_ROOT
    IMAGE     = ('Image', '', True )  # relative filename of MEDIA_ROOT
    VIDEO     = ('Video', '', True )  # relative filename of MEDIA_ROOT
    AUDIO     = ('Audio', '', True )  # relative filename of MEDIA_ROOT
    FILE      = ('File', '', True )  # relative filename of MEDIA_ROOT
    DATETIME  = ('DateTime', '' )
    DATE      = ('Date', '' )
    LINK      = ('Link', '' )
    PASSWORD  = ('Password', '' )
    EMAIL     = ('Email', '' )
    PHONE     = ('Phone', '' )
    INTEGER   = ('Integer', '' )
    FLOAT     = ('Float', '' )
    BOOLEAN   = ('Boolean', '' )
    TIME      = ('Time', '' )
    JSON      = ('JSON', '' )

    @classmethod
    def default(cls):
        return cls.TEXT
