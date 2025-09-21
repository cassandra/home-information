from abc import ABC, abstractmethod
from contextlib import contextmanager
import copy
import logging
import threading
import time

from .api_health_status import ApiCallContext, ApiHealthStatus
from .provider_info import ProviderInfo
from .enums import ApiCallStatusType, ApiHealthStatusType

logger = logging.getLogger(__name__)


class ApiHealthStatusProvider(ABC):
    
    def __init__(self):
        # We try not to depend on __init__() being called fo a provider context,
        # so protected most access methods anyway.
        self._ensure_api_health_status_provider_setup()
        return
    
    def _ensure_api_health_status_provider_setup(self):
        if hasattr( self, '_api_health_status' ):
            return

        # Get the API service info from the implementing class
        service_info = self.get_api_provider_info()
        self._api_health_lock = threading.Lock()
        self._api_health_status = ApiHealthStatus(
            provider_id = service_info.provider_id,
            provider_name = service_info.provider_name,
            status = ApiHealthStatusType.UNKNOWN,
        )
        return

    @classmethod
    @abstractmethod
    def get_api_provider_info(cls) -> ProviderInfo:
        """Get the API service info for this class. Must be implemented by subclasses."""
        pass

    @property
    def api_health_status(self) -> ApiHealthStatus:
        self._ensure_api_health_status_provider_setup()
        with self._api_health_lock:
            return copy.deepcopy( self._api_health_status )

    @contextmanager
    def api_call_context( self, operation_name : str ):
        """
          Context manager for tracking API call execution.
          
          Usage:
              with self.api_context( 'fetch_user' ) as ctx:
                  response = requests.get( f'/api/users/{user_id}' )
          """
        self._ensure_api_health_status_provider_setup()
        start_time = time.time()
        api_call_context = ApiCallContext(
            operation_name = operation_name,
            start_time = start_time,
        )
        try:
            yield api_call_context  # Let the API call happen
            api_call_context.status = ApiCallStatusType.SUCCESS
        except Exception as e:
            api_call_context.status = ApiCallStatusType.EXCEPTION
            api_call_context.error = str(e)
            raise
        finally:
            # Always track the call
            api_call_context.duration = time.time() - start_time
            self.record_api_call( api_call_context = api_call_context )
            
        return
    
    def record_api_call( self, api_call_context : ApiCallContext ):
        self._ensure_api_health_status_provider_setup()
        with self._api_health_lock:
            self._api_health_status.record_api_call(         
                api_call_context = api_call_context,
            )
        return
    
    def record_cache_hit( self ):
        self._ensure_api_health_status_provider_setup()
        with self._api_health_lock:
            self._api_health_status.record_cache_hit()
        return
    
    def record_cache_miss( self ):
        self._ensure_api_health_status_provider_setup()
        with self._api_health_lock:
            self._api_health_status.record_cache_miss()
        return

    def record_healthy( self ) -> None:
        self._ensure_api_health_status_provider_setup()
        with self._api_health_lock:
            self._api_health_status.record_healthy()
        return
    
    def record_error( self, message: str ) -> None:
        self._ensure_api_health_status_provider_setup()
        with self._api_health_lock:
            self._api_health_status.record_error( message = message )
        return
    
    def record_disabled( self ) -> None:
        self.update_api_health_status( status_type = ApiHealthStatusType.DISABLED )
        return
    
    def update_api_health_status( self, status_type : ApiHealthStatusType ) -> None:
        self._ensure_api_health_status_provider_setup()
        with self._api_health_lock:
            self._api_health_status.status = status_type
        return

