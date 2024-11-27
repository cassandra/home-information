from hi.apps.common.enums import LabeledEnum


class AttributeType(LabeledEnum):

    PREDEFINED  = ('Predefined', '' )
    CUSTOM = ('Custom', '' )

    @property
    def can_delete(self):
        return bool( self == AttributeType.CUSTOM )

    
class AttributeValueType(LabeledEnum):

    TEXT      = ('Text'     , '' )
    FILE      = ('File'     , '' )  # relative filename of MEDIA_ROOT
    SECRET    = ('Secret'   , '' )
    TIMEZONE  = ('Timezone' , '' , 'America/Chicago' )

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
    def is_timezone(self):
        return bool( self == AttributeValueType.TIMEZONE )
    
    def __init__( self,
                  label           : str,
                  description     : str,
                  initial_value   : str  = '' ):
        super().__init__( label, description )
        self.initial_value = initial_value
        return
