import logging

from hi.apps.monitor.periodic_monitor import PeriodicMonitor
from hi.apps.monitor.state_monitor_mixin import EntityStateMonitorMixin

from .hass_manager import HassManager

logger = logging.getLogger(__name__)


class HassMonitor( PeriodicMonitor, EntityStateMonitorMixin ):

    def __init__( self ):
        super().__init__(
            id = 'hass-monitor',
            interval_secs = 10,
        )
        self._manager = HassManager()
        return

    async def do_work(self):
        if self.TRACE:
            logger.debug( 'Fetched HAss States' )
        
        id_to_hass_state_map = self._manager.fetch_hass_states_from_api( verbose = False )
        for hass_state in id_to_hass_state_map.values():





            # TODO: zzz Update Redis with state values


            
            # zzz How do Hass states roll up to hass entities and how to identify
            # if one entity has multiple states...do states need integration id too???

            
            

            


            
            
            continue
        return
    
