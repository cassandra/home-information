from abc import ABC, abstractmethod
import copy
import logging
import threading
from typing import Optional, TYPE_CHECKING

import hi.apps.common.datetimeproxy as datetimeproxy

from .enums import HealthStatusType
from .health_status import HealthStatus
from .health_status_transition import HealthStatusTransition
from .provider_info import ProviderInfo

if TYPE_CHECKING:
    from hi.apps.alert.enums import AlarmLevel

logger = logging.getLogger(__name__)


class HealthStatusProvider(ABC):

    def __init__(self):
        # We try not to depend on __init__() being called fo a provider context,
        # so protected most access methods anyway.
        self._ensure_health_status_provider_setup()
        return

    @property
    def initial_health_status(self) -> HealthStatus:
        provider_info = self.get_provider_info()
        return HealthStatus(
            provider_id = provider_info.provider_id,
            provider_name = provider_info.provider_name,
            status = HealthStatusType.UNKNOWN,
            last_update = datetimeproxy.now(),
            last_message = 'Initialization',
            expected_heartbeat_interval_secs = provider_info.expected_heartbeat_interval_secs,
        )
        
    def _ensure_health_status_provider_setup(self):
        if hasattr( self, '_health_status' ):
            return
        self._health_status = self.initial_health_status
        self._health_lock = threading.Lock()
        return

    @classmethod
    @abstractmethod
    def get_provider_info(cls) -> ProviderInfo:
        """Get the API service info for this class. Must be implemented by subclasses."""
        pass

    @property
    def health_status(self) -> HealthStatus:
        self._ensure_health_status_provider_setup()
        with self._health_lock:
            health_status = copy.deepcopy( self._health_status )
        return health_status

    def record_healthy( self, message: str ) -> None:
        self.update_health_status( HealthStatusType.HEALTHY, message )
        return
    
    def record_warning( self, message: str ) -> None:
        self.update_health_status( HealthStatusType.WARNING, message )
        return
    
    def record_error( self, message: str ) -> None:
        self.update_health_status( HealthStatusType.ERROR, message )
        return
    
    def record_disabled( self, message: str ) -> None:
        self.update_health_status( HealthStatusType.DISABLED, message )
        return
    
    def record_heartbeat(self) -> None:
        self._ensure_health_status_provider_setup()
        with self._health_lock:
            self._health_status.heartbeat = datetimeproxy.now()
        logger.debug("Health heartbeat updated")
        return
    
    def alarm_max_level( self ) -> Optional['AlarmLevel']:
        """
        Maximum alarm level this provider is permitted to fire on
        state transitions. Return None to opt out of alarm dispatch
        entirely (the default — most providers update local health
        only). Override and return an AlarmLevel to participate; the
        HealthStatusAlarmMapper will compute a "natural" level for the
        transition (ERROR=CRITICAL, DISABLED=WARNING, recovery=INFO)
        and clamp it down to this ceiling so different providers can
        express their relative importance without each owning the
        full mapping policy.

        Subclass guidance:
        - User-facing managers (whose state transitions reflect
          user-initiated actions like Configure/Sync) should leave
          this at None — those paths give immediate inline feedback
          and don't need redundant alarms.
        - Background periodic monitors that publish health for
          dependencies the user cannot otherwise see should override
          this. The ceiling expresses "how serious is it when this
          dependency degrades silently in the background".
        """
        return None

    def update_health_status( self,
                              status         : HealthStatusType,
                              last_message  : Optional[str]      = None) -> None:
        self._ensure_health_status_provider_setup()
        with self._health_lock:
            previous_status = self._health_status.status
            self._health_status.status = status
            self._health_status.last_update = datetimeproxy.now()
            self._health_status.last_message = last_message

            if status.is_error:
                self._health_status.error_count += 1
            else:
                # Reset error count on successful status
                self._health_status.error_count = 0

            current_error_count = self._health_status.error_count
            current_update_time = self._health_status.last_update

        logger.debug( f'Health status updated to {status.label}:'
                      f' {last_message or "No error"}')

        if previous_status != status:
            try:
                self._dispatch_transition_alarm(
                    previous_status = previous_status,
                    current_status = status,
                    last_message = last_message,
                    error_count = current_error_count,
                    timestamp = current_update_time,
                )
            except Exception:
                # Framework-level safety net: a misbehaving alarm path
                # (or a subclass override that forgets its own
                # try/except) must NEVER break health bookkeeping for
                # the caller of update_health_status.
                logger.exception( 'Failed to dispatch health-status transition alarm.' )
        return

    def _dispatch_transition_alarm( self,
                                    previous_status  : HealthStatusType,
                                    current_status   : HealthStatusType,
                                    last_message     : Optional[str],
                                    error_count      : int,
                                    timestamp ) -> None:
        """
        Map a state transition to an alarm and queue it via AlertManager
        when the provider is opted in (alarm_max_level returns
        non-None). The framework calls into the alert subsystem
        directly — the dependency direction (apps/system -> apps/alert)
        is acceptable since alert is a more general-purpose facility.

        Caller (update_health_status) wraps invocations in a safety
        net, so subclass overrides do not need to defend against their
        own exceptions to preserve health bookkeeping.
        """
        max_level = self.alarm_max_level()
        if max_level is None:
            return

        # Imported lazily to avoid module-load-time edges in apps that
        # do not depend on the alert subsystem at import time.
        from hi.apps.alert.alert_manager import AlertManager
        from .health_status_alarm_mapper import HealthStatusAlarmMapper

        transition = HealthStatusTransition(
            provider_info = self.get_provider_info(),
            previous_status = previous_status,
            current_status = current_status,
            last_message = last_message,
            error_count = error_count,
            timestamp = timestamp,
        )
        alarm = HealthStatusAlarmMapper().create_alarm(
            transition = transition,
            max_level = max_level,
        )
        if alarm is None:
            return
        AlertManager().add_alarm( alarm = alarm )
        return
    
    
    
