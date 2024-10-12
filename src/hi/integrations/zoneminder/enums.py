from hi.apps.common.enums import LabeledEnum

from hi.apps.attribute.enums import AttributeValueType


class ZmAttributeName(LabeledEnum):

    def __init__( self,
                  label        : str,
                  description  : str,
                  value_type   : AttributeValueType,
                  is_editable  : bool,
                  is_required  : bool ):
        super().__init__( label, description )
        self.value_type = value_type
        self.is_editable = is_editable
        self.is_required = is_required
        return

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
