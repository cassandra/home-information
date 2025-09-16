import logging
from asgiref.sync import sync_to_async
from .pyzm_client.api import ZMApi
from .pyzm_client.helpers.Event import Event as ZmEvent
from .pyzm_client.helpers.Monitor import Monitor as ZmMonitor
from .pyzm_client.helpers.State import State as ZmState
from .pyzm_client.helpers.globals import logger as pyzm_logger
from threading import Lock
from typing import Dict, List

import hi.apps.common.datetimeproxy as datetimeproxy
from hi.apps.common.singleton import Singleton
from hi.apps.common.utils import str_to_bool

from hi.integrations.exceptions import IntegrationAttributeError, IntegrationError
from hi.integrations.transient_models import IntegrationKey, IntegrationHealthStatus, IntegrationHealthStatusType
from hi.integrations.models import Integration, IntegrationAttribute

from .enums import ZmAttributeType
from .zm_metadata import ZmMetaData

logger = logging.getLogger(__name__)
pyzm_logger.set_level( 0 )  # pyzm does not use standard 'logging' module. ugh.


class ZoneMinderManager( Singleton ):
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

    # ZM monitors and states will not change frequently, so we do not need
    # to query for them at a high frequency.
    #
    STATE_REFRESH_INTERVAL_SECS = 300
    MONITOR_REFRESH_INTERVAL_SECS = 300
   
    def __init_singleton__( self ):
        self._zm_attr_type_to_attribute = dict()
        self._zm_client = None

        self._zm_state_list = list()
        self._zm_state_timestamp = datetimeproxy.min()
        
        self._zm_monitor_list = list()
        self._zm_monitor_timestamp = datetimeproxy.min()

        self._change_listeners = list()
        self._was_initialized = False
        self._data_lock = Lock()
        
        # Health status tracking
        self._health_status = IntegrationHealthStatus(
            status=IntegrationHealthStatusType.UNKNOWN,
            last_check=datetimeproxy.now()
        )
        return
    
    def ensure_initialized(self):
        if self._was_initialized:
            return
        self.reload()
        self._was_initialized = True
        return

    def register_change_listener( self, callback ):
        logger.debug( f'Adding ZM setting change listener from {callback.__module__}' )
        self._change_listeners.append( callback )
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
        # Docs: https://pyzm.readthedocs.io/en/latest/
        if not self._zm_client:
            self.reload()
        return self._zm_client
    
    def reload( self ):
        """ Called when integration models are changed (via signals below). """
        logger.debug( 'ZoneMinder manager loading started.' )
        with self._data_lock:
            try:
                self._zm_attr_type_to_attribute = self._load_attributes()
                self._zm_client = self.create_zm_client( self._zm_attr_type_to_attribute )
                self.clear_caches()
                self._update_health_status(IntegrationHealthStatusType.HEALTHY)
                logger.debug( 'ZoneMinder manager loading completed.' )
            except IntegrationError as e:
                error_msg = f'ZoneMinder integration configuration error: {e}'
                logger.error(error_msg)
                self._update_health_status(IntegrationHealthStatusType.CONFIG_ERROR, error_msg)
            except IntegrationAttributeError as e:
                error_msg = f'ZoneMinder integration attribute error: {e}'
                logger.error(error_msg)
                self._update_health_status(IntegrationHealthStatusType.CONFIG_ERROR, error_msg)
            except Exception as e:
                error_msg = f'Unexpected error loading ZoneMinder configuration: {e}'
                logger.exception(error_msg)
                self._update_health_status(IntegrationHealthStatusType.TEMPORARY_ERROR, error_msg)
        return

    def clear_caches(self):
        self._zm_state_list = list()
        self._zm_monitor_list = list()
        return

    def _load_attributes(self) -> Dict[ ZmAttributeType, IntegrationAttribute ]:
        try:
            zm_integration = Integration.objects.get( integration_id = ZmMetaData.integration_id )
        except Integration.DoesNotExist:
            raise IntegrationError( 'ZoneMinder integration is not implemented.' )
        
        if not zm_integration.is_enabled:
            raise IntegrationError( 'ZoneMinder integration is not enabled.' )

        integration_attributes = list(zm_integration.attributes.all())
        return self._build_zm_attr_type_to_attribute_map(
            integration_attributes=integration_attributes,
            enforce_requirements=True
        )
        
    def create_zm_client(
            self,
            zm_attr_type_to_attribute : Dict[ ZmAttributeType, IntegrationAttribute ] ) -> ZMApi:

        # Verify integration and build API data payload
        api_options = {
            # 'disable_ssl_cert_check': True
        }
        attr_to_api_option_key = {
            ZmAttributeType.API_URL: 'apiurl',
            ZmAttributeType.PORTAL_URL: 'portalurl',
            ZmAttributeType.API_USER: 'user',
            ZmAttributeType.API_PASSWORD: 'password',
        }
        
        integration_key_to_attribute = { x.integration_key: x for x in zm_attr_type_to_attribute.values() }
        for zm_attr_type in attr_to_api_option_key.keys():
            integration_key = IntegrationKey(
                integration_id = ZmMetaData.integration_id,
                integration_name = str(zm_attr_type),
            )
            zm_attr = integration_key_to_attribute.get( integration_key )
            if not zm_attr:
                raise IntegrationAttributeError( f'Missing ZM API attribute {zm_attr_type}' )
            if not zm_attr.value.strip():
                raise IntegrationAttributeError( f'Missing ZM API attribute value for {zm_attr_type}' )

            options_key = attr_to_api_option_key[zm_attr_type]
            api_options[options_key] = zm_attr.value
            continue
        
        logger.debug( f'ZoneMinder client options: {api_options}' )
        return ZMApi( options = api_options )

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
            self._zm_state_list = self.zm_client.states().list()
            self._zm_state_timestamp = datetimeproxy.now()
            logger.debug( f'Fetched ZM states: {[ x.get() for x in self._zm_state_list ]}' )
        return self._zm_state_list
    
    def get_zm_monitors( self, force_load : bool = False ) -> List[ ZmMonitor ]:
        monitor_list_age = datetimeproxy.now() - self._zm_monitor_timestamp
        if ( force_load
             or ( not self._zm_monitor_list )
             or ( monitor_list_age.seconds > self.MONITOR_REFRESH_INTERVAL_SECS )):
            if not self.zm_client:
                logger.warning('ZoneMinder client not available - cannot fetch monitors')
                return []
            options = {
                'force_reload': True,  # pyzm caches monitors so need to force api call
            }
            self._zm_monitor_list = self.zm_client.monitors( options ).list()
            self._zm_monitor_timestamp = datetimeproxy.now()
            logger.debug( f'\n\nFetched ZM monitors: {[ x.get() for x in self._zm_monitor_list ]}\n\n' )
            
        return self._zm_monitor_list
        
    def get_zm_events( self, options : Dict[ str, str ] ) -> List[ ZmEvent ]:
        if not self.zm_client:
            logger.warning('ZoneMinder client not available - cannot fetch events')
            return []
        return self.zm_client.events( options ).list()
    
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
    
    def get_health_status(self) -> IntegrationHealthStatus:
        """Get the current health status of the ZoneMinder integration."""
        return self._health_status
    
    def _update_health_status(self, status: IntegrationHealthStatusType, error_message: str = None):
        """Update the health status of this integration."""
        old_status = self._health_status.status
        
        # Update health status
        self._health_status = IntegrationHealthStatus(
            status=status,
            last_check=datetimeproxy.now(),
            error_message=error_message,
            error_count=self._health_status.error_count + (1 if status.is_error else 0)
        )
        
        # Log status changes
        if old_status != status:
            if status == IntegrationHealthStatusType.HEALTHY:
                logger.info('ZoneMinder integration is now healthy')
            else:
                logger.warning(f'ZoneMinder integration health status changed to {status.value}: {error_message}')
    
    def test_connection(self) -> bool:
        """Test the connection to ZoneMinder API and update health status."""
        try:
            if not self.zm_client:
                self._update_health_status(IntegrationHealthStatusType.CONFIG_ERROR, "ZoneMinder client not configured")
                return False
            
            # Try to fetch states to test connection
            states = self.get_zm_states(force_load=True)
            if states:
                self._update_health_status(IntegrationHealthStatusType.HEALTHY)
                return True
            else:
                self._update_health_status(IntegrationHealthStatusType.CONNECTION_ERROR, "Failed to fetch states from ZoneMinder API")
                return False
                
        except Exception as e:
            error_msg = f'Connection test failed: {e}'
            logger.debug(error_msg)
            self._update_health_status(IntegrationHealthStatusType.CONNECTION_ERROR, error_msg)
            return False
    
    def test_client_with_attributes(self, zm_attr_type_to_attribute: Dict[ZmAttributeType, IntegrationAttribute]) -> Dict[str, any]:
        """
        Test API connectivity using provided attributes without affecting manager state.
        
        Args:
            zm_attr_type_to_attribute: Dictionary mapping attribute types to attribute objects
            
        Returns:
            Dictionary with validation result:
            {
                'success': bool,
                'error_message': str or None,
                'error_type': 'config'|'connection'|'auth'|'unknown' or None
            }
        """
        try:
            # Create temporary client with provided attributes
            temp_client = self.create_zm_client(zm_attr_type_to_attribute)
            
            # Test basic API connectivity by fetching states
            states = temp_client.states().list()
            if states is not None:
                # Successful API call
                return {
                    'success': True,
                    'error_message': None,
                    'error_type': None
                }
            else:
                return {
                    'success': False,
                    'error_message': 'Failed to fetch states from ZoneMinder API',
                    'error_type': 'connection'
                }
                
        except IntegrationError as e:
            return {
                'success': False,
                'error_message': str(e),
                'error_type': 'config'
            }
        except IntegrationAttributeError as e:
            return {
                'success': False,
                'error_message': str(e),
                'error_type': 'config'
            }
        except Exception as e:
            error_msg = str(e).lower()
            
            # Categorize common error types for better user feedback
            if any(keyword in error_msg for keyword in ['auth', 'unauthorized', 'forbidden', 'login', 'credential', 'password']):
                error_type = 'auth'
                user_message = f'Authentication failed: {e}'
            elif any(keyword in error_msg for keyword in ['connect', 'network', 'timeout', 'unreachable', 'resolve', 'schema', 'url']):
                error_type = 'connection'  
                user_message = f'Cannot connect to ZoneMinder: {e}'
            else:
                error_type = 'unknown'
                user_message = f'API test failed: {e}'
            
            return {
                'success': False,
                'error_message': user_message,
                'error_type': error_type
            }
    
    def validate_configuration(self, integration_attributes: List[IntegrationAttribute]) -> Dict[str, any]:
        """
        Validate ZoneMinder configuration using provided attributes.
        
        Args:
            integration_attributes: List of IntegrationAttribute objects
            
        Returns:
            Dictionary with validation result (same format as test_client_with_attributes)
        """
        try:
            # Build attribute mapping without enforcing requirements (for validation testing)
            zm_attr_type_to_attribute = self._build_zm_attr_type_to_attribute_map(
                integration_attributes=integration_attributes,
                enforce_requirements=False
            )
            
            # Use existing test method
            return self.test_client_with_attributes(zm_attr_type_to_attribute)
            
        except Exception as e:
            logger.exception(f'Error in ZoneMinder configuration validation: {e}')
            return {
                'success': False,
                'error_message': f'Configuration validation failed: {e}',
                'error_type': 'unknown'
            }
    
    def _build_zm_attr_type_to_attribute_map(
            self, 
            integration_attributes: List[IntegrationAttribute], 
            enforce_requirements: bool = True) -> Dict[ZmAttributeType, IntegrationAttribute]:
        """Build mapping from ZmAttributeType to IntegrationAttribute.
        
        Args:
            integration_attributes: List of IntegrationAttribute objects
            enforce_requirements: If True, raise errors for missing required attributes
            
        Returns:
            Dictionary mapping ZmAttributeType to IntegrationAttribute
        """
        zm_attr_type_to_attribute = {}
        integration_key_to_attribute = {attr.integration_key: attr for attr in integration_attributes}
        
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
