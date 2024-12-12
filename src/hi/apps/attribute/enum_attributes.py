from typing import List, Tuple

from hi.apps.console.audio_file import AudioFile
from hi.apps.console.enums import Theme
from hi.apps.security.enums import SecurityState

from hi.constants import TIME_OF_DAY_CHOICES, TIMEZONE_NAME_LIST


class PredefinedEnumAttributes:
    """
    For attributes of type AttributeValueType.ENUM.  There are some
    predefined common defaults that can be used.  Instead of putting all
    the possible choices in the 'value_range_str' field of an Attribute,
    you can include a well-known identifier and the values will come from
    this module.

    This is also needed for enumerations that might change in future
    releases where we do not want to have to update the user database.
    """

    TIMEZONE_CHOICES_ID = 'hi.timezone'
    THEME_CHOICES_ID = 'hi.theme'
    AUDIO_FILE_CHOICES_ID = 'hi.audio.file'
    TIME_OF_DAY_CHOICES_ID = 'hi.datetime.time-of-day'
    SECURITY_STATE_CHOICES_ID = 'hi.security.state'
    
    ID_TO_CHOICES = {
        TIME_OF_DAY_CHOICES_ID: TIME_OF_DAY_CHOICES,
        TIMEZONE_CHOICES_ID: [ ( x, x ) for x in TIMEZONE_NAME_LIST ],
        THEME_CHOICES_ID: Theme.choices(),
        AUDIO_FILE_CHOICES_ID: AudioFile.choices(),
        SECURITY_STATE_CHOICES_ID: SecurityState.choices(),
    }
    
    @classmethod
    def get_choices( cls, choices_id : str ) -> List[ Tuple[ str, str ] ]:
        return cls.ID_TO_CHOICES.get( choices_id )
    
