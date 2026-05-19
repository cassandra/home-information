from typing import List

from django.core.exceptions import BadRequest
from django.http import Http404, HttpRequest

from .models import DbSimEntity, SimProfile
from .service_simulator import ServiceSimulator
from .service_simulator_manager import ServiceSimulatorManager
from .base_models import SimEntityDefinition


class ServiceSimulatorViewMixin:

    def get_current_simulator( self,
                               request         : HttpRequest,
                               simulator_list  : List[ ServiceSimulator ] ) -> ServiceSimulator:
        if not simulator_list:
            return None
        current_simulator_id = request.sim_view_parameters.simulator_id
        for simulator in simulator_list:
            if simulator.id == current_simulator_id:
                return simulator
            continue
        return simulator_list[0]

    def set_current_simulator( self,
                               request    : HttpRequest,
                               simulator  : ServiceSimulator ):
        request.sim_view_parameters.simulator_id = simulator.id
        request.sim_view_parameters.to_session( request )
        return

    def get_sim_profile( self, request, *args, **kwargs) -> SimProfile:
        sim_profile_id = kwargs.get('profile_id')
        try:
            return SimProfile.objects.get( id = sim_profile_id )
        except SimProfile.DoesNotExist:
            raise Http404( 'ServiceSimulator profile does not exist.' )
        
    def get_simulator( self, request, *args, **kwargs ) -> ServiceSimulator:
        """ Side effect of setting current simulator in session. """
        simulator_id = kwargs.get('simulator_id')
        simulator = self.get_simulator_by_id( simulator_id = simulator_id )
        self.set_current_simulator(
            request = request,
            simulator = simulator,
        )
        return simulator

    def get_simulator_by_id( self, simulator_id : str ) -> ServiceSimulator:
        if not simulator_id:
            raise BadRequest( 'Missing simulator id.' )
        simulator = ServiceSimulatorManager().get_simulator( simulator_id = simulator_id )
        if not simulator:
            raise Http404( 'Unknown simulator id "{simulator_id}".' )
        return simulator

    def get_entity_definition( self,
                               simulator : ServiceSimulator,
                               request, *args, **kwargs ) -> SimEntityDefinition:
        class_id = kwargs.get('class_id')
        return self.get_entity_definition_by_id(
            simulator = simulator,
            class_id = class_id,
        )
    
    def get_entity_definition_by_id( self, simulator : ServiceSimulator, class_id : str ) -> SimEntityDefinition:
        for sim_entity_definition in simulator.sim_entity_definition_list:
            if class_id == sim_entity_definition.class_id:
                return sim_entity_definition
            continue
        raise Http404( 'Unknown entity class id.' )
    
    def get_db_sim_entity( self, request, *args, **kwargs ) -> SimProfile:
        db_sim_entity_id = kwargs.get('sim_entity_id')
        try:
            return DbSimEntity.objects.get( id = db_sim_entity_id )
        except DbSimEntity.DoesNotExist:
            raise Http404( 'ServiceSimulator entity does not exist.' )
