from hi.apps.common.enums import LabeledEnum

from hi.integrations.core.enums import PropertyValueType


class ZmPropertyName(LabeledEnum):

    def __init__( self,
                  label          : str,
                  description    : str,
                  value_type     : PropertyValueType,
                  is_editable    : bool,
                  is_required    : bool ):
        super().__init__( label, description )
        self.is_editable = is_editable
        self.is_required = is_required
        return

    API_URL = (
        'API URL',
        'e.g., https://myserver:8443/zm/api',
        PropertyValueType.STRING,
        True,
        True,
    )
    PORTAL_URL = (
        'Portal URL',
        'e.g., https://myserver:8443/zm',
        PropertyValueType.STRING,
        True,
        True,
    )
    API_USER = (
        'Username',
        '',
        PropertyValueType.STRING,
        True,
        True,
    )
    API_PASSWORD = (
        'Password',
        '',
        PropertyValueType.STRING,
        True,
        True,
    )


class ZmAttributeName(LabeledEnum):

    ZM_MONITOR_ID = ( 'ZM Monitor Id', '' )

    
class ZmMonitorState(LabeledEnum):

    NONE      = ( 'None', '' )
    MONITOR   = ( 'Monitor', '' )
    MODECT    = ( 'Modect', '' )
    RECORD    = ( 'Record', '' )
    MOCORD    = ( 'Mocord', '' )
    NODECT    = ( 'Nodect', '' )
