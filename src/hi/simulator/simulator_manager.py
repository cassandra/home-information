from asgiref.sync import sync_to_async
import logging
from threading import Lock
from typing import Dict, Type

from django.apps import apps

import hi.apps.common.datetimeproxy as datetimeproxy
from hi.apps.common.module_utils import import_module_safe
from hi.apps.common.singleton import Singleton

from .models import DbSimEntity, SimProfile
from .simulator import Simulator
from .simulator_data import SimulatorData
from .transient_models import SimEntity, SimEntityClassWrapper

logger = logging.getLogger(__name__)


class SimulatorManager( Singleton ):

    DEFAULT_PROFILE_NAME = 'Default'
    
    def __init_singleton__( self ):
        self._current_sim_profile = None
        self._simulator_data_map : Dict[ str, SimulatorData ] = dict()
        self._data_lock = Lock()
        return

    def get_sim_profile_list(self):
        return list( SimProfile.objects.all().order_by('name') )

    @property
    def current_sim_profile(self) -> SimProfile:
        return self._current_sim_profile

    def set_sim_profile( self, sim_profile : SimProfile ):
        if not sim_profile:
            self._initialize_sim_profile()
        else:
            sim_profile.last_switched_to_datetime = datetimeproxy.now()
            sim_profile.save()
            self._current_sim_profile = sim_profile

        if sim_profile != self._current_sim_profile:
            self._initialize_simulators()
        return
        
    def get_simulator( self, simulator_id : str ) -> Simulator:
        simulator_data = self._simulator_data_map.get( simulator_id )
        if not simulator_id:
            raise KeyError( f'Simulator id "{simulator_id}" not found.' )
        return simulator_data.simulator
    
    def get_simulator_list(self):
        simulator_list = [ x.simulator for x in self._simulator_data_map.values() ]
        simulator_list.sort( key = lambda item : item.label )
        return simulator_list

    def add_sim_entity( self,
                        simulator   : Simulator,
                        sim_entity  : SimEntity ):
        self._data_lock.acquire()
        try:
            simulator_data = self._simulator_data_map.get( simulator.id )
            if not simulator_data:
                raise KeyError( f'No data found for simulator id = {simulator.id}' )
                
            sim_entity_class_wrapper = SimEntityClassWrapper( sim_entity_class = sim_entity.__class__ )

            db_sim_entity = DbSimEntity.objects.create(
                sim_profile = self.current_sim_profile,
                simulator_id = simulator.id,
                entity_class_name = sim_entity_class_wrapper.name,
                entity_type = sim_entity_class_wrapper.entity_type,
                editable_fields = sim_entity.to_json_dict()
            )

            simulator_data.sim_entity_instance_map[sim_entity] = db_sim_entity
            simulator.add_sim_entity( sim_entity = sim_entity )

        finally:
            self._data_lock.release()
                        
    async def initialize(self) -> None:
        self._data_lock.acquire()
        try:
            await sync_to_async( self._initialize_sim_profile )()
            await sync_to_async( self._discover_defined_simulators )()
            await sync_to_async( self._discovery_sim_entity_classes )()
            await sync_to_async( self._load_sim_entity_instances )()
            await sync_to_async( self._initialize_simulators )()

        finally:
            self._data_lock.release()
        return

    def _initialize_sim_profile(self):
        logger.debug("Initialize SimProfile ...")
        self._current_sim_profile = SimProfile.objects.all().first()  # Default ordering by usage time
        if not self._current_sim_profile:
            self._current_sim_profile = SimProfile.objects.create(
                name = self.DEFAULT_PROFILE_NAME,
                last_switched_to_datetime = datetimeproxy.now(),
            )
        return

    def _discover_defined_simulators(self):
        logger.debug("Discovering defined simulators ...")

        self._simulator_data_map = dict()
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
                        self._simulator_data_map[simulator.id] = SimulatorData(
                            simulator = simulator,
                        )
                    continue                
                
            except Exception as e:
                logger.exception( f'Problem getting simulator for {module_name}.', e )
            continue

        return
    
    def _discovery_sim_entity_classes(self):
        """
        Query simulators to get the defined subclasses of SimEntity and
        populates the SimulatorData for each simulator.
        """
        for simulator_id, simulator_data in self._simulator_data_map.items():
            simulator = simulator_data.simulator
            sim_entity_class_list = simulator.get_sim_entity_class_list()
            logger.debug( f'Adding {len(sim_entity_class_list)} entity class to simulator {simulator_id}.' )
            for sim_entity_class in sim_entity_class_list:
                sim_entity_class_wrapper = SimEntityClassWrapper( sim_entity_class = sim_entity_class )
                class_name = sim_entity_class_wrapper.name
                simulator_data.sim_entity_class_map[class_name] = sim_entity_class
                continue
            continue
        return

    def _load_sim_entity_instances(self):
        
        db_sim_entity_queryset = DbSimEntity.objects.filter(
            sim_profile = self.current_sim_profile,
        )
        for db_sim_entity in db_sim_entity_queryset:
            simulator_id = db_sim_entity.simulator_id
            simulator_data = self._simulator_data_map.get( simulator_id )
            if not simulator_data:
                logger.warning( f'Instance found for non-existent simulator id = {simulator_id}' )
                continue

            sim_entity_class_map = simulator_data.sim_entity_class_map
            class_name = db_sim_entity.entity_class_name
            sim_entity_class = sim_entity_class_map.get( class_name )
            if not sim_entity_class:
                logger.warning( f'Entity class "{class_name}" not found for simulator "{simulator_id}"' )
                continue
            
            sim_entity = sim_entity_class.from_json_dict( db_sim_entity.editable_fields )
            simulator_data.sim_entity_instance_map[sim_entity] = db_sim_entity
            continue
        return
    
    def _initialize_simulators(self):
        
        for simulator_id, simulator_data in self._simulator_data_map.items():
            sim_entity_list = list( simulator_data.sim_entity_instance_map.keys() )
            logger.debug( f'Initializing simulator {simulator_id} with {len(sim_entity_list)} entities.' )
            simulator_data.simulator.initialize( sim_entity_list = sim_entity_list )
            continue
        return
    
