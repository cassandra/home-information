from typing import List, Tuple

from hi.apps.common.singleton import Singleton
from hi.apps.config.enums import Theme


class AttributeEnums( Singleton ):
    """
    For attributes of type AttributeValueType.ENUM.  There are some
    predefined common defaults, or can add others when modules are
    added.. This is needed so that the general attribute rendering
    templates can have access to them.

    TODO: Add some form of dynamic registration process to decouple
    this module from all the individual modules that need an enum type.
    """

    TIMEZONE_NAME_LIST = [
        'UTC',
        'America/New_York',
        'America/Chicago',
        'America/Denver',
        'America/Los_Angeles',
        'America/Toronto',
        'America/Mexico_City',
        'America/Sao_Paulo',
        'Europe/London',
        'Europe/Berlin',
        'Europe/Paris',
        'Europe/Moscow',
        'Asia/Dubai',
        'Asia/Tokyo',
        'Asia/Seoul',
        'Asia/Shanghai',
        'Asia/Hong_Kong',
        'Asia/Singapore',
        'Asia/Kolkata',
        'Asia/Jakarta',
        'Australia/Sydney',
        'Australia/Melbourne',
        'Africa/Johannesburg',
        'Africa/Lagos',
        'Africa/Cairo',
        'America/Argentina/Buenos_Aires',
    ]
    
    def __init_singleton__( self ):
        self._enum_name_to_choices = dict()
        self._enum_name_to_choices['Timezone'] = [ ( x, x ) for x in self.TIMEZONE_NAME_LIST ]
        self._enum_name_to_choices['Theme'] = Theme.choices()
        return

    @property
    def attribute_enums_map(self) -> List[ Tuple[ str, str ] ]:
        return self._enum_name_to_choices
