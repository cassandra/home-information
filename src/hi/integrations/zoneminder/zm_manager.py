import logging
from pyzm.api import ZMApi
from pyzm.helpers.Event import Event as ZmEvent
from pyzm.helpers.Monitor import Monitor as ZmMonitor
from pyzm.helpers.State import State as ZmState
from pyzm.helpers.globals import logger as pyzm_logger
from typing import Dict, List

import hi.apps.common.datetimeproxy as datetimeproxy
from hi.apps.common.singleton import Singleton

from hi.integrations.core.exceptions import IntegrationAttributeError
from hi.integrations.core.integration_key import IntegrationKey
from hi.integrations.core.models import Integration, IntegrationAttribute

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
    TRACE = False
    
    ZM_ENTITY_NAME = 'ZoneMinder'
    ZM_SYSTEM_INTEGRATION_NAME = 'system'
    ZM_MONITOR_INTEGRATION_NAME_PREFIX = 'monitor'
    VIDEO_STREAM_SENSOR_PREFIX = 'monitor.video_stream'
    MOVEMENT_SENSOR_PREFIX = 'monitor.motion'
    MONITOR_FUNCTION_SENSOR_PREFIX = 'monitor.function'
    ZM_RUN_STATE_SENSOR_INTEGRATION_NAME = 'run.state'

    # ZM monitors and states will not change frequently, so we do not need
    # to query for them at a high frequency.
    #
    STATE_REFRESH_INTERVAL_SECS = 300
    MONITOR_REFRESH_INTERVAL_SECS = 300
   
    def __init_singleton__( self ):
        self._is_loading = False
        self._zm_client = None

        self._zm_state_list = list()
        self._zm_state_timestamp = datetimeproxy.min()
        
        self._zm_monitor_list = list()
        self._zm_monitor_timestamp = datetimeproxy.min()
        
        self.reload()
        return

    @property
    def zm_client(self):
        # Docs: https://pyzm.readthedocs.io/en/latest/
        return self._zm_client
    
    def reload( self ):
        """ Should be called when integration settings are changed. """
        if self._is_loading:
            logger.warning( 'ZoneMinder manager is already loading.' )
            return
        try:
            self._is_loading = True
            self._zm_client = self.create_zm_client()
            self.clear_caches()
            
        finally:
            self._is_loading = False
            logger.debug( 'ZoneMinder manager loading completed.' )
        return

    def clear_caches(self):
        self._zm_state_list = list()
        self._zm_monitor_list = list()
        return
    
    def create_zm_client(self):
        try:
            zm_integration = Integration.objects.get( integration_id = ZmMetaData.integration_id )
        except Integration.DoesNotExist:
            logger.debug( 'ZoneMinder integration is not implemented.' )

        if not zm_integration.is_enabled:
            logger.debug( 'ZoneMinder integration is not enabled.' )
            return None

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
        
        attribute_dict = zm_integration.attributes_by_integration_key
        for zm_attr_type in attr_to_api_option_key.keys():
            integration_key = IntegrationKey(
                integration_id = zm_integration.integration_id,
                integration_name = str(zm_attr_type),
            )
            zm_attr = attribute_dict.get( integration_key )
            if not zm_attr:
                raise IntegrationAttributeError( f'Missing ZM attribute {zm_attr_type}' ) 
            if zm_attr.is_required and not zm_attr.value.strip():
                raise IntegrationAttributeError( f'Missing ZM attribute value for {zm_attr_type}' )

            if zm_attr_type in attr_to_api_option_key:
                options_key = attr_to_api_option_key[zm_attr_type]
                api_options[options_key] = zm_attr.value
            
            continue
        
        logger.debug( f'ZoneMinder client options: {api_options}' )
        return ZMApi( options = api_options )
        
    def get_zm_states( self, force_load : bool = False ) -> List[ ZmState ]:
        state_list_age = datetimeproxy.now() - self._zm_state_timestamp
        if ( force_load
             or ( not self._zm_state_list )
             or ( state_list_age.seconds > self.STATE_REFRESH_INTERVAL_SECS )):
            self._zm_state_list = self.zm_client.states().list()
            self._zm_state_timestamp = datetimeproxy.now()
            if self.TRACE:
                logger.debug( f'Fetched ZM states: {[ x.get() for x in self._zm_state_list ]}' )
        return self._zm_state_list
    
    def get_zm_monitors( self, force_load : bool = False ) -> List[ ZmMonitor ]:
        monitor_list_age = datetimeproxy.now() - self._zm_monitor_timestamp
        if ( force_load
             or ( not self._zm_monitor_list )
             or ( monitor_list_age.seconds > self.MONITOR_REFRESH_INTERVAL_SECS )):
            options = {
                'force_reload': True,  # pyzm caches monitors so need to force api call
            }
            self._zm_monitor_list = self.zm_client.monitors( options ).list()
            self._zm_monitor_timestamp = datetimeproxy.now()
            if self.TRACE:
                logger.debug( f'\n\nFetched ZM monitors: {[ x.get() for x in self._zm_monitor_list ]}\n\n' )
            
        return self._zm_monitor_list
        
    def get_zm_events( self, options : Dict[ str, str ] ) -> List[ ZmEvent ]:
        return self.zm_client.events( options ).list()
    
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
    
    def _monitor_to_integration_key( self, zm_monitor_id  : ZmMonitor ) -> IntegrationKey:
        return IntegrationKey(
            integration_id = ZmMetaData.integration_id,
            integration_name = f'{self.ZM_MONITOR_INTEGRATION_NAME_PREFIX}.{zm_monitor_id}',
        )
    
    def _sensor_to_integration_key( self, sensor_prefix : str, zm_monitor_id  : int ) -> IntegrationKey:
        return IntegrationKey(
            integration_id = ZmMetaData.integration_id,
            integration_name = f'{sensor_prefix}.{zm_monitor_id}',
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
                return integration_attribute.value
            logger.error( 'ZoneMinder integration is not implemented.' )
                
        except IntegrationAttribute.DoesNotExist:
            logger.error( 'ZoneMinder timezone not found.' )

        return 'UTC'

    def get_video_stream_url( self, monitor_id : int ):
        return f'{self.zm_client.portal_url}/cgi-bin/nph-zms?mode=jpeg&scale=100&rate=5&maxfps=5&monitor={monitor_id}'

    def get_event_video_stream_url( self, event_id : int ):
        return f'{self.zm_client.portal_url}/cgi-bin/nph-zms?mode=jpeg&scale=100&rate=5&maxfps=5&replay=single&source=event&event={event_id}'
