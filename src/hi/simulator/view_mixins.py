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
        """ Side effect of setting current simulator in session. """
        simulator_id = kwargs.get('simulator_id')
        simulator = self.get_simulator_by_id( simulator_id = simulator_id )
        self.set_current_simulator(
            request = request,
            simulator = simulator,
        )
        return simulator

    def get_simulator_by_id( self, simulator_id : str ) -> Simulator:
        if not simulator_id:
            raise BadRequest( 'Missing simulator id.' )
        simulator = SimulatorManager().get_simulator( simulator_id = simulator_id )
        if not simulator:
            raise Http404( 'Unknown simulator id "{simulator_id}".' )
        return simulator

    def get_entity_class_data( self, simulator : Simulator, request, *args, **kwargs ) -> Type[ SimEntity ]:
        class_id = kwargs.get('class_id')
        return self.get_entity_class_data_by_id(
            simulator = simulator,
            class_id = class_id,
        )
    
    def get_entity_class_data_by_id( self, simulator : Simulator, class_id : str ) -> Type[ SimEntity ]:
        for sim_entity_class_data in simulator.sim_entity_class_data_list:
            if class_id == sim_entity_class_data.class_id:
                return sim_entity_class_data
            continue
        raise Http404( 'Unknown entity class id.' )
    
    def get_db_sim_entity( self, request, *args, **kwargs ) -> SimProfile:
        db_sim_entity_id = kwargs.get('sim_entity_id')
        try:
            return DbSimEntity.objects.get( id = db_sim_entity_id )
        except DbSimEntity.DoesNotExist:
            raise Http404( 'Simulator entity does not exist.' )
