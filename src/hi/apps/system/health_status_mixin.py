import copy
import logging
import threading
from typing import Optional

import hi.apps.common.datetimeproxy as datetimeproxy
from hi.apps.system.enums import HealthStatusType
from hi.apps.system.health_status import HealthStatus

logger = logging.getLogger(__name__)


class HealthStatusMixin:

    def __init__(self):
        # We try not to depend on __init__() being called fo a mixin context,
        # so protected most access methods anyway.
        self._ensure_health_status_mixin_setup()
        return
    
    def _ensure_health_status_mixin_setup(self):
        if hasattr( self, '_health_status' ):
            return
        self._health_lock = threading.Lock()
        self._health_status = HealthStatus(
            status = HealthStatusType.UNKNOWN,
            last_check = datetimeproxy.now(),
        )
        return

    @property
    def health_status(self) -> HealthStatus:
        self._ensure_health_status_mixin_setup()
        with self._health_lock:
            health_status = copy.deepcopy( self._health_status )
        return health_status

    def record_warning( self, error_message: str ) -> None:
        self.update_health_status( HealthStatusType.ERROR, error_message )
        return
    
    def record_error( self, error_message: str ) -> None:
        self.update_health_status( HealthStatusType.ERROR, error_message )
        return
    
    def update_health_status( self,
                              status         : HealthStatusType,
                              error_message  : Optional[str]      = None) -> None:
        self._ensure_health_status_mixin_setup()
        with self._health_lock:
            self._health_status.status = status
            self._health_status.last_check = datetimeproxy.now()
            self._health_status.error_message = error_message

            if status.is_error:
                self._health_status.error_count += 1
            else:
                # Reset error count on successful status
                self._health_status.error_count = 0

        logger.debug( f'Health status updated to {status.label}:'
                      f' {error_message or "No error"}')
        return

    def update_heartbeat(self) -> None:
        self._ensure_health_status_mixin_setup()
        with self._health_lock:
            self._health_status.heartbeat = datetimeproxy.now()
        logger.debug("Health heartbeat updated")
        return
    
    
    
