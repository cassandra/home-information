from typing import Dict, FrozenSet, Optional

from hi.apps.attribute.enums import AttributeValueType
from hi.apps.common.enums import LabeledEnum


class IntegrationCapability( LabeledEnum ):

    CONNECT = ( 'Connect', 'Live mirror of an upstream system.' )
    IMPORT = ( 'Import', 'One-shot pull of upstream items into HI.' )


ALL_CAPABILITIES = frozenset( IntegrationCapability )


class IntegrationDisableMode( LabeledEnum ):
    """
    Mode used when removing (disabling) an integration. Controls how the
    integration's attached entities are handled.

    SAFE — delete entities without user-created data; preserve entities with
    user-created data by detaching them from the integration (strips
    integration association, removes integration-only components, records
    the previous integration identity to drive the "From ..." UI
    badge and the auto-reconnect path). This mirrors the sync-time
    preservation behavior.

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
                  initial_value     : str                                              = '',
                  capabilities      : Optional[ FrozenSet[ IntegrationCapability ] ]   = None ):
        super().__init__( label, description )
        self.value_type = value_type
        self.value_range_dict = value_range_dict
        self.is_editable = is_editable
        self.is_required = is_required
        self.initial_value = initial_value
        self.capabilities = capabilities if capabilities is not None else ALL_CAPABILITIES
        return
