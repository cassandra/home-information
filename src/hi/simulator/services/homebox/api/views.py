"""
Emulated HomeBox REST API endpoints.

Mirrors the subset of the real HomeBox API consumed by the main app's
HomeBox integration:
  - POST /v1/users/login
  - GET  /v1/items
  - GET  /v1/items/<id>

The login endpoint accepts any credentials and returns a fixed token. The
token is not validated on subsequent requests. Both the request body
shapes and the response shapes match the real HomeBox API closely enough
for the integration's HbItem parser to consume them unchanged.
"""

import logging

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View

from hi.simulator.services.homebox.sim_models import build_item_api_dict
from hi.simulator.services.homebox.simulator import HomeBoxSimulator

logger = logging.getLogger(__name__)


# Static token returned by the simulator's login endpoint. Not validated
# on subsequent requests; the simulator simply ignores the Authorization
# header.
_STATIC_SIM_TOKEN = 'simulator-token'


@method_decorator(csrf_exempt, name='dispatch')
class LoginView( View ):

    def post(self, request, *args, **kwargs):
        return JsonResponse( { 'token': _STATIC_SIM_TOKEN } )


class AllItemsView( View ):

    def get(self, request, *args, **kwargs):
        try:
            simulator = HomeBoxSimulator()
            items = [
                build_item_api_dict(
                    sim_entity_id  = sim_entity_id,
                    fields         = fields,
                    archived_state = archived_state,
                )
                for ( sim_entity_id, fields, archived_state )
                in simulator.get_sim_entity_pairs()
            ]
            return JsonResponse( { 'items': items } )

        except Exception:
            logger.exception( 'Problem processing HomeBox items list' )
            return JsonResponse( { 'items': [] } )


class ItemDetailView( View ):

    def get(self, request, *args, **kwargs):
        item_id = kwargs.get('item_id')
        simulator = HomeBoxSimulator()
        for ( sim_entity_id, fields, archived_state ) in simulator.get_sim_entity_pairs():
            if str(sim_entity_id) == item_id:
                return JsonResponse( build_item_api_dict(
                    sim_entity_id  = sim_entity_id,
                    fields         = fields,
                    archived_state = archived_state,
                ))
        return JsonResponse( { 'message': f'Item {item_id} not found' }, status = 404 )
