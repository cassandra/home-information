from hi.apps.attribute.enums import AttributeValueType

from hi.integrations.enums import IntegrationAttributeType


class HbAttributeType( IntegrationAttributeType ):

    API_URL = (
        'API URL',
        'e.g., https://myserver:8443/hb/api',
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
