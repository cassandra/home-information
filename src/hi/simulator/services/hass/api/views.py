import json
import logging

from django.core.exceptions import BadRequest
from django.http import HttpResponse, JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View

from hi.simulator.media import render_jpeg_frame
from hi.simulator.services.hass.api_composers import HassApiComposer
from hi.simulator.services.hass.service_dispatchers import HassServiceDispatcher
from hi.simulator.services.hass.simulator import HassSimulator

logger = logging.getLogger(__name__)


class PingView( View ):
    """
    Mirrors the real Home Assistant API root endpoint, which returns a
    small JSON envelope confirming the API is running. Used by
    `HassClient.ping()` as a lightweight reachability + content-type
    probe so validate_access can fail quickly when the configured base
    URL points at the wrong place.
    """

    def get(self, request, *args, **kwargs):
        return JsonResponse( { 'message': 'API running.' } )


class AllStatesView( View ):

    def get(self, request, *args, **kwargs):
        try:
            hass_simulator = HassSimulator()
            # Compose per-entity rather than per-state so devices
            # whose HA shape is "one entity with attributes from
            # multiple SimStates" (color smart bulbs, future
            # climate entities) get collapsed correctly. Devices
            # without a registered composer use the default
            # one-state-per-HA-entity behavior, preserving the
            # existing motion-detector / switch / sensor shapes.
            api_dicts = []
            for sim_entity in hass_simulator.sim_entities:
                api_dicts.extend( HassApiComposer.compose( sim_entity ) )
            return JsonResponse( api_dicts, safe = False )

        except Exception:
            logger.exception( 'Problem processing HAss states API request' )
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

    Service-call → SimState translation is delegated to
    ``HassServiceDispatcher`` so per-device-type behavior (single-state
    on/off, dimmer brightness, color-bulb hs/temp routing) lives in
    one place rather than as a hard-coded mapping table here.
    """

    def post(self, request, *args, **kwargs):
        try:
            domain = kwargs.get('domain')
            service = kwargs.get('service')

            try:
                data = json.loads( request.body ) if request.body else dict()
            except json.JSONDecodeError as jde:
                raise BadRequest( f'Request body is not JSON: {jde}' )

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
                sim_entity = hass_simulator.find_sim_entity_by_hass_entity_id(
                    hass_entity_id = hass_entity_id,
                )
                if sim_entity is None:
                    # Real HA silently no-ops on unknown entity_ids
                    # in service calls; mirror that behavior.
                    logger.warning( f'HAss entity not found: {hass_entity_id}' )
                    continue

                updates = HassServiceDispatcher.dispatch(
                    sim_entity = sim_entity,
                    domain = domain,
                    service = service,
                    payload = data,
                )
                if not updates:
                    logger.warning(
                        f'Unsupported HAss service for {hass_entity_id}: '
                        f'{domain}.{service}'
                    )
                    continue

                for sim_state_id, value_str in updates:
                    sim_state = sim_entity.set_sim_state(
                        sim_state_id = sim_state_id,
                        value_str = value_str,
                    )
                    changed_states.append( sim_state.to_api_dict() )
                    continue
                continue

            logger.debug(
                f'HAss service call: {domain}.{service} on {entity_id_list} '
                f'({len(changed_states)} state(s) changed)'
            )
            return JsonResponse( changed_states, safe = False )

        except BadRequest:
            raise

        except Exception:
            logger.exception( 'Problem processing HAss service call' )
            return JsonResponse( list(), safe = False )


class CameraSnapshotView( View ):
    """Mirrors HA's ``/api/camera_proxy/<entity_id>`` endpoint, which
    returns a single JPEG of the camera's current view. The simulator
    accepts any ``token`` query param (real HA validates the rotating
    ``access_token``); the goal here is shape parity with HA's URL
    contract, not auth enforcement.

    Returns a Pillow-rendered placeholder JPEG with the entity_id
    overlaid so artifacts viewed inside HI are obviously coming from
    the simulator and from a specific camera."""

    def get(self, request, entity_id, *args, **kwargs):
        jpeg_bytes = render_jpeg_frame(
            text_lines = [
                'HA Camera',
                entity_id,
            ],
        )
        return HttpResponse( jpeg_bytes, content_type = 'image/jpeg' )
