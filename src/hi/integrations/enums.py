from typing import Dict

from hi.apps.attribute.enums import AttributeValueType
from hi.apps.common.enums import LabeledEnum


class IntegrationAttributeType(LabeledEnum):
    """ Abstract base class for integrations ot define the required attributes they need. """
    
    def __init__( self,
                  label             : str,
                  description       : str,
                  value_type        : AttributeValueType,
                  value_range_dict  : Dict[ str, str ],
                  is_editable       : bool,
                  is_required       : bool,
                  initial_value     : str                = '' ):
        super().__init__( label, description )
        self.value_type = value_type
        self.value_range_dict = value_range_dict
        self.is_editable = is_editable
        self.is_required = is_required
        self.initial_value = initial_value
        return
    
