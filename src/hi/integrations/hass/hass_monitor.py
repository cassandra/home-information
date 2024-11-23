import logging

from hi.apps.monitor.periodic_monitor import PeriodicMonitor
from hi.apps.monitor.monitor_mixin import SensorMonitorMixin

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
        return

    async def do_work(self):
        id_to_hass_state_map = self._manager.fetch_hass_states_from_api( verbose = False )

        if self.TRACE:
            logger.debug( f'Fetched {len(id_to_hass_state_map)} HAss States' )
        
        
        for hass_state in id_to_hass_state_map.values():
            state_integration_key = HassConverter.hass_state_to_integration_key( hass_state = hass_state )


            hass_state.state_value
            




            # TODO: zzz Update Redis with state values


            
            # zzz How do Hass states roll up to hass entities and how to identify
            # if one entity has multiple states...do states need integration id too???

            
            

            


            
            
            continue
        return
    
