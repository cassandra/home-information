from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

from .enums import IntegrationAttributeType, IntegrationHealthStatusType


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
class IntegrationHealthStatus:

    status         : IntegrationHealthStatusType
    last_check     : datetime
    error_message  : Optional[str]     = None
    error_count    : int               = 0
    # Enhanced monitoring fields for debugging transient issues
    monitor_heartbeat : Optional[datetime] = None  # Last time the monitor cycled successfully
    last_api_success  : Optional[datetime] = None  # Last successful API call
    api_metrics      : Optional[Dict] = None      # API call performance metrics
    async_diagnostics : Optional[Dict] = None     # Background task and async loop diagnostics

    @property
    def is_healthy(self) -> bool:
        return self.status == IntegrationHealthStatusType.HEALTHY

    @property
    def is_error(self) -> bool:
        return self.status.is_error

    @property
    def is_critical(self) -> bool:
        return self.status.is_critical

    @property
    def status_display(self) -> str:
        return self.status.label

    def to_dict(self) -> Dict:
        result = {
            'status': self.status.value,
            'status_display': self.status_display,
            'last_check': self.last_check,
            'error_message': self.error_message,
            'error_count': self.error_count,
            'is_healthy': self.is_healthy,
            'is_error': self.is_error,
            'is_critical': self.is_critical,
        }

        # Include enhanced monitoring fields if present
        if self.monitor_heartbeat is not None:
            import hi.apps.common.datetimeproxy as datetimeproxy
            heartbeat_age = (datetimeproxy.now() - self.monitor_heartbeat).total_seconds()
            result['monitor_heartbeat'] = self.monitor_heartbeat
            result['monitor_heartbeat_age_seconds'] = heartbeat_age

        if self.last_api_success is not None:
            result['last_api_success'] = self.last_api_success

        if self.api_metrics is not None:
            result['api_metrics'] = self.api_metrics

        if self.async_diagnostics is not None:
            result['async_diagnostics'] = self.async_diagnostics

        return result


@dataclass
class IntegrationValidationResult:
    """Result from integration configuration validation."""

    is_valid       : bool
    status         : IntegrationHealthStatusType
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
            status=IntegrationHealthStatusType.HEALTHY
        )

    @classmethod
    def error(cls, status: IntegrationHealthStatusType, error_message: str) -> 'IntegrationValidationResult':
        """Create an error validation result."""
        return cls(
            is_valid=False,
            status=status,
            error_message=error_message
        )
