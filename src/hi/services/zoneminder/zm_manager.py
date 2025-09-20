import logging
import threading
from asgiref.sync import sync_to_async
from .pyzm_client.api import ZMApi
from .pyzm_client.helpers.Event import Event as ZmEvent
from .pyzm_client.helpers.Monitor import Monitor as ZmMonitor
from .pyzm_client.helpers.State import State as ZmState
from .pyzm_client.helpers.globals import logger as pyzm_logger
from typing import Dict, List

import hi.apps.common.datetimeproxy as datetimeproxy
from hi.apps.common.singleton_manager import SingletonManager
from hi.apps.common.utils import str_to_bool
from hi.apps.system.aggregate_health_provider import AggregateHealthProvider
from hi.apps.system.api_health_status_provider import ApiHealthStatusProvider
from hi.apps.system.provider_info import ProviderInfo
from hi.apps.system.enums import HealthStatusType

from hi.integrations.exceptions import (
    IntegrationAttributeError,
    IntegrationError,
    IntegrationDisabledError,
)
from hi.integrations.transient_models import (
    IntegrationKey,
    IntegrationValidationResult,
)
from hi.integrations.models import Integration, IntegrationAttribute

from .constants import ZmTimeouts
from .enums import ZmAttributeType
from .zm_client_factory import ZmClientFactory
from .zm_metadata import ZmMetaData

logger = logging.getLogger(__name__)
pyzm_logger.set_level( 0 )  # pyzm does not use standard 'logging' module. ugh.


