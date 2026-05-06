from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

from hi.apps.system.enums import HealthStatusType
from .enums import IntegrationAttributeType


@dataclass
class IntegrationMetaData:

    integration_id            : str  # An identifier that must be unique across all integrations
    label                     : str  # For human-friendly displaying
    attribute_type            : IntegrationAttributeType
    allow_entity_deletion     : bool
    can_add_custom_attributes : bool = True
    logo_static_path          : str  = 'img/integrations/default.svg'

    
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
        # Make matching more robust by canonicalizing both fields.
        # The exact rule (currently lowercase) lives in normalize() so
        # external callers comparing raw strings against stored
        # integration_name values can apply the same rule without
        # constructing a full IntegrationKey.
        self.integration_id = self.normalize( self.integration_id )
        self.integration_name = self.normalize( self.integration_name )
        return

    @staticmethod
    def normalize( value : str ) -> str:
        """Canonical normalization applied to ``integration_id`` and
        ``integration_name``. Exposed so callers that need to compare
        raw strings against stored values can apply exactly the same
        rule without constructing full IntegrationKey instances. Most
        comparisons should go through full ``IntegrationKey`` objects
        and rely on the dataclass's ``__hash__`` / ``__eq__`` (which
        also use this rule); this static is the escape hatch for
        cases where a one-shot string normalization is enough."""
        return value.lower()
    
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
class IntegrationRemovalSummary:
    """
    Classification of an integration's attached entities for the Remove
    confirmation dialog. Raw counts only; derived values are properties so
    the object stays consistent.
    """

    total_count: int
    user_data_count: int

    @property
    def deletable_count(self) -> int:
        return self.total_count - self.user_data_count

    @property
    def has_mixed_state(self) -> bool:
        """
        True when at least one entity has user data. Drives the dialog
        decision between a single DELETE action and the DELETE SAFE /
        DELETE ALL variants.
        """
        return self.user_data_count > 0


@dataclass
class ConnectionTestResult:
    """
    Result from a live integration connection probe.

    Distinct from IntegrationValidationResult, which represents schema-level
    validation outcomes. ConnectionTestResult specifically reports whether
    a network probe against the proposed configuration succeeded within a
    bounded timeout.
    """

    is_success     : bool
    message        : Optional[str] = None

    @classmethod
    def success(cls, message: Optional[str] = None) -> 'ConnectionTestResult':
        return cls(is_success=True, message=message)

    @classmethod
    def failure(cls, message: str) -> 'ConnectionTestResult':
        return cls(is_success=False, message=message)


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

