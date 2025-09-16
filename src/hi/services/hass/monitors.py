import logging

import hi.apps.common.datetimeproxy as datetimeproxy
from hi.apps.monitor.periodic_monitor import PeriodicMonitor
from hi.apps.sense.sensor_response_manager import SensorResponseMixin
from hi.apps.sense.transient_models import SensorResponse

from .hass_converter import HassConverter
from .hass_mixins import HassMixin

logger = logging.getLogger(__name__)


class HassMonitor( PeriodicMonitor, HassMixin, SensorResponseMixin ):

    HASS_POLLING_INTERVAL_SECS = 2
    HASS_API_TIMEOUT_SECS = 10.0  # Shorter timeout appropriate for 2-second polling

    def __init__( self ):
        super().__init__(
            id = 'hass-monitor',
            interval_secs = self.HASS_POLLING_INTERVAL_SECS,
        )
        self._was_initialized = False
        return
    
    def get_api_timeout(self) -> float:
        return self.HASS_API_TIMEOUT_SECS

    async def _initialize(self):
        hass_manager = await self.hass_manager_async()
        if not hass_manager:
            return
        _ = await self.sensor_response_manager_async()  # Allows async use of self.sensor_response_manager()
        hass_manager.register_change_listener( self.refresh )
        self._was_initialized = True
        return
    
    def refresh( self ):
        """ 
        Called when integration settings are changed (via listener callback).
        
        Note: HassManager.reload() is already called BEFORE this callback is triggered,
        so we should NOT call manager.reload() here to avoid redundant reloads.
        The monitor should just reset its own state to pick up fresh manager state.
        """
        # Reset monitor state so next cycle reinitializes with updated manager
        self._was_initialized = False
        logger.info( 'HassMonitor refreshed - will reinitialize with new settings on next cycle' )
        return
    
    async def do_work(self):
        if not self._was_initialized:
            await self._initialize()

        if not self._was_initialized:
            # Timing issues when first enabling could fail initialization.
            logger.warning( 'HAss monitor failed to initialize. Skipping work cycle.' )
            return
        
        hass_manager = await self.hass_manager_async()
        if not hass_manager:
            return
        
        id_to_hass_state_map = await hass_manager.fetch_hass_states_from_api_async( verbose = False )
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
    
