from typing import List

from hi.simulator.models import SimDevice
from hi.simulator.service_simulator import ServiceSimulator


class HassSimulator( ServiceSimulator ):

    @property
    def id(self):
        return 'hass'

    @property
    def label(self):
        return 'Home Assistant'

    @property
    def sim_devices(self) -> List[ SimDevice ]:
        raise NotImplementedError('Subclasses must override this method.')

    def set_state( self, device_id : int, value : str ):
        raise NotImplementedError('Subclasses must override this method.')
        
