from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

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
    """ Internal identifier to help map to/from an integration's external names/identifiers """

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
    """ Integration key plus data for cases where additional integration-specific data is needed """
    key      : IntegrationKey
    payload  : Optional[Dict] = None


class IntegrationHealthStatusType(Enum):
    """Health status types for integrations"""
    HEALTHY = "healthy"
    CONFIG_ERROR = "config_error"
    CONNECTION_ERROR = "connection_error" 
    TEMPORARY_ERROR = "temporary_error"
    UNKNOWN = "unknown"

    @property
    def is_error(self) -> bool:
        """Returns True if this status represents an error condition"""
        return self in (
            IntegrationHealthStatusType.CONFIG_ERROR,
            IntegrationHealthStatusType.CONNECTION_ERROR,
            IntegrationHealthStatusType.TEMPORARY_ERROR
        )

    @property
    def is_critical(self) -> bool:
        """Returns True if this status requires immediate attention"""
        return self in (
            IntegrationHealthStatusType.CONFIG_ERROR,
            IntegrationHealthStatusType.CONNECTION_ERROR
        )


@dataclass
class IntegrationHealthStatus:
    """Health status information for an integration"""
    
    status: IntegrationHealthStatusType
    last_check: datetime
    error_message: Optional[str] = None
    error_count: int = 0
    
    @property
    def is_healthy(self) -> bool:
        """Returns True if the integration is healthy"""
        return self.status == IntegrationHealthStatusType.HEALTHY
    
    @property
    def is_error(self) -> bool:
        """Returns True if the integration has an error"""
        return self.status.is_error
    
    @property
    def is_critical(self) -> bool:
        """Returns True if the integration has a critical error"""
        return self.status.is_critical
    
    @property
    def status_display(self) -> str:
        """Human-readable status display"""
        return self.status.value.replace('_', ' ').title()
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for template contexts"""
        return {
            'status': self.status.value,
            'status_display': self.status_display,
            'last_check': self.last_check,
            'error_message': self.error_message,
            'error_count': self.error_count,
            'is_healthy': self.is_healthy,
            'is_error': self.is_error,
            'is_critical': self.is_critical,
        }
