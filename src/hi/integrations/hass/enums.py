from hi.apps.common.enums import LabeledEnum

from hi.integrations.core.enums import PropertyValueType


class HassPropertyName(LabeledEnum):

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

    API_BASE_URL = (
        ' URL',
        'e.g., https://myhassserver:8123',
        PropertyValueType.STRING,
        True,
        True,
    )
    API_TOKEN = (
        'API Token',
        '',
        PropertyValueType.STRING,
        True,
        True,
    )

    
class HassAttributeName(LabeledEnum):

    HASS_ENTITY_ID = ( 'HAss Entity Id', '' )
