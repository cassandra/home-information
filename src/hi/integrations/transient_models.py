from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

from hi.apps.system.enums import HealthStatusType
from .enums import IntegrationAttributeType


@dataclass
class IntegrationMetaData:

    integration_id         : str  # An identifier that must be unique across all integrations
    label                  : str  # For human-friendly displaying
    attribute_type         : IntegrationAttributeType
    allow_entity_deletion  : bool

    
@dataclass
class IntegrationControlResult:

    new_value    : str
    error_list   : List[ str ]

    @property
    def has_errors(self):
        return bool( self.error_list )


@dataclass
class IntegrationKey:
    """
    Internal identifier to help map to/from an integration's
    external names/identifiers
    """

    integration_id    : str  # Internally defined unique identifier for the integration source
    integration_name  : str  # Name or identifier that is used by the external source.

    def __post_init__(self):
        # Want to make matching more robust, so convert to lowercase
        self.integration_id = self.integration_id.lower()
        self.integration_name = self.integration_name.lower()
        return
    
    def __str__(self):
        return self.integration_key_str

    def __eq__(self, other):
        if isinstance(other, IntegrationKey):
            return self.integration_key_str == other.integration_key_str
        return False

    def __hash__(self):
        return hash(self.integration_key_str)
    
    @property
    def integration_key_str(self):
        return f'{self.integration_id}.{self.integration_name}'

    @classmethod
    def from_string( cls, a_string : str ):
        prefix, suffix = a_string.split( '.', 1 )
        return IntegrationKey(
            integration_id = prefix,
            integration_name = suffix,
        )


@dataclass
class IntegrationDetails:
    """
    Integration key plus data for cases where additional integration-specific
    data is needed
    """
    key      : IntegrationKey
    payload  : Optional[Dict] = None


@dataclass
class IntegrationValidationResult:
    """Result from integration configuration validation."""

    is_valid       : bool
    status         : HealthStatusType
    error_message  : Optional[str] = None
    timestamp      : Optional[datetime] = None

    def __post_init__(self):
        if self.timestamp is None:
            import hi.apps.common.datetimeproxy as datetimeproxy
            self.timestamp = datetimeproxy.now()

    @classmethod
    def success(cls) -> 'IntegrationValidationResult':
        """Create a successful validation result."""
        return cls(
            is_valid=True,
            status=HealthStatusType.HEALTHY
        )

    @classmethod
    def error(cls, status: HealthStatusType, error_message: str) -> 'IntegrationValidationResult':
        """Create an error validation result."""
        return cls(
            is_valid=False,
            status=status,
            error_message=error_message
        )
