from typing import List

from hi.simulator.models import SimDevice
from hi.simulator.service_simulator import ServiceSimulator


class ZoneMinderSimulator( ServiceSimulator ):
    
    @property
    def id(self):
        return 'zm'

    @property
    def label(self) -> str:
        return 'ZoneMinder'
        
    @property
    def sim_devices(self) -> List[ SimDevice ]:
        raise NotImplementedError('Subclasses must override this method.')

    def set_state( self, device_id : int, value : str ):
        raise NotImplementedError('Subclasses must override this method.')
        
