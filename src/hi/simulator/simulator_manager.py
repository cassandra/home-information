import logging
from threading import Lock
from typing import Dict

from django.apps import apps

from hi.apps.common.module_utils import import_module_safe
from hi.apps.common.singleton import Singleton

from .service_simulator import ServiceSimulator

logger = logging.getLogger(__name__)


class SimulatorManager( Singleton ):

    def __init_singleton__( self ):
        self._id_to_simulator_map : Dict[ str, ServiceSimulator ] = dict()
        self._data_lock = Lock()
        return

    def get_simulator( self, simulator_id : str ) -> ServiceSimulator:
        return self._id_to_simulator_map.get( simulator_id )
    
    def get_simulator_list(self):
        simulator_list = [ x for x in self._id_to_simulator_map.values() ]
        simulator_list.sort( key = lambda item : item.label )
        return simulator_list
    
    async def initialize(self) -> None:
        self._data_lock.acquire()
        try:
            await self._load_simulator_data()
        finally:
            self._data_lock.release()
        return
        
    async def _load_simulator_data(self) -> None:
        logger.debug("Discovering defined simulators ...")
        self._id_to_simulator_map = self._discover_defined_simulators()
        return

    def _discover_defined_simulators(self) -> Dict[ str, ServiceSimulator ]:

        simulator_id_to_simulator = dict()
        for app_config in apps.get_app_configs():
            if not app_config.name.startswith( 'hi.simulator.services' ):
                continue
            module_name = f'{app_config.name}.simulator'
            try:
                app_module = import_module_safe( module_name = module_name )
                if not app_module:
                    logger.debug( f'No simulator module for {app_config.name}' )
                    continue

                logger.debug( f'Found simulator module for {app_config.name}' )
                
                for attr_name in dir(app_module):
                    attr = getattr( app_module, attr_name )
                    if ( isinstance( attr, type )
                         and issubclass( attr, ServiceSimulator )
                         and attr is not ServiceSimulator ):
                        logger.debug(f'Found simulator: {attr_name}')
                        simulator = attr()
                        simulator_id_to_simulator[simulator.id] = simulator
                    continue                
                
            except Exception as e:
                logger.exception( f'Problem getting simulator for {module_name}.', e )
            continue

        return simulator_id_to_simulator
