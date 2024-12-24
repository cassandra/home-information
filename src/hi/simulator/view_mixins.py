from typing import List, Type

from django.core.exceptions import BadRequest
from django.http import Http404, HttpRequest

from .models import DbSimEntity, SimProfile
from .simulator import Simulator
from .simulator_manager import SimulatorManager
from .transient_models import SimEntity


class SimulatorViewMixin:

    def get_current_simulator( self,
                               request         : HttpRequest,
                               simulator_list  : List[ Simulator ] ) -> Simulator:
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
                               simulator  : Simulator ):
        request.sim_view_parameters.simulator_id = simulator.id
        request.sim_view_parameters.to_session( request )
        return

    def get_sim_profile( self, request, *args, **kwargs) -> SimProfile:
        sim_profile_id = kwargs.get('profile_id')
        try:
            return SimProfile.objects.get( id = sim_profile_id )
        except SimProfile.DoesNotExist:
            raise Http404( 'Simulator profile does not exist.' )
        
    def get_simulator( self, request, *args, **kwargs ) -> Simulator:
        simulator_id = kwargs.get('simulator_id')
        if not simulator_id:
            raise BadRequest( 'Missing simulator id.' )
        simulator = SimulatorManager().get_simulator( simulator_id = simulator_id )
        if not simulator:
            raise Http404( 'Unknown simulator id "{simulator_id}".' )
        self.set_current_simulator(
            request = request,
            simulator = simulator,
        )
        return simulator

    def get_entity_class( self, simulator : Simulator, request, *args, **kwargs ) -> Type[ SimEntity ]:
        class_name = kwargs.get('class_name')
        return self.get_entity_class_by_name(
            simulator = simulator,
            class_name = class_name,
        )
    
    def get_entity_class_by_name( self, simulator : Simulator, class_name : str ) -> Type[ SimEntity ]:
        sim_entity_class = None
        for sim_entity_class_wrapper in simulator.sim_entity_class_wrapper_list:
            if class_name == sim_entity_class_wrapper.name:
                sim_entity_class = sim_entity_class_wrapper.sim_entity_class
                break
            continue
        if not sim_entity_class:
            raise Http404( 'Unknown entity class name.' )
        return sim_entity_class
    
    def get_db_sim_entity( self, request, *args, **kwargs ) -> SimProfile:
        db_sim_entity_id = kwargs.get('sim_entity_id')
        try:
            return DbSimEntity.objects.get( id = db_sim_entity_id )
        except DbSimEntity.DoesNotExist:
            raise Http404( 'Simulator entity does not exist.' )
