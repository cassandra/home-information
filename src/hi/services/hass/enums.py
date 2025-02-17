from hi.apps.attribute.enums import AttributeValueType
from hi.integrations.enums import IntegrationAttributeType


class HassAttributeType( IntegrationAttributeType ):

    API_BASE_URL = (
        'Server URL',
        'e.g., https://myhassserver:8123',
        AttributeValueType.TEXT,
        None,
        True,
        True,
    )
    API_TOKEN = (
        'API Token',
        '',
        AttributeValueType.TEXT,
        None,
        True,
        True,
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

    
class HassStateValue:

    ON = 'on'
    OFF = 'off'
