from hi.apps.attribute.enums import AttributeValueType
from hi.apps.common.enums import LabeledEnum


class IntegrationAttributeType(LabeledEnum):
    """ Abstract base class for integrations ot define the required attributes they need. """
    
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
