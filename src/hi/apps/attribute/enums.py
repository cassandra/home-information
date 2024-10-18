from hi.apps.common.enums import LabeledEnum


class AttributeType(LabeledEnum):

    PREDEFINED  = ('Predefined', '' )
    CUSTOM = ('Custom', '' )

    
class AttributeValueType(LabeledEnum):

    TEXT      = ('Text', '' )
    FILE      = ('File', '' )  # relative filename of MEDIA_ROOT
    SECRET    = ('Secret', '' )

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
    
