from typing import List, Tuple

from hi.apps.config.enums import Theme

from hi.constants import TIMEZONE_NAME_LIST


class AttributeEnums:
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
    
    ID_TO_CHOICES = {
        TIMEZONE_CHOICES_ID: [ ( x, x ) for x in TIMEZONE_NAME_LIST ],
        THEME_CHOICES_ID: Theme.choices(),
    }
    
    @classmethod
    def get_choices( cls, choices_id : str ) -> List[ Tuple[ str, str ] ]:
        return cls.ID_TO_CHOICES.get( choices_id )
    
