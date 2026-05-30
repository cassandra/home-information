from hi.apps.attribute.enums import AttributeValueType

from hi.integrations.enums import IntegrationAttributeType

from hi.constants import TIMEZONE_NAME_LIST

from .constants import ZmTimeouts


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
    POLLING_INTERVAL_SECS = (
        'Polling Interval (seconds)',
        'How often the monitor polls ZoneMinder for new events. Lower '
        'values are more responsive but increase API load on the '
        'ZoneMinder server.',
        AttributeValueType.INTEGER,
        [ 1, 86400 ],   # 1 second to 24 hours
        True,
        True,
        str( ZmTimeouts.POLLING_INTERVAL_SECS ),
    )
