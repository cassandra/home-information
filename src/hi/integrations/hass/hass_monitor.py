import logging

import hi.apps.common.datetimeproxy as datetimeproxy
from hi.apps.monitor.periodic_monitor import PeriodicMonitor
from hi.apps.monitor.monitor_mixin import SensorMonitorMixin
from hi.apps.monitor.transient_models import SensorResponse

from .hass_converter import HassConverter
from .hass_manager import HassManager

logger = logging.getLogger(__name__)


class HassMonitor( PeriodicMonitor, SensorMonitorMixin ):

    def __init__( self ):
        super().__init__(
            id = 'hass-monitor',
            interval_secs = 10,
        )
        self._manager = HassManager()
        self._logger = logging.getLogger(__name__)
        return

    async def do_work(self):
        id_to_hass_state_map = self._manager.fetch_hass_states_from_api( verbose = False )

        if self.TRACE:
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

        self.update_with_latest_sensor_responses( sensor_response_latest_map )
        return
    
