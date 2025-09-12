from hi.apps.common.enums import LabeledEnum


class ProfileType( LabeledEnum ):

    SINGLE_STORY  = ( 'Single Story', '' )
    TWO_STORY     = ( 'Two Story', '' )
    APARTMENT     = ( 'Apartment', '' )

    @classmethod
    def default(cls):
        return cls.SINGLE_STORY

    def json_filename(self):
        return f'profile_{self}.json'
    
