from hi.apps.attribute.enums import AttributeValueType
from hi.integrations.enums import IntegrationAttributeType


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
    IMPORT_ALLOWLIST = (
        'Allowed Item Types',
        'HA domains and device classes to import (one per line). '
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


class HassStateValue:

    ON = 'on'
    OFF = 'off'
