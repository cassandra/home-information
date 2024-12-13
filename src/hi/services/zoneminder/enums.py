from hi.apps.attribute.enums import AttributeValueType
from hi.apps.common.enums import LabeledEnum

from hi.integrations.enums import IntegrationAttributeType

from hi.constants import TIMEZONE_NAME_LIST


class ZmAttributeType( IntegrationAttributeType ):

    API_URL = (
        'API URL',
        'e.g., https://myserver:8443/zm/api',
        AttributeValueType.TEXT,
        None,
        True,
        True,
    )
    PORTAL_URL = (
        'Portal URL',
        'e.g., https://myserver:8443/zm',
        AttributeValueType.TEXT,
        None,
        True,
        True,
    )
    API_USER = (
        'Username',
        '',
        AttributeValueType.TEXT,
        None,
        True,
        True,
    )
    API_PASSWORD = (
        'Password',
        '',
        AttributeValueType.SECRET,
        None,
        True,
        True,
    )
    TIMEZONE = (
        'Timezone',
        '',
        AttributeValueType.ENUM,
        { x: x for x in TIMEZONE_NAME_LIST },
        True,
        True,
        'America/Chicago',
    )
    ADD_ALARM_EVENTS = (
        'Add Alarm Events',
        '',
        AttributeValueType.BOOLEAN,
        None,
        True,
        False,
        True,
    )
    

class ZmMonitorFunction(LabeledEnum):

    NONE      = ( 'None', '' )
    MONITOR   = ( 'Monitor', '' )
    MODECT    = ( 'Modect', '' )
    RECORD    = ( 'Record', '' )
    MOCORD    = ( 'Mocord', '' )
    NODECT    = ( 'Nodect', '' )
