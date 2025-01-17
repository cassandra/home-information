import logging

import hi.apps.common.datetimeproxy as datetimeproxy
from hi.apps.monitor.periodic_monitor import PeriodicMonitor
from hi.apps.sense.sensor_response_manager import SensorResponseMixin
from hi.apps.sense.transient_models import SensorResponse

from .hass_converter import HassConverter
from .hass_mixins import HassMixin

logger = logging.getLogger(__name__)


class HassMonitor( PeriodicMonitor, HassMixin, SensorResponseMixin ):

    HASS_POLLING_INTERVAL_SECS = 10

    def __init__( self ):
        super().__init__(
            id = 'hass-monitor',
            interval_secs = self.HASS_POLLING_INTERVAL_SECS,
        )
        self._was_initialized = False
        return

    async def _initialize(self):
        hass_manager = await self.hass_manager_async()
        _ = await self.sensor_response_manager_async()  # Allows async use of self.sensor_response_manager()
        hass_manager.register_change_listener( self.refresh )
        self._was_initialized = True
        return
    
    def refresh( self ):
        """ Should be called when integration settings are changed (via listener callback). """
        return
    
    async def do_work(self):
        if not self._was_initialized:
            await self._initialize()
            
        id_to_hass_state_map = self.hass_manager().fetch_hass_states_from_api( verbose = False )
        logger.debug( f'Fetched {len(id_to_hass_state_map)} HAss States' )
        
        current_datetime = datetimeproxy.now()
        sensor_response_latest_map = dict()
        
        for hass_state in id_to_hass_state_map.values():
            integration_key = HassConverter.hass_state_to_integration_key( hass_state = hass_state )
            sensor_value_str = HassConverter.hass_state_to_sensor_value_str( hass_state )
            if not sensor_value_str:
                continue
            sensor_response = SensorResponse(
                integration_key = integration_key,
                value = sensor_value_str,
                timestamp = current_datetime,
            )
            sensor_response_latest_map[integration_key] = sensor_response
            continue

        await self.sensor_response_manager().update_with_latest_sensor_responses(
            sensor_response_map = sensor_response_latest_map,
        )
        return
    
