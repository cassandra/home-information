from hi.apps.attribute.enums import AttributeValueType

from hi.integrations.enums import IntegrationAttributeType


class PlAttributeType( IntegrationAttributeType ):
    """Operator-configurable settings for the paperless integration.

    Two required fields drive the entire EXTERNAL_REFERENCE surface:
    the base URL of the paperless server (used by the referencer's
    HTTP client and by the thumbnail proxy) and the API token sent
    as ``Authorization: Token <value>`` on every upstream call.
    """

    API_URL = (
        'API URL',
        'e.g., https://paperless.example.com/',
        AttributeValueType.TEXT,
        None,
        True,
        True,
    )
    API_TOKEN = (
        'API Token',
        'Paperless token sent as Authorization: Token <value>.',
        AttributeValueType.SECRET,
        None,
        True,
        True,
    )
