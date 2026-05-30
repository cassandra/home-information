from hi.apps.attribute.enums import AttributeValueType

from hi.integrations.enums import IntegrationAttributeType

from .constants import FrigateTimeouts


class FrigateAttributeType( IntegrationAttributeType ):

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
        'Optional. Sent verbatim as the Authorization header '
        '(e.g., "Basic <base64>" or "Bearer <token>").',
        AttributeValueType.SECRET,
        None,
        True,
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
    POLLING_INTERVAL_SECS = (
        'Polling Interval (seconds)',
        'How often the monitor polls Frigate for new events. Lower '
        'values are more responsive but increase API load on the '
        'Frigate server.',
        AttributeValueType.INTEGER,
        [ 1, 86400 ],   # 1 second to 24 hours
        True,
        True,
        str( FrigateTimeouts.POLLING_INTERVAL_SECS ),
    )
