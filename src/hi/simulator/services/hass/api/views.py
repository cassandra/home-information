import json
import logging

from django.core.exceptions import BadRequest
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View

from hi.simulator.services.hass.simulator import HassSimulator

logger = logging.getLogger(__name__)


class AllStatesView( View ):

    def get(self, request, *args, **kwargs):
        try:
            hass_simulator = HassSimulator()
            hass_sim_state_list = hass_simulator.get_hass_sim_state_list()
            return JsonResponse( [ x.to_api_dict() for x in hass_sim_state_list ], safe = False )

        except Exception as e:
            logger.exception( 'Problem processing HAss states API request', e )
            return JsonResponse( list(), safe = False )

        
@method_decorator(csrf_exempt, name='dispatch')
class StateView( View ):

    def post(self, request, *args, **kwargs):
        try:
            hass_entity_id = kwargs.get('entity_id')
            data = json.loads( request.body )
            value_str = data.get('state')
            if not value_str:
                raise BadRequest( 'Request body is missing "state" value.' )
            logger.debug( f'HAss set state: {hass_entity_id} = {value_str}' )

            hass_simulator = HassSimulator()
            sim_state = hass_simulator.set_sim_state_by_hass_entity_id(
                hass_entity_id = hass_entity_id,
                value_str = value_str,
            )
            return JsonResponse( sim_state.to_api_dict(), safe = False )
        
        except json.JSONDecodeError as jde:
            raise BadRequest( f'Request body is not JSON: {jde}' )

        except KeyError as ke:
            raise BadRequest( f'Unknown HAss state: {ke}' )
            
