from hi.apps.attribute.enums import AttributeValueType
from hi.integrations.core.enums import IntegrationAttributeType


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

    
class HassStateValue:

    ON = 'on'
    OFF = 'off'
