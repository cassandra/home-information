from hi.apps.attribute.enums import AttributeValueType
from hi.integrations.enums import IntegrationAttributeType

from .constants import HassTimeouts


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
    INCLUDE_FILTER = (
        'Allowed Item Types',
        'HA domains and device classes to include (one per line). '
        'Use "domain" for all classes, or "domain:class" for specific ones.',
        AttributeValueType.TEXT,
        None,
        True,
        False,
        'binary_sensor\n'
        'camera\n'
        'climate\n'
        'cover\n'
        'fan\n'
        'light\n'
        'lock\n'
        'media_player\n'
        'sensor\n'
        'switch',
    )
    POLLING_INTERVAL_SECS = (
        'Polling Interval (seconds)',
        'How often the monitor polls Home Assistant for state changes. '
        'Lower values are more responsive but increase API load on the '
        'Home Assistant server.',
        AttributeValueType.INTEGER,
        [ 1, 86400 ],   # 1 second to 24 hours
        True,
        True,
        str( HassTimeouts.POLLING_INTERVAL_SECS ),
    )


class HassStateValue:

    ON = 'on'
    OFF = 'off'
    LOCKED = 'locked'
    UNLOCKED = 'unlocked'
    OPEN = 'open'
    CLOSED = 'closed'
    OPENING = 'opening'
    CLOSING = 'closing'

    # Special states HA emits when an entity is offline or
    # hasn't reported yet. Treat as "no value" at the boundary
    # so they don't pollute sensor history with placeholder
    # strings that would later display as labels.
    UNKNOWN = 'unknown'
    UNAVAILABLE = 'unavailable'

    NO_VALUE_STATES = frozenset({ UNKNOWN, UNAVAILABLE })
