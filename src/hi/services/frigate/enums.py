from hi.apps.attribute.enums import AttributeValueType

from hi.integrations.enums import IntegrationAttributeType


class FrigateAttributeType( IntegrationAttributeType ):
    """Operator-configurable settings for the Frigate integration.

    v1 assumes Frigate is reachable directly (or behind an operator-managed
    reverse proxy that handles auth). The optional ``AUTH_HEADER`` slot is a
    stretch for installs that gate Frigate behind basic-auth / a static
    bearer token; JWT login is out of v1 scope and will be revisited once
    we have real-install validation.
    """

    BASE_URL = (
        'Base URL',
        'e.g., http://frigate.local:5000',
        AttributeValueType.TEXT,
        None,
        True,
        True,
    )
    AUTH_HEADER = (
        'Authorization Header',
        'Optional. Verbatim Authorization header value (e.g., '
        '"Bearer xyz" or "Basic <base64>"). Leave blank for unauthenticated '
        'access or when auth is handled by a reverse proxy.',
        AttributeValueType.SECRET,
        None,
        False,
        False,
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
