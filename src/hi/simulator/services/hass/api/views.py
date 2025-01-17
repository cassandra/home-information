import logging

from django.http import JsonResponse
from django.views.generic import View

from hi.simulator.services.hass.simulator import HassSimulator

logger = logging.getLogger(__name__)


class StatesView( View ):

    def get(self, request, *args, **kwargs):
        try:
            hass_simulator = HassSimulator()
            zm_monitor_sim_entity_list = hass_simulator.get_hass_sim_state_list()
            return JsonResponse( [ x.to_api_dict() for x in zm_monitor_sim_entity_list ], safe = False )

        except Exception as e:
            logger.exception( 'Problem processing HAss states API request', e )
            return JsonResponse( list(), safe = False )

    def post(self, request, *args, **kwargs):
        pass
    