class ZoneMinderManager( SingletonManager, AggregateHealthProvider, ApiHealthStatusProvider ):
    """
    References:
      ZM Api code: https://github.com/ZoneMinder/zoneminder/tree/master/web/api/app/Controller
      PyZM code: https://github.com/pliablepixels/pyzm/tree/357fdbd1937dab8027882598b61258ef43dc366a
    """
    ZM_ENTITY_NAME = 'ZoneMinder'
    ZM_SYSTEM_INTEGRATION_NAME = 'system'
    ZM_MONITOR_INTEGRATION_NAME_PREFIX = 'monitor'
    MOVEMENT_SENSOR_PREFIX = 'monitor.motion'
    MOVEMENT_EVENT_PREFIX = 'monitor.motion'
    MONITOR_FUNCTION_SENSOR_PREFIX = 'monitor.function'
    ZM_RUN_STATE_SENSOR_INTEGRATION_NAME = 'run.state'

    # Use centralized timeout values from constants
    STATE_REFRESH_INTERVAL_SECS = ZmTimeouts.STATE_REFRESH_INTERVAL_SECS
    MONITOR_REFRESH_INTERVAL_SECS = ZmTimeouts.MONITOR_REFRESH_INTERVAL_SECS
   
    def __init_singleton__( self ):
        super().__init_singleton__()  # Initialize _data_lock, _async_data_lock, _was_initialized
        self._zm_attr_type_to_attribute = dict()
        self._client_factory = ZmClientFactory()
        # Thread-local storage for ZMApi clients to avoid session sharing
        self._thread_local = threading.local()

        self._zm_state_list = list()
        self._zm_state_timestamp = datetimeproxy.min()

        self._zm_monitor_list = list()
        self._zm_monitor_timestamp = datetimeproxy.min()

        self._change_listeners = set()

        # Add self as the API health status provider to aggregate
        self.add_api_health_status_provider(self)

        return

    @classmethod
    def get_provider_info(cls) -> ProviderInfo:
        return ProviderInfo(
            provider_id = 'zm_integration',
            provider_name = 'ZoneMinder Integration',
            description = '',            
        )
    
    @classmethod
    def get_api_provider_info(cls) -> ProviderInfo:
        """Get the API service info for this manager."""
        return ProviderInfo(
            provider_id = 'zm_api',
            provider_name = 'ZoneMinder API',
            description = 'ZoneMinder video surveillance system API'
        )
    
    def register_change_listener( self, callback ):
        if callback not in self._change_listeners:
            logger.debug( f'Adding ZM setting change listener from {callback.__module__}' )
            self._change_listeners.add( callback )
        else:
            logger.debug( f'ZM setting change listener from {callback.__module__}'
                          f' already registered, skipping duplicate' )
        return
    
    def notify_settings_changed(self):
        self.reload()
        for callback in self._change_listeners:
            try:
                callback()
            except Exception:
                logger.exception( 'Problem calling setting change callback.' )
            continue
        return
    
    @property
    def zm_client(self):
        """
        Get thread-local ZMApi client instance.

        Each thread gets its own client with its own requests.Session
        to avoid thread-safety issues with shared HTTP connections.
        """
        # Check if current thread has a client
        if not hasattr(self._thread_local, 'zm_client') or self._thread_local.zm_client is None:
            # Ensure we have configuration loaded
            if not self._was_initialized:
                self.ensure_initialized()

            # Create new client for this thread
            if self._zm_attr_type_to_attribute:
                self._thread_local.zm_client = self.create_zm_client(self._zm_attr_type_to_attribute)
                logger.debug( f'Created new thread-local ZM client for thread:'
                              f' {threading.current_thread().name}' )
            else:
                logger.warning('Cannot create ZM client - no attributes configured')
                self._thread_local.zm_client = None
                return None

        return self._thread_local.zm_client
    
    def _reload_implementation(self):
        try:
            self._zm_attr_type_to_attribute = self._load_attributes()
            # Clear all thread-local clients since configuration changed
            self._clear_thread_local_clients()
            self.clear_caches()
            self.update_health_status(HealthStatusType.HEALTHY)
            logger.debug( 'ZoneMinder manager loading completed.' )

        except IntegrationDisabledError:
            msg = 'ZoneMinder integration disabled'
            logger.info(msg)
            self.update_health_status( HealthStatusType.DISABLED, msg )

        except IntegrationError as e:
            error_msg = f'ZoneMinder integration configuration error: {e}'
            logger.error(error_msg)
            self.update_health_status( HealthStatusType.ERROR, f"Configuration error: {error_msg}" )

        except IntegrationAttributeError as e:
            error_msg = f'ZoneMinder integration attribute error: {e}'
            logger.error(error_msg)
            self.update_health_status( HealthStatusType.ERROR, f"Configuration error: {error_msg}" )

        except Exception as e:
            error_msg = f'Unexpected error loading ZoneMinder configuration: {e}'
            logger.exception(error_msg)
            self.update_health_status( HealthStatusType.WARNING, f"Temporary issue: {error_msg}" )
        return

    def clear_caches(self):
        self._zm_state_list = list()
        self._zm_monitor_list = list()
        return

    def _clear_thread_local_clients(self):
        """
        Clear thread-local client for current thread.

        Note: We can only clear the client for the current thread since
        threading.local() only exposes data for the current thread.
        Other threads will get new clients on their next access.
        """
        if hasattr(self._thread_local, 'zm_client'):
            old_client = self._thread_local.zm_client
            self._thread_local.zm_client = None
            logger.debug(f'Cleared thread-local ZM client for thread: {threading.current_thread().name}')

            # Clean up the old client's session if possible
            try:
                if old_client and hasattr(old_client, 'session'):
                    old_client.session.close()
                    logger.debug('Closed old ZM client session')
            except Exception as e:
                logger.debug(f'Error closing old ZM client session: {e}')

    def _load_attributes(self) -> Dict[ ZmAttributeType, IntegrationAttribute ]:
        try:
            zm_integration = Integration.objects.get( integration_id = ZmMetaData.integration_id )
        except Integration.DoesNotExist:
            raise IntegrationError( 'ZoneMinder integration is not implemented.' )
        
        if not zm_integration.is_enabled:
            raise IntegrationDisabledError( 'ZoneMinder integration is not enabled.' )

        integration_attributes = list(zm_integration.attributes.all())
        return self._build_zm_attr_type_to_attribute_map(
            integration_attributes=integration_attributes,
            enforce_requirements=True
        )
        
    def create_zm_client(
            self,
            zm_attr_type_to_attribute : Dict[ ZmAttributeType, IntegrationAttribute ] ) -> ZMApi:
        """Create a ZMApi client from integration attributes.

        Delegates to ZmClientFactory for actual client creation.
        """
        return self._client_factory.create_client(zm_attr_type_to_attribute)

    @property
    def should_add_alarm_events( self ) -> bool:
        attribute = self._zm_attr_type_to_attribute.get( ZmAttributeType.ADD_ALARM_EVENTS )
        if attribute:
            return str_to_bool( attribute.value )
        return False
        
    def get_zm_states( self, force_load : bool = False ) -> List[ ZmState ]:
        state_list_age = datetimeproxy.now() - self._zm_state_timestamp
        if ( force_load
             or ( not self._zm_state_list )
             or ( state_list_age.seconds > self.STATE_REFRESH_INTERVAL_SECS )):
            if not self.zm_client:
                logger.warning('ZoneMinder client not available - cannot fetch states')
                return []

            with self.api_call_context( 'zm_states' ):
                self._zm_state_list = self.zm_client.states().list()
                self._zm_state_timestamp = datetimeproxy.now()
                
        return self._zm_state_list
    
    def get_zm_monitors( self, force_load : bool = False ) -> List[ ZmMonitor ]:
        monitor_list_age = datetimeproxy.now() - self._zm_monitor_timestamp
        if ( force_load
             or ( not self._zm_monitor_list )
             or ( monitor_list_age.seconds > self.MONITOR_REFRESH_INTERVAL_SECS )):
            if not self.zm_client:
                logger.warning('ZoneMinder client not available - cannot fetch monitors')
                return []

            with self.api_call_context( 'zm_monitors' ):
                options = {
                    'force_reload': True,  # pyzm caches monitors so need to force api call
                }
                self._zm_monitor_list = self.zm_client.monitors( options ).list()
                self._zm_monitor_timestamp = datetimeproxy.now()

        return self._zm_monitor_list
        
    def get_zm_events( self, options : Dict[ str, str ] ) -> List[ ZmEvent ]:
        if not self.zm_client:
            logger.warning('ZoneMinder client not available - cannot fetch events')
            return []

        # Track API call timing for events (this is the most critical API call)
        with self.api_call_context( 'zm_events' ):
            result = self.zm_client.events( options ).list()

        return result
    
    async def get_zm_states_async( self, force_load : bool = False ) -> List[ ZmState ]:
        """
        Async version of get_zm_states for use in async contexts (monitors).
        Uses sync_to_async to properly handle the synchronous API call.
        """
        return await sync_to_async(
            self.get_zm_states,
            thread_sensitive=True
        )(force_load=force_load)
    
    async def get_zm_monitors_async( self, force_load : bool = False ) -> List[ ZmMonitor ]:
        """
        Async version of get_zm_monitors for use in async contexts (monitors).
        Uses sync_to_async to properly handle the synchronous API call.
        """
        return await sync_to_async(
            self.get_zm_monitors,
            thread_sensitive=True
        )(force_load=force_load)
    
    async def get_zm_events_async( self, options : Dict[ str, str ] ) -> List[ ZmEvent ]:
        """
        Async version of get_zm_events for use in async contexts (monitors).
        Uses sync_to_async to properly handle the synchronous API call.
        """
        return await sync_to_async(
            self.get_zm_events,
            thread_sensitive=True
        )(options=options)
    
    def _zm_integration_key( self ) -> IntegrationKey:
        return IntegrationKey(
            integration_id = ZmMetaData.integration_id,
            integration_name = self.ZM_SYSTEM_INTEGRATION_NAME,
            
        )
    
    def _zm_run_state_integration_key( self ) -> IntegrationKey:
        return IntegrationKey(
            integration_id = ZmMetaData.integration_id,
            integration_name = self.ZM_RUN_STATE_SENSOR_INTEGRATION_NAME,
            
        )
    
    def _to_integration_key( self, prefix : str, zm_monitor_id  : ZmMonitor ) -> IntegrationKey:
        return IntegrationKey(
            integration_id = ZmMetaData.integration_id,
            integration_name = f'{prefix}.{zm_monitor_id}',
        )
    
    def get_zm_tzname(self) -> str:
        try:
            zm_integration = Integration.objects.get( integration_id = ZmMetaData.integration_id )
            integration_key = IntegrationKey(
                integration_id = ZmMetaData.integration_id,
                integration_name = str(ZmAttributeType.TIMEZONE),
            )
            integration_attribute = IntegrationAttribute.objects.filter(
                integration = zm_integration,
                integration_key_str = str(integration_key),
            ).first()
            if integration_attribute:
                tz_name = integration_attribute.value
                if datetimeproxy.is_valid_timezone_name( tz_name = tz_name ):
                    return tz_name
                else:
                    logger.warning( f'ZoneMinder timezone setting is invalid: {tz_name}' )
                    
            logger.error( 'ZoneMinder timezone name is not available.' )
                
        except (Integration.DoesNotExist, IntegrationAttribute.DoesNotExist):
            logger.error( 'ZoneMinder timezone not found.' )

        return 'UTC'
    
    async def get_zm_tzname_async(self) -> str:
        """
        Async version of get_zm_tzname for use in async contexts (monitors).
        Uses sync_to_async to properly handle the synchronous database call.
        """
        return await sync_to_async(
            self.get_zm_tzname,
            thread_sensitive=True
        )()

    def get_video_stream_url( self, monitor_id : int ):
        return f'{self.zm_client.portal_url}/cgi-bin/nph-zms?mode=jpeg&scale=100&rate=5&maxfps=5&monitor={monitor_id}'

    def get_event_video_stream_url( self, event_id : int ):
        # Add timestamp for cache busting to help with connection management
        import time
        timestamp = int(time.time())
        return f'{self.zm_client.portal_url}/cgi-bin/nph-zms?mode=jpeg&scale=100&rate=5&maxfps=5&replay=single&source=event&event={event_id}&_t={timestamp}'
        
    def test_connection(self) -> bool:
        """Test the connection to ZoneMinder API and update health status."""
        try:
            if not self.zm_client:
                self.update_health_status( HealthStatusType.ERROR,
                                           "ZoneMinder client not configured")
                return False
            
            # Try to fetch states to test connection
            states = self.get_zm_states(force_load=True)
            if states:
                self.update_health_status(HealthStatusType.HEALTHY)
                return True
            else:
                self.update_health_status(HealthStatusType.ERROR,
                                          "Failed to fetch states from ZoneMinder API")
                return False
                
        except Exception as e:
            error_msg = f'Connection test failed: {e}'
            logger.debug(error_msg)
            self.update_health_status(HealthStatusType.ERROR, f"Connection error: {error_msg}")
            return False
    
    def test_client_with_attributes(
            self,
            zm_attr_type_to_attribute: Dict[ZmAttributeType, IntegrationAttribute]
    ) -> IntegrationValidationResult:
        """
        Test API connectivity using provided attributes without affecting manager state.
        """
        try:
            temp_client = self._client_factory.create_client(zm_attr_type_to_attribute)
            return self._client_factory.test_client(temp_client)

        except IntegrationError as e:
            return IntegrationValidationResult.error(
                status = HealthStatusType.ERROR,
                error_message = str(e)
            )
        except IntegrationAttributeError as e:
            return IntegrationValidationResult.error(
                status = HealthStatusType.ERROR,
                error_message = str(e)
            )
    
    def validate_configuration(
            self,
            integration_attributes: List[IntegrationAttribute]) -> IntegrationValidationResult:
        try:
            # Build attribute mapping without enforcing requirements (for validation testing)
            zm_attr_type_to_attribute = self._build_zm_attr_type_to_attribute_map(
                integration_attributes=integration_attributes,
                enforce_requirements=False
            )
            return self.test_client_with_attributes(zm_attr_type_to_attribute)

        except Exception as e:
            logger.exception(f'Error in ZoneMinder configuration validation: {e}')
            return IntegrationValidationResult.error(
                status=HealthStatusType.WARNING,
                error_message=f'Configuration validation failed: {e}'
            )
    
    def _build_zm_attr_type_to_attribute_map(
            self, 
            integration_attributes: List[IntegrationAttribute], 
            enforce_requirements: bool = True) -> Dict[ZmAttributeType, IntegrationAttribute]:

        zm_attr_type_to_attribute = {}
        integration_key_to_attribute = { attr.integration_key: attr
                                         for attr in integration_attributes }
        
        for zm_attr_type in ZmAttributeType:
            integration_key = IntegrationKey(
                integration_id = ZmMetaData.integration_id,
                integration_name = str(zm_attr_type),
            )
            zm_attr = integration_key_to_attribute.get(integration_key)
            
            if not zm_attr:
                if enforce_requirements and zm_attr_type.is_required:
                    raise IntegrationAttributeError(f'Missing ZM attribute {zm_attr_type}')
                else:
                    continue
                    
            if enforce_requirements and zm_attr.is_required and not zm_attr.value.strip():
                raise IntegrationAttributeError(f'Missing ZM attribute value for {zm_attr_type}')
            
            zm_attr_type_to_attribute[zm_attr_type] = zm_attr
            
        return zm_attr_type_to_attribute
