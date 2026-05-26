"""
Emulated HomeBox REST API endpoints.

Mirrors the subset of the real HomeBox API consumed by the main app's
HomeBox integration. Two endpoint families are served, switched by
the simulator's ``api_version`` setting:

  - v0.25 mode (default): ``/v1/items/*``
      - POST /v1/users/login
      - GET  /v1/items
      - GET  /v1/items/<id>
      - GET  /v1/items/<id>/attachments/<key>
  - v0.26 mode: ``/v1/entities/*`` (the "entity merge")
      - GET  /v1/entities
      - GET  /v1/entities/<id>
      - GET  /v1/entities/<id>/attachments/<key>

When the simulator is in the "wrong" mode for a given URL family
the view returns 404 — that's what lets the integration's version
probe (which 404-detects) resolve correctly against the simulator.

The login endpoint accepts any credentials and is served in either
mode (auth wasn't affected by the entity merge). Attachment download
URL shape changes paths but the response shape is identical between
versions.
"""

from django.http import HttpResponse, JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View

from hi.simulator.services.homebox.attachment_catalog import (
    parse_attachment_keys,
    render_attachment_content,
)
from hi.simulator.services.homebox.sim_models import (
    build_entity_api_dict,
    build_item_api_dict,
    build_paginated_envelope,
)
from hi.simulator.services.homebox.simulator import HbApiVersion, HomeBoxSimulator


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


def _not_found( message: str ) -> JsonResponse:
    return JsonResponse( { 'message': message }, status = 404 )


# ----- v0.25 ``/v1/items/*`` views ------------------------------------


class _LegacyOnlyMixin:
    """Returns 404 when the simulator is in v0.26 mode so the
    version probe in the integration's client factory correctly
    detects the absence of the legacy endpoints."""

    def _legacy_mode_active( self, simulator: HomeBoxSimulator ) -> bool:
        return simulator.api_version is HbApiVersion.V0_25


class AllItemsView( View, _LegacyOnlyMixin ):

    def get(self, request, *args, **kwargs):
        simulator = HomeBoxSimulator()
        if not self._legacy_mode_active( simulator ):
            return _not_found( 'Legacy items endpoint not served in v0.26 mode' )
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


class ItemDetailView( View, _LegacyOnlyMixin ):

    def get(self, request, *args, **kwargs):
        item_id = kwargs.get('item_id')
        simulator = HomeBoxSimulator()
        if not self._legacy_mode_active( simulator ):
            return _not_found( f'Item {item_id} not found' )
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
        return _not_found( f'Item {item_id} not found' )


def _serve_attachment( request, item_id, attachment_id, simulator ):
    """Common attachment-serving logic for both API versions; the
    URL path differs but the response is identical."""
    thumbnail_suffix = '-thumb'
    is_thumbnail = attachment_id.endswith( thumbnail_suffix )
    lookup_key = (
        attachment_id[:-len(thumbnail_suffix)]
        if is_thumbnail else attachment_id
    )

    for ( sim_entity_id, fields, _archived_state,
          _created_at, _updated_at ) in simulator.get_sim_entity_pairs():
        if _api_id_for(fields, sim_entity_id) != item_id:
            continue
        templates_by_key = {
            template.key: template
            for template in parse_attachment_keys( fields.attachment_keys )
        }
        template = templates_by_key.get( lookup_key )
        if template is None:
            return _not_found( f'Attachment {attachment_id} not found' )
        if is_thumbnail and template.kind != 'image':
            return _not_found( f'Attachment {attachment_id} not found' )
        rendered = render_attachment_content(
            template = template,
            item_name = fields.name,
            thumbnail = is_thumbnail,
        )
        if not rendered:
            return _not_found( f'Attachment {attachment_id} not found' )
        return HttpResponse(
            rendered['content'],
            content_type = rendered['mime_type'],
        )
    return _not_found( f'Item {item_id} not found' )


class AttachmentDownloadView( View, _LegacyOnlyMixin ):
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
        simulator = HomeBoxSimulator()
        if not self._legacy_mode_active( simulator ):
            return _not_found( 'Legacy attachment endpoint not served in v0.26 mode' )
        return _serve_attachment(
            request,
            item_id = kwargs.get('item_id'),
            attachment_id = kwargs.get('attachment_id'),
            simulator = simulator,
        )


# ----- v0.26 ``/v1/entities/*`` views ---------------------------------


class _EntitiesOnlyMixin:
    """Returns 404 when the simulator is in v0.25 mode so the
    integration's version probe falls back to the legacy
    endpoints correctly."""

    def _entities_mode_active( self, simulator: HomeBoxSimulator ) -> bool:
        return simulator.api_version is HbApiVersion.V0_26


class AllEntitiesView( View, _EntitiesOnlyMixin ):

    def get(self, request, *args, **kwargs):
        simulator = HomeBoxSimulator()
        if not self._entities_mode_active( simulator ):
            return _not_found( 'Entities endpoint not served in v0.25 mode' )
        entities = [
            build_entity_api_dict(
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
        return JsonResponse( build_paginated_envelope( entities ) )


class EntityDetailView( View, _EntitiesOnlyMixin ):

    def get(self, request, *args, **kwargs):
        entity_id = kwargs.get('entity_id')
        simulator = HomeBoxSimulator()
        if not self._entities_mode_active( simulator ):
            return _not_found( f'Entity {entity_id} not found' )
        for ( sim_entity_id, fields, archived_state,
              created_at, updated_at ) in simulator.get_sim_entity_pairs():
            if _api_id_for(fields, sim_entity_id) == entity_id:
                return JsonResponse( build_entity_api_dict(
                    sim_entity_id  = sim_entity_id,
                    fields         = fields,
                    archived_state = archived_state,
                    created_at     = created_at,
                    updated_at     = updated_at,
                ))
        return _not_found( f'Entity {entity_id} not found' )


class EntityAttachmentDownloadView( View, _EntitiesOnlyMixin ):
    """v0.26 attachment download. Same response shape as the
    legacy view; only the URL path changed."""

    def get(self, request, *args, **kwargs):
        simulator = HomeBoxSimulator()
        if not self._entities_mode_active( simulator ):
            return _not_found( 'Entities attachment endpoint not served in v0.25 mode' )
        return _serve_attachment(
            request,
            item_id = kwargs.get('entity_id'),
            attachment_id = kwargs.get('attachment_id'),
            simulator = simulator,
        )
