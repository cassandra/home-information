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
    FILE      = ('File', '', True )  # relative filename of MEDIA_ROOT
    SECRET    = ('Secret', '' )

    @classmethod
    def default(cls):
        return cls.TEXT
