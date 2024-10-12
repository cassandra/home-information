from hi.apps.common.enums import LabeledEnum

from hi.apps.attribute.enums import AttributeValueType


class HassAttributeName(LabeledEnum):

    def __init__( self,
                  label        : str,
                  description  : str,
                  value_type   : AttributeValueType,
                  is_editable  : bool,
                  is_required  : bool ):
        super().__init__( label, description )
        self.value_type = value_type,
        self.is_editable = is_editable
        self.is_required = is_required
        return

    API_BASE_URL = (
        ' URL',
        'e.g., https://myhassserver:8123',
        AttributeValueType.STRING,
        True,
        True,
    )
    API_TOKEN = (
        'API Token',
        '',
        AttributeValueType.STRING,
        True,
        True,
    )

    
