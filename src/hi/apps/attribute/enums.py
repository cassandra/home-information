from hi.apps.common.enums import LabeledEnum


class AttributeType(LabeledEnum):

    PREDEFINED  = ('Predefined', '' )
    CUSTOM = ('Custom', '' )

    @property
    def can_delete(self):
        return bool( self == AttributeType.CUSTOM )

    
class AttributeValueType(LabeledEnum):

    TEXT        = ('Text'     , '' )
    FILE        = ('File'     , '' )  # relative filename of MEDIA_ROOT
    SECRET      = ('Secret'   , '' )
    ENUM        = ('Enum'     , '' )
    BOOLEAN     = ('Boolean'  , '' )
    INTEGER     = ('Integer'  , '' )
    
    @classmethod
    def default(cls):
        return cls.TEXT

    @property
    def is_file(self):
        return bool( self == AttributeValueType.FILE )

    @property
    def is_text(self):
        return bool( self == AttributeValueType.TEXT )

    @property
    def is_secret(self):
        return bool( self == AttributeValueType.SECRET )

    @property
    def is_enum(self):
        return bool( self == AttributeValueType.ENUM )

    @property
    def is_integer(self):
        return bool( self == AttributeValueType.INTEGER )

    @property
    def is_boolean(self):
        return bool( self == AttributeValueType.BOOLEAN )
