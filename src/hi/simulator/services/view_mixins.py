from django.core.exceptions import BadRequest
from django.http import Http404

from .models import DbSimEntity
from .service_simulator import ServiceSimulator
from .service_simulator_manager import ServiceSimulatorManager
from .base_models import SimEntityDefinition


class ServiceSimulatorViewMixin:

    def get_simulator( self, request, *args, **kwargs ) -> ServiceSimulator:
        simulator_id = kwargs.get( 'simulator_id' )
        return self.get_simulator_by_id( simulator_id = simulator_id )

    def get_simulator_by_id( self, simulator_id : str ) -> ServiceSimulator:
        if not simulator_id:
            raise BadRequest( 'Missing simulator id.' )
        simulator = ServiceSimulatorManager().get_simulator( simulator_id = simulator_id )
        if not simulator:
            raise Http404( f'Unknown simulator id "{simulator_id}".' )
        return simulator

    def get_entity_definition( self,
                               simulator : ServiceSimulator,
                               request, *args, **kwargs ) -> SimEntityDefinition:
        class_id = kwargs.get( 'class_id' )
        return self.get_entity_definition_by_id(
            simulator = simulator,
            class_id = class_id,
        )

    def get_entity_definition_by_id( self,
                                     simulator : ServiceSimulator,
                                     class_id  : str ) -> SimEntityDefinition:
        for sim_entity_definition in simulator.sim_entity_definition_list:
            if class_id == sim_entity_definition.class_id:
                return sim_entity_definition
            continue
        raise Http404( 'Unknown entity class id.' )

    def get_db_sim_entity( self, request, *args, **kwargs ) -> DbSimEntity:
        db_sim_entity_id = kwargs.get( 'sim_entity_id' )
        try:
            return DbSimEntity.objects.get( id = db_sim_entity_id )
        except DbSimEntity.DoesNotExist:
            raise Http404( 'Simulator entity does not exist.' )
