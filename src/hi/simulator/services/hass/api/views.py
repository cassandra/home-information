import json
import logging

from django.core.exceptions import BadRequest
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View

from hi.simulator.services.hass.simulator import HassSimulator

logger = logging.getLogger(__name__)


# Service-call mapping for the limited set of entity types the simulator
# supports (switches, outlets, dimmer light switches). Keys are
# (domain, service) tuples; values are the target state value the
# simulator should set on the addressed entity.
#
# Sensors (motion, open/close) are read-only and accept no service calls.
_SUPPORTED_SERVICES = {
    ( 'switch', 'turn_on' ): 'on',
    ( 'switch', 'turn_off' ): 'off',
    ( 'light', 'turn_on' ): 'on',
    ( 'light', 'turn_off' ): 'off',
}


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


@method_decorator(csrf_exempt, name='dispatch')
class ServiceCallView( View ):
    """
    Handles HAss service calls:
        POST /api/services/<domain>/<service>

    Mirrors the real Home Assistant REST API (see
    https://developers.home-assistant.io/docs/api/rest/#post-apiservicesdomainservice).
    The response is a JSON list of state objects for the entities that
    were changed.

    Only the services emitted by Home Information's HAss controller for
    the hard-coded simulator entity types (switch/light turn_on/turn_off)
    are supported. Brightness data on light.turn_on is accepted but not
    modeled — the simulator's dimmer states are ON_OFF only.
    """

    def post(self, request, *args, **kwargs):
        try:
            domain = kwargs.get('domain')
            service = kwargs.get('service')

            try:
                data = json.loads( request.body ) if request.body else dict()
            except json.JSONDecodeError as jde:
                raise BadRequest( f'Request body is not JSON: {jde}' )

            target_state = _SUPPORTED_SERVICES.get( (domain, service) )
            if target_state is None:
                logger.warning( f'Unsupported HAss service: {domain}.{service}' )
                return JsonResponse(
                    { 'message': f'Service {domain}.{service} not supported by simulator' },
                    status = 400,
                )

            entity_id_field = data.get('entity_id')
            if not entity_id_field:
                raise BadRequest( '"entity_id" is required in service call body.' )
            if isinstance( entity_id_field, list ):
                entity_id_list = entity_id_field
            else:
                entity_id_list = [ entity_id_field ]

            hass_simulator = HassSimulator()
            changed_states = list()
            for hass_entity_id in entity_id_list:
                try:
                    sim_state = hass_simulator.set_sim_state_by_hass_entity_id(
                        hass_entity_id = hass_entity_id,
                        value_str = target_state,
                    )
                    changed_states.append( sim_state.to_api_dict() )
                except KeyError:
                    # Real HA silently no-ops on unknown entity_ids in
                    # service calls; mirror that behavior.
                    logger.warning( f'HAss entity not found: {hass_entity_id}' )
                continue

            logger.debug(
                f'HAss service call: {domain}.{service} on {entity_id_list} '
                f'-> {target_state} ({len(changed_states)} changed)'
            )
            return JsonResponse( changed_states, safe = False )

        except BadRequest:
            raise

        except Exception as e:
            logger.exception( 'Problem processing HAss service call', e )
            return JsonResponse( list(), safe = False )
