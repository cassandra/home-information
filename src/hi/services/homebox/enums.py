from hi.apps.attribute.enums import AttributeValueType

from hi.integrations.enums import IntegrationAttributeType

from .constants import HbTimeouts


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
    INCLUDE_FILTER = (
        'Include Items By Location/Tag',
        'One location or tag name per line.',
        AttributeValueType.TEXT,
        None,
        True,
        False,
    )
    EXCLUDE_FILTER = (
        'Exclude Items By Location/Tag',
        'One location or tag name per line.',
        AttributeValueType.TEXT,
        None,
        True,
        False,
    )
    POLLING_INTERVAL_SECS = (
        'Polling Interval (seconds)',
        'How often the monitor probes HomeBox for reachability. Lower '
        'values produce a faster signal when the API goes down but '
        'increase background API load; HomeBox is inventory data, so '
        'longer intervals are usually appropriate.',
        AttributeValueType.INTEGER,
        [ 1, 86400 ],   # 1 second to 24 hours
        True,
        True,
        str( HbTimeouts.POLLING_INTERVAL_SECS ),
    )
