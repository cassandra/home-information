from hi.apps.common.enums import LabeledEnum

from hi.apps.attribute.enums import AttributeValueType
from hi.integrations.core.enums import IntegrationAttributeType


class ZmAttributeType( IntegrationAttributeType ):

    API_URL = (
        'API URL',
        'e.g., https://myserver:8443/zm/api',
        AttributeValueType.LINK,
        True,
        True,
    )
    PORTAL_URL = (
        'Portal URL',
        'e.g., https://myserver:8443/zm',
        AttributeValueType.LINK,
        True,
        True,
    )
    API_USER = (
        'Username',
        '',
        AttributeValueType.STRING,
        True,
        True,
    )
    API_PASSWORD = (
        'Password',
        '',
        AttributeValueType.PASSWORD,
        True,
        True,
    )
    

class ZmMonitorState(LabeledEnum):

    NONE      = ( 'None', '' )
    MONITOR   = ( 'Monitor', '' )
    MODECT    = ( 'Modect', '' )
    RECORD    = ( 'Record', '' )
    MOCORD    = ( 'Mocord', '' )
    NODECT    = ( 'Nodect', '' )
