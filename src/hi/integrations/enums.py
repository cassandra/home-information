from typing import Dict

from hi.apps.attribute.enums import AttributeValueType
from hi.apps.common.enums import LabeledEnum


class IntegrationAttributeType( LabeledEnum ):
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

    
class IntegrationHealthStatusType( LabeledEnum ):

    HEALTHY            = ( 'Healthy', '' )
    CONFIG_ERROR       = ( 'Config Error', '' )
    CONNECTION_ERROR   = ( 'Connection Error', '' )
    TEMPORARY_ERROR    = ( 'Temporary Error', '' )
    DISABLED           = ( 'Disabled', '' )
    UNKNOWN            = ( 'Unknown', '' )

    @property
    def is_error(self) -> bool:
        return self in (
            IntegrationHealthStatusType.CONFIG_ERROR,
            IntegrationHealthStatusType.CONNECTION_ERROR,
            IntegrationHealthStatusType.TEMPORARY_ERROR
        )

    @property
    def is_critical(self) -> bool:
        return self in (
            IntegrationHealthStatusType.CONFIG_ERROR,
            IntegrationHealthStatusType.CONNECTION_ERROR
        )


