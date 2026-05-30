from hi.apps.attribute.enums import AttributeValueType

from hi.integrations.enums import IntegrationAttributeType


class ImAttributeType( IntegrationAttributeType ):

    API_URL = (
        'API URL',
        'e.g., https://immich.example.com/',
        AttributeValueType.TEXT,
        None,
        True,
        True,
    )
    API_KEY = (
        'API Key',
        'Immich API key sent as x-api-key on every request. Create '
        'one in the Immich web UI under Account Settings → API Keys '
        'with at least the asset.read permission.',
        AttributeValueType.SECRET,
        None,
        True,
        True,
    )
