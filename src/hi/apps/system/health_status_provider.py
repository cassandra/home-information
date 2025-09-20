from abc import ABC, abstractmethod
import copy
import logging
import threading
from typing import Optional

import hi.apps.common.datetimeproxy as datetimeproxy

from .enums import HealthStatusType
from .health_status import HealthStatus
from .provider_info import ProviderInfo

logger = logging.getLogger(__name__)


class HealthStatusProvider(ABC):

    def __init__(self):
        # We try not to depend on __init__() being called fo a provider context,
        # so protected most access methods anyway.
        self._ensure_health_status_provider_setup()
        return

    def _ensure_health_status_provider_setup(self):
        if hasattr( self, '_health_status' ):
            return
        provider_info = self.get_provider_info()
        self._health_status = HealthStatus(
            provider_id = provider_info.provider_id,
            provider_name = provider_info.provider_name,
            status = HealthStatusType.UNKNOWN,
            last_check = datetimeproxy.now(),
        )
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

    def record_warning( self, error_message: str ) -> None:
        self.update_health_status( HealthStatusType.WARNING, error_message )
        return
    
    def record_error( self, error_message: str ) -> None:
        self.update_health_status( HealthStatusType.ERROR, error_message )
        return
    
    def update_health_status( self,
                              status         : HealthStatusType,
                              error_message  : Optional[str]      = None) -> None:
        self._ensure_health_status_provider_setup()
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
        self._ensure_health_status_provider_setup()
        with self._health_lock:
            self._health_status.heartbeat = datetimeproxy.now()
        logger.debug("Health heartbeat updated")
        return
    
    
    
