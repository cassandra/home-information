from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from .enums import HealthStatusType
from .provider_info import ProviderInfo


@dataclass
class HealthStatusTransition:
    """
    Materialization of a single observed change in a HealthStatusProvider's
    status. Built and dispatched by HealthStatusProvider.update_health_status
    when (and only when) the new status differs from the prior one.

    Consumers (e.g., HealthStatusAlarmMapper) use this to decide whether to
    emit alarms / alerts. The transient is intentionally narrow — no
    references to alert plumbing — so apps/system stays alert-free.
    """

    provider_info    : ProviderInfo
    previous_status  : HealthStatusType
    current_status   : HealthStatusType
    last_message     : Optional[ str ]
    error_count      : int
    timestamp        : datetime

    @property
    def is_recovery(self) -> bool:
        """Transition into HEALTHY from a previously-non-HEALTHY state."""
        return bool(
            self.current_status == HealthStatusType.HEALTHY
            and self.previous_status != HealthStatusType.HEALTHY
        )
