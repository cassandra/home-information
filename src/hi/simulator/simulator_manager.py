from asgiref.sync import sync_to_async
import logging
import threading
from typing import Dict, List

from django.apps import apps as django_apps

import hi.apps.common.datetimeproxy as datetimeproxy
from hi.apps.common.module_utils import import_module_safe
from hi.apps.common.singleton import Singleton

from .base_models import SimEntityDefinition, SimEntityFields
from .exceptions import SimEntityValidationError
from .models import DbSimEntity, SimProfile
from .sim_entity import SimEntity
from .simulator import Simulator
from .simulator_data import SimulatorData

logger = logging.getLogger(__name__)


class SimulatorManager( Singleton ):

    DEFAULT_PROFILE_NAME = 'Default'
    
    def __init_singleton__( self ):
        self._current_sim_profile = None
        self._simulator_data_map : Dict[ str, SimulatorData ] = dict()  # Key = simulator.id
        self._initialized = False
        self._data_lock = threading.Lock()
        return

    @property
    def sim_profile_list(self) -> List[ SimProfile ]:
        return list( SimProfile.objects.all().order_by('name') )

    @property
    def current_sim_profile(self) -> SimProfile:
        return self._current_sim_profile

    def set_sim_profile( self, sim_profile : SimProfile ):
        should_reload_instances = bool( not sim_profile
                                        or ( sim_profile != self._current_sim_profile ))
        if not sim_profile:
            self._initialize_sim_profile()
        else:
            sim_profile.last_switched_to_datetime = datetimeproxy.now()
            sim_profile.save()
            self._current_sim_profile = sim_profile

        if should_reload_instances:
            self._load_sim_entity_instances()            
        return
        
    def get_simulator( self, simulator_id : str ) -> Simulator:
        simulator_data = self._simulator_data_map.get( simulator_id )
        if not simulator_data:
            raise KeyError( f'Simulator id "{simulator_id}" not found.' )
        return simulator_data.simulator
    
    def get_simulator_data_list(self) -> List[ SimulatorData ]:
        simulator_data_list = [ x for x in self._simulator_data_map.values() ]
        simulator_data_list.sort( key = lambda item : item.simulator.label )
        return simulator_data_list

    def add_sim_entity( self,
                        simulator              : Simulator,
                        sim_entity_definition  : SimEntityDefinition,
                        sim_entity_fields      : SimEntityFields ):
        
        with self._data_lock:
            simulator_data = self._simulator_data_map.get( simulator.id )
            if not simulator_data:
                raise KeyError( f'No data found for simulator id = {simulator.id}' )
            
            db_sim_entity = DbSimEntity(
                sim_profile = self.current_sim_profile,
                simulator_id = simulator.id,
                entity_fields_class_id = sim_entity_definition.class_id,
                sim_entity_type = sim_entity_definition.sim_entity_type,
                sim_entity_fields_json = sim_entity_fields.to_json_dict(),
            )

            simulator.validate_new_sim_entity_fields( new_sim_entity_fields = sim_entity_fields )
            db_sim_entity.save()
            sim_entity = SimEntity(
                db_sim_entity = db_sim_entity,
                sim_entity_definition = sim_entity_definition,
            )
            simulator.add_sim_entity( sim_entity = sim_entity )
                                    
    def update_sim_entity_fields( self,
                                  simulator          : Simulator,
                                  sim_entity_definition  : SimEntityDefinition,
                                  db_sim_entity      : DbSimEntity,
                                  sim_entity_fields  : SimEntityFields ):

        with self._data_lock:
            simulator_data = self._simulator_data_map.get( simulator.id )
            if not simulator_data:
                raise KeyError( f'No data found for simulator id = {simulator.id}' )

            db_sim_entity.sim_entity_fields_json = sim_entity_fields.to_json_dict()

            sim_entity = SimEntity(
                db_sim_entity = db_sim_entity,
                sim_entity_definition = sim_entity_definition,
            )
            simulator.validate_updated_sim_entity( updated_sim_entity = sim_entity )
            db_sim_entity.save()
            simulator.add_sim_entity( sim_entity = sim_entity )

        return
        
    def delete_sim_entity( self,
                           simulator      : Simulator,
                           db_sim_entity  : DbSimEntity ):
        simulator.remove_sim_entity_by_id( sim_entity_id = db_sim_entity.id )
        db_sim_entity.delete()
        return
        
    async def initialize(self) -> None:
        with self._data_lock:
            if self._initialized:
                logger.info("SimulationManager already initialize. Skipping.")
                return
            self._initialized = True
            logger.info("Initializing SimulationManager ...")
            await sync_to_async( self._initialize_sim_profile,
                                 thread_sensitive = True )()
            self._discover_defined_simulators()
            self._fetch_sim_entity_definitions()
            await sync_to_async( self._load_sim_entity_instances,
                                 thread_sensitive = True )()

        return

    async def shutdown(self) -> None:
        # Nothing yet
        logger.info("Stopping SimulationManager...")
        return
    
    def _initialize_sim_profile(self):
        logger.debug("Initialize SimProfile ...")
        self._current_sim_profile = SimProfile.objects.all().first()  # Default ordering is by recency use
        if not self._current_sim_profile:
            self._current_sim_profile = SimProfile.objects.create(
                name = self.DEFAULT_PROFILE_NAME,
                last_switched_to_datetime = datetimeproxy.now(),
            )
        return

    def _discover_defined_simulators(self):
        logger.debug("Discovering defined simulators ...")

        self._simulator_data_map = dict()
        for app_config in django_apps.get_app_configs():
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
    
    def _fetch_sim_entity_definitions(self):
        """
        Query simulators to get the defined subclasses of SimEntity and
        populates the SimulatorData for each simulator.
        """
        logger.debug("Fetching simulator entity definitions ...")

        for simulator_id, simulator_data in self._simulator_data_map.items():
            simulator = simulator_data.simulator
            sim_entity_definition_list = simulator.sim_entity_definition_list
            logger.debug( f'Adding {len(sim_entity_definition_list)} entity definitions to {simulator_id}.' )
            for sim_entity_definition in sim_entity_definition_list:
                class_id = sim_entity_definition.class_id
                simulator_data.sim_entity_definition_map[class_id] = sim_entity_definition
                continue
            continue
        return

    def _load_sim_entity_instances(self):

        logger.debug("Initializing simulators ...")
        for simulator_id, simulator_data in self._simulator_data_map.items():
            simulator_data.simulator.initialize()
            continue
        
        logger.debug("Loading saved simulator entities ...")
        db_sim_entity_queryset = DbSimEntity.objects.filter(
            sim_profile = self.current_sim_profile,
        )
        for db_sim_entity in db_sim_entity_queryset:
            simulator_id = db_sim_entity.simulator_id
            simulator_data = self._simulator_data_map.get( simulator_id )
            if not simulator_data:
                logger.warning( f'Instance found for non-existent simulator id = {simulator_id}' )
                continue
            
            sim_entity_definition_map = simulator_data.sim_entity_definition_map
            class_id = db_sim_entity.entity_fields_class_id
            sim_entity_definition = sim_entity_definition_map.get( class_id )
            if not sim_entity_definition:
                logger.warning( f'Entity class "{class_id}" not found for simulator "{simulator_id}"' )
                continue

            sim_entity = SimEntity(
                db_sim_entity = db_sim_entity,
                sim_entity_definition = sim_entity_definition,
            )
            try:
                simulator_data.simulator.add_sim_entity( sim_entity = sim_entity )
            except SimEntityValidationError as ve:
                logger.exception( 'Could not add DB simulator entity.', ve )
            continue
        
        return
