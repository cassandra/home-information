from typing import Dict, FrozenSet, List, Optional, Union

from hi.apps.attribute.enums import AttributeValueType
from hi.apps.common.enums import LabeledEnum


class IntegrationCapability( LabeledEnum ):

    CONNECT = ( 'Connect', 'Live mirror of an upstream system.' )
    IMPORT = ( 'Import', 'One-shot pull of upstream items into HI.' )
    EXTERNAL_REFERENCE = (
        'External Reference',
        'Search-and-attach external documents/photos as Entity/Location external references.',
    )


ALL_CAPABILITIES = frozenset( IntegrationCapability )


class IntegrationDisableMode( LabeledEnum ):

    SAFE = ( 'Delete Safe',
             'Delete entities without user data; preserve those with user data' )
    ALL  = ( 'Delete All',
             'Hard-delete all entities regardless of user data' )

    @classmethod
    def default(cls):
        return cls.SAFE


class IntegrationAttributeType( LabeledEnum ):
    """Base for per-integration attribute-type enums."""

    def __init__( self,
                  label             : str,
                  description       : str,
                  value_type        : AttributeValueType,
                  value_range       : Optional[ Union[ List, Dict ] ],
                  is_editable       : bool,
                  is_required       : bool,
                  initial_value     : str                                              = '',
                  capabilities      : Optional[ FrozenSet[ IntegrationCapability ] ]   = None ):
        super().__init__( label, description )
        self.value_type = value_type
        # Shape is value_type-specific and parallels the underlying
        # ``Attribute.value_range_str`` reader on the model side:
        #   * ENUM      -> dict of {value: label} OR list of values
        #                  (consumed via ``Attribute.choices()``)
        #   * INTEGER   -> two-element list [min, max] OR
        #                  dict {"min": ..., "max": ...}
        #                  (consumed via ``Attribute.value_range_int()``)
        #   * FLOAT     -> same shapes as INTEGER
        #                  (consumed via ``Attribute.value_range()``)
        #   * TEXT / SECRET / BOOLEAN / FILE -> ``None`` (no constraint)
        # Persisted by IntegrationManager as ``json.dumps(value_range)``
        # so the attribute model's ``value_range_str`` carries a
        # canonical JSON representation regardless of which shape the
        # author used.
        self.value_range = value_range
        self.is_editable = is_editable
        self.is_required = is_required
        self.initial_value = initial_value
        self.capabilities = capabilities if capabilities is not None else ALL_CAPABILITIES
        return
