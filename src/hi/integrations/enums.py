from typing import Dict

from hi.apps.attribute.enums import AttributeValueType
from hi.apps.common.enums import LabeledEnum


class IntegrationDisableMode( LabeledEnum ):
    """
    Mode used when removing (disabling) an integration. Controls how the
    integration's attached entities are handled.

    SAFE — delete entities without user-created data; preserve entities with
    user-created data by disconnecting them (strips integration association,
    removes integration-only components, applies '[Disconnected]' name
    prefix). This mirrors the sync-time preservation behavior.

    ALL  — hard-delete all entities attached to the integration regardless of
    user-created data.
    """

    SAFE = ( 'Delete Safe',
             'Delete entities without user data; preserve those with user data' )
    ALL  = ( 'Delete All',
             'Hard-delete all entities regardless of user data' )

    @classmethod
    def default(cls):
        return cls.SAFE


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
