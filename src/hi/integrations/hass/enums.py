from hi.apps.attribute.enums import AttributeValueType
from hi.integrations.core.enums import IntegrationAttributeType


class HassAttributeType( IntegrationAttributeType ):

    API_BASE_URL = (
        'Server URL',
        'e.g., https://myhassserver:8123',
        AttributeValueType.TEXT,
        True,
        True,
    )
    API_TOKEN = (
        'API Token',
        '',
        AttributeValueType.TEXT,
        True,
        True,
    )
