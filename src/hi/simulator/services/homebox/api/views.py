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

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View

from hi.simulator.services.homebox.sim_models import build_item_api_dict
from hi.simulator.services.homebox.simulator import HomeBoxSimulator


# Static token returned by the simulator's login endpoint. Not validated
# on subsequent requests; the simulator simply ignores the Authorization
# header.
_STATIC_SIM_TOKEN = 'simulator-token'


@method_decorator(csrf_exempt, name='dispatch')
class LoginView( View ):

    def post(self, request, *args, **kwargs):
        return JsonResponse( { 'token': _STATIC_SIM_TOKEN } )


def _api_id_for(fields, sim_entity_id) -> str:
    """The id rule the simulator's HomeBox API emits for an item.

    Single source of truth so the list view and the detail-by-id
    view agree on identity. Prefer the operator-supplied
    ``item_id`` (stable across profiles); fall back to the row PK
    for items that don't set one.
    """
    return fields.item_id or str(sim_entity_id)


class AllItemsView( View ):

    def get(self, request, *args, **kwargs):
        # No broad except: if entity hydration or dict-building
        # fails for any reason, surface a real 500 with the
        # traceback so problems are visible. Returning an empty
        # items list silently was previously masking real bugs.
        simulator = HomeBoxSimulator()
        items = [
            build_item_api_dict(
                sim_entity_id  = sim_entity_id,
                fields         = fields,
                archived_state = archived_state,
                created_at     = created_at,
                updated_at     = updated_at,
            )
            for ( sim_entity_id, fields, archived_state,
                  created_at, updated_at )
            in simulator.get_sim_entity_pairs()
        ]
        return JsonResponse( { 'items': items } )


class ItemDetailView( View ):

    def get(self, request, *args, **kwargs):
        item_id = kwargs.get('item_id')
        simulator = HomeBoxSimulator()
        for ( sim_entity_id, fields, archived_state,
              created_at, updated_at ) in simulator.get_sim_entity_pairs():
            if _api_id_for(fields, sim_entity_id) == item_id:
                return JsonResponse( build_item_api_dict(
                    sim_entity_id  = sim_entity_id,
                    fields         = fields,
                    archived_state = archived_state,
                    created_at     = created_at,
                    updated_at     = updated_at,
                ))
        return JsonResponse( { 'message': f'Item {item_id} not found' }, status = 404 )
