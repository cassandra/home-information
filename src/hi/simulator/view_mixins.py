from typing import List

from django.http import Http404, HttpRequest

from .models import SimProfile
from .simulator import Simulator


class SimulatorViewMixin:

    def get_current_simulator( self,
                               request         : HttpRequest,
                               simulator_list  : List[ Simulator ] ) -> Simulator:
        if not simulator_list:
            return None
        current_simulator_id = request.sim_view_parameters.simulator_id
        current_simulator = simulator_list[0]
        for simulator in simulator_list:
            if simulator.id == current_simulator_id:
                current_simulator = simulator
                break
            continue
        return current_simulator

    def get_sim_profile( self, request, *args, **kwargs):
        sim_profile_id = kwargs.get('profile_id')
        try:
            return SimProfile.objects.get( id = sim_profile_id )
        except SimProfile.DoesNotExist:
            raise Http404( 'Simulator profile does not exist.' )
        
