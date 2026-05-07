"""
Emulated HomeBox REST API endpoints.

Mirrors the subset of the real HomeBox API consumed by the main app's
HomeBox integration:
  - POST /v1/users/login
  - GET  /v1/items
  - GET  /v1/items/<id>
  - GET  /v1/items/<id>/attachments/<key>

The login endpoint accepts any credentials and returns a fixed token. The
token is not validated on subsequent requests. Both the request body
shapes and the response shapes match the real HomeBox API closely enough
for the integration's HbItem parser to consume them unchanged. The
attachment download endpoint serves bytes generated on the fly from
the per-item ``attachment_keys`` configuration plus the catalog in
``attachment_catalog`` — no files on disk.
"""

from django.http import HttpResponse, JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View

from hi.simulator.services.homebox.attachment_catalog import (
    parse_attachment_keys,
    render_attachment_content,
)
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


class AttachmentDownloadView( View ):
    """Serves the binary content for an attachment listed on an item.

    The real HomeBox API exposes ``GET /v1/items/<id>/attachments/<id>``
    returning the raw file with a Content-Type header; the
    integration's ``HbClient.download_attachment`` reads the body
    bytes and the header. Here, the bytes are rendered on demand from
    the catalog so the simulator stays file-management-free; the
    item's name is baked into the rendered content so the operator
    can identify which item an attachment came from when inspecting
    it inside HI.
    """

    def get(self, request, *args, **kwargs):
        item_id = kwargs.get('item_id')
        attachment_id = kwargs.get('attachment_id')

        simulator = HomeBoxSimulator()
        for ( sim_entity_id, fields, _archived_state,
              _created_at, _updated_at ) in simulator.get_sim_entity_pairs():
            if _api_id_for(fields, sim_entity_id) != item_id:
                continue
            templates_by_key = {
                template.key: template
                for template in parse_attachment_keys( fields.attachment_keys )
            }
            template = templates_by_key.get( attachment_id )
            if template is None:
                return JsonResponse(
                    { 'message': f'Attachment {attachment_id} not found' },
                    status = 404,
                )
            rendered = render_attachment_content(
                template = template, item_name = fields.name,
            )
            if not rendered:
                return JsonResponse(
                    { 'message': f'Attachment {attachment_id} not found' },
                    status = 404,
                )
            return HttpResponse(
                rendered['content'],
                content_type = rendered['mime_type'],
            )
        return JsonResponse( { 'message': f'Item {item_id} not found' }, status = 404 )
