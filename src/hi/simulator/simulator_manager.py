from asgiref.sync import sync_to_async
import logging
from threading import Lock
from typing import Dict, Type

from django.apps import apps

from hi.apps.common.module_utils import import_module_safe
from hi.apps.common.singleton import Singleton

from .models import DbSimEntity, SimProfile
from .simulator import Simulator
from .transient_models import SimEntity

logger = logging.getLogger(__name__)


class SimulatorManager( Singleton ):

    DEFAULT_PROFILE_NAME = 'Default'
    
    def __init_singleton__( self ):
        self._current_sim_profile = None
        self._id_to_simulator_map : Dict[ str, Simulator ] = dict()
        self._data_lock = Lock()
        return

    @property
    def current_sim_profile(self) -> SimProfile:
        return self._current_sim_profile
    
    def get_simulator( self, simulator_id : str ) -> Simulator:
        return self._id_to_simulator_map.get( simulator_id )
    
    def get_simulator_list(self):
        simulator_list = [ x for x in self._id_to_simulator_map.values() ]
        simulator_list.sort( key = lambda item : item.label )
        return simulator_list
    
    async def initialize(self) -> None:
        self._data_lock.acquire()
        try:
            await sync_to_async( self._set_current_sim_profile )()
            await sync_to_async( self._load_simulator_data )()
        finally:
            self._data_lock.release()
        return

    def _set_current_sim_profile(self):
        self._current_sim_profile = SimProfile.objects.all().first()
        if not self._current_sim_profile:
            self._current_sim_profile = SimProfile.objects.create(
                name = self.DEFAULT_PROFILE_NAME,
            )
        return
    
    def _load_simulator_data(self) -> None:
        logger.debug("Discovering defined simulators ...")
        self._id_to_simulator_map = self._discover_defined_simulators()
        self._defined_entity_classes = self._load_defined_entity_classes()
        self._initialize_simulators( )
        return

    def _load_defined_entity_classes(self) -> Dict[ str, Dict[ str, Type[ SimEntity ]]]:
        """
        Query simulators to get the defined subclasses of SimEntity. Returns a
        map from simulator id, to class name, then to the (sub) class itself
        (which is used to create instances).
        """
        
        defined_entity_classes = dict()
        for simulator_id, simulator in self._id_to_simulator_map.items():
            sim_entity_class_list = simulator.get_sim_entity_class_list()
            logger.debug( f'Adding {len(sim_entity_class_list)} entity class to simulator {simulator_id}.' )
            if simulator_id not in defined_entity_classes:
                defined_entity_classes[simulator_id] = dict()
            for sim_entity_class in sim_entity_class_list:
                class_name = sim_entity_class.__name__
                defined_entity_classes[class_name] = sim_entity_class
                continue
            continue
        return defined_entity_classes
    
    def _initialize_simulators(self):
        
        db_sim_entity_queryset = DbSimEntity.objects.prefetch_related( 'db_sim_states' ).filter(
            sim_profile = self.current_sim_profile,
        )
        simulator_id_to_entity_list = dict()
        for db_sim_entity in db_sim_entity_queryset:
            simulator_id = db_sim_entity.simulator_id
            if simulator_id not in simulator_id_to_entity_list:
                simulator_id_to_entity_list[simulator_id] = list()

            sim_entity_class_map = self._defined_entity_classes.get( simulator_id )

            class_name = db_sim_entity.entity_class_name
            entity_class = sim_entity_class_map.get( class_name )
            if not entity_class:
                logger.warning( f'Entity class "{class_name}" not found for simulator "{simulator_id}"' )
                continue
            
            sim_entity = entity_class.from_db_model( db_sim_entity )
            simulator_id_to_entity_list[simulator_id].append( sim_entity )
            continue

        for simulator_id, simulator in self._id_to_simulator_map.items():
            sim_entity_list = simulator_id_to_entity_list.get( simulator_id, list() )
            logger.debug( f'Initializing simulator {simulator_id} with {len(sim_entity_list)} entities.' )
            simulator.initialize( sim_entity_list = sim_entity_list )
            continue
        
        return

    def _discover_defined_simulators(self) -> Dict[ str, Simulator ]:

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
                         and issubclass( attr, Simulator )
                         and attr is not Simulator ):
                        logger.debug(f'Found simulator: {attr_name}')
                        simulator = attr()
                        simulator_id_to_simulator[simulator.id] = simulator
                    continue                
                
            except Exception as e:
                logger.exception( f'Problem getting simulator for {module_name}.', e )
            continue

        return simulator_id_to_simulator
