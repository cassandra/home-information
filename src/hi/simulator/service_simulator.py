from typing import List

from hi.apps.common.singleton import Singleton

from .models import SimDevice


class ServiceSimulator( Singleton ):

    def __init_singleton__( self ):
        return
    
    @property
    def id(self) -> str:
        raise NotImplementedError('Subclasses must override this method.')
        
    @property
    def label(self) -> str:
        raise NotImplementedError('Subclasses must override this method.')
        
    @property
    def sim_devices(self) -> List[ SimDevice ]:
        raise NotImplementedError('Subclasses must override this method.')

    def set_state( self, device_id : int, value : str ):
        raise NotImplementedError('Subclasses must override this method.')
        
