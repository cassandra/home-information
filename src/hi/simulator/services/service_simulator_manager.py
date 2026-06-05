from asgiref.sync import sync_to_async
import logging
import threading
from typing import Dict, List

from django.apps import apps as django_apps

from hi.apps.common.module_utils import import_module_safe
from hi.apps.common.singleton import Singleton

from hi.simulator.profile.profile_manager import ProfileManager

from .base_models import SimEntityDefinition, SimEntityFields
from .exceptions import SimEntityValidationError
from .models import DbSimEntity
from .sim_entity import SimEntity
from .service_simulator import ServiceSimulator
from .service_simulator_data import ServiceSimulatorData

logger = logging.getLogger(__name__)


class ServiceSimulatorManager( Singleton ):
    """Discovers service-simulator sub-apps, hydrates each one's
    entities from its module-specific current profile, and registers
    a reload callback so a profile switch in any module triggers a
    fresh load of that module's entities.

    The cross-cutting "current profile" concept lives in
    ``ProfileManager`` (per-module). This manager only owns the
    per-simulator runtime state (entity instances, definitions).
    """

    def __init_singleton__( self ):
        self._simulator_data_map : Dict[ str, ServiceSimulatorData ] = dict()  # Key = simulator.id
        self._initialized = False
        self._data_lock = threading.Lock()
        return

    def get_simulator( self, simulator_id : str ) -> ServiceSimulator:
        simulator_data = self._simulator_data_map.get( simulator_id )
        if not simulator_data:
            raise KeyError( f'ServiceSimulator id "{simulator_id}" not found.' )
        return simulator_data.simulator

    def get_simulator_data_list( self ) -> List[ ServiceSimulatorData ]:
        simulator_data_list = [ x for x in self._simulator_data_map.values() ]
        simulator_data_list.sort( key = lambda item : item.simulator.label )
        return simulator_data_list

    def reset_all_to_defaults( self ):
        """Re-hydrate every simulator to its current profile's defaults. Sim
        state values aren't persisted, so a reload resets them — used by the
        Scenes 'Clear States' action to start a fresh sequence run clean."""
        self._load_entities_for_all_simulators()
        return

    def add_sim_entity( self,
                        simulator              : ServiceSimulator,
                        sim_entity_definition  : SimEntityDefinition,
                        sim_entity_fields      : SimEntityFields ):

        with self._data_lock:
            simulator_data = self._simulator_data_map.get( simulator.id )
            if not simulator_data:
                raise KeyError( f'No data found for simulator id = {simulator.id}' )

            current_profile = ProfileManager().get_current( simulator.module_key )
            db_sim_entity = DbSimEntity(
                sim_profile = current_profile,
                entity_fields_class_id = sim_entity_definition.class_id,
                sim_entity_type = sim_entity_definition.sim_entity_type,
                sim_entity_fields_json = sim_entity_fields.to_json_dict(),
            )
            simulator.validate_new_sim_entity_fields(
                new_sim_entity_fields = sim_entity_fields,
            )
            db_sim_entity.save()
            sim_entity = SimEntity(
                db_sim_entity = db_sim_entity,
                sim_entity_definition = sim_entity_definition,
            )
            simulator.add_sim_entity( sim_entity = sim_entity )
        return

    def update_sim_entity_fields( self,
                                  simulator              : ServiceSimulator,
                                  sim_entity_definition  : SimEntityDefinition,
                                  db_sim_entity          : DbSimEntity,
                                  sim_entity_fields      : SimEntityFields ):

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
                           simulator      : ServiceSimulator,
                           db_sim_entity  : DbSimEntity ):
        simulator.remove_sim_entity_by_id( sim_entity_id = db_sim_entity.id )
        db_sim_entity.delete()
        return

    async def initialize( self ) -> None:
        with self._data_lock:
            if self._initialized:
                logger.info( 'ServiceSimulatorManager already initialized. Skipping.' )
                return
            self._initialized = True
            logger.info( 'Initializing ServiceSimulatorManager ...' )
            self._discover_defined_simulators()
            self._fetch_sim_entity_definitions()
            self._register_profile_callbacks()
        # Release the lock before per-simulator hydration: each
        # _load_entities_for_simulator acquires the lock for the
        # duration of its own clear+rehydrate, and post_load_hook
        # then calls back through add_sim_entity which re-acquires
        # the lock. Holding the lock across the sync_to_async hop
        # would also block any other thread that tried to acquire it.
        await sync_to_async( self._load_entities_for_all_simulators,
                             thread_sensitive = True )()
        return

    async def shutdown( self ) -> None:
        logger.info( 'Stopping ServiceSimulatorManager...' )
        return

    def _discover_defined_simulators( self ):
        logger.debug( 'Discovering defined simulators ...' )

        self._simulator_data_map = dict()
        for app_config in django_apps.get_app_configs():
            if not app_config.name.startswith( 'hi.simulator.services.' ):
                continue
            module_name = f'{app_config.name}.simulator'
            try:
                app_module = import_module_safe( module_name = module_name )
                if not app_module:
                    logger.debug( f'No simulator module for {app_config.name}' )
                    continue

                logger.debug( f'Found simulator module for {app_config.name}' )

                for attr_name in dir( app_module ):
                    attr = getattr( app_module, attr_name )
                    if ( isinstance( attr, type )
                         and issubclass( attr, ServiceSimulator )
                         and attr is not ServiceSimulator ):
                        logger.debug( f'Found simulator: {attr_name}' )
                        simulator = attr()
                        self._simulator_data_map[simulator.id] = ServiceSimulatorData(
                            simulator = simulator,
                        )
                    continue

            except Exception:
                logger.exception( f'Problem getting simulator for {module_name}.' )
            continue
        return

    def _fetch_sim_entity_definitions( self ):
        logger.debug( 'Fetching simulator entity definitions ...' )

        for simulator_id, simulator_data in self._simulator_data_map.items():
            simulator = simulator_data.simulator
            sim_entity_definition_list = simulator.sim_entity_definition_list
            logger.debug(
                f'Adding {len(sim_entity_definition_list)} entity'
                f' definitions to {simulator_id}.'
            )
            for sim_entity_definition in sim_entity_definition_list:
                class_id = sim_entity_definition.class_id
                simulator_data.sim_entity_definition_map[class_id] = sim_entity_definition
                continue
            continue
        return

    def _register_profile_callbacks( self ):
        for simulator_data in self._simulator_data_map.values():
            simulator = simulator_data.simulator

            def _on_switched( profile, simulator = simulator ):
                self._load_entities_for_simulator(
                    simulator = simulator,
                    profile = profile,
                )
                return

            ProfileManager().register_on_switched(
                module_key = simulator.module_key,
                callback = _on_switched,
            )
            continue
        return

    def _load_entities_for_all_simulators( self ):
        for simulator_data in self._simulator_data_map.values():
            simulator = simulator_data.simulator
            profile = ProfileManager().get_current( simulator.module_key )
            self._load_entities_for_simulator(
                simulator = simulator,
                profile = profile,
            )
            continue
        return

    def _load_entities_for_simulator( self, simulator, profile ):
        logger.debug(
            f'Loading entities for {simulator.id} from profile {profile}.'
        )
        # Hold the lock for the entire clear+rehydrate so concurrent
        # add_sim_entity calls (e.g. an on-demand auto-create racing
        # in via a request while we're mid-hydration) cannot see a
        # partially-populated map and decide a singleton is missing.
        # Without this, the auto-create persists a duplicate row and
        # the duplicate sticks in the DB for that profile thereafter.
        with self._data_lock:
            simulator.initialize()
            simulator_data = self._simulator_data_map.get( simulator.id )
            if simulator_data is None:
                return
            sim_entity_definition_map = simulator_data.sim_entity_definition_map

            for db_sim_entity in DbSimEntity.objects.filter( sim_profile = profile ):
                class_id = db_sim_entity.entity_fields_class_id
                sim_entity_definition = sim_entity_definition_map.get( class_id )
                if not sim_entity_definition:
                    continue
                sim_entity = SimEntity(
                    db_sim_entity = db_sim_entity,
                    sim_entity_definition = sim_entity_definition,
                )
                try:
                    simulator.add_sim_entity( sim_entity = sim_entity )
                except SimEntityValidationError:
                    logger.exception( 'Could not add DB simulator entity.' )
                continue
        # Outside the lock: the hook may call back through
        # add_sim_entity, which re-acquires the lock.
        simulator.post_load_hook()
        return
