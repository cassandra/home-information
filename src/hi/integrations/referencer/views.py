"""
ATTRIBUTE_REFERENCE picker — one HiModal view backed by antinode
partial swaps.

Workflow:

  - GET ``/integrations/referencer/picker/`` with ``item_type`` +
    ``item_id`` query params renders the full picker modal. The
    action-bar "LINK" button in EntityEdit / LocationEdit opens
    the modal via ``data-async="modal"``. The view discovers all
    currently-enabled ATTRIBUTE_REFERENCE integrations and lets
    the operator choose between them via an in-modal selector
    when more than one is configured.

  - POST to the same URL re-renders the picker body. The form
    carries ``integration_id`` as a hidden field so the view knows
    which referencer to drive the search against. The form's
    ``data-async="#picker-body-<uuid>"`` + ``data-stay-in-modal``
    keeps the modal open while the body partial swaps in.

  - When the operator submits with ``action=attach``, the view
    creates one TEXT attribute per current selection on the host
    Entity / Location and returns ``antinode.refresh_response()`` to
    reload the parent page (modal closes via page reload).

Multi-select state is server-driven via three form fields:
``selections_json`` (canonical existing list, hidden), ``visible_url``
(hidden per result; identifies what was rendered), and ``result_url``
(checkbox value per result; only submitted when checked). The view
computes the new selection list each POST: existing + newly checked
- unchecked visibles ± an explicit ``remove_url`` if the operator
clicked a chip's × button.
"""

import json
import logging
import uuid
from typing import Dict, List

from django.core.exceptions import BadRequest
from django.db import transaction
from django.http import Http404
from django.template.loader import render_to_string

from hi.apps.attribute.enums import AttributeType, AttributeValueType
from hi.apps.common import antinode
from hi.apps.entity.models import Entity, EntityAttribute
from hi.apps.location.models import Location, LocationAttribute
from hi.enums import ItemType
from hi.hi_async_view import HiModalView

from hi.integrations.enums import IntegrationCapability
from hi.integrations.integration_data import IntegrationData
from hi.integrations.integration_manager import IntegrationManager

from .integration_attribute_referencer import IntegrationAttributeReferencer
from .transient_models import AttributeReferenceResult, WireField


logger = logging.getLogger(__name__)


class AttributeReferencePickerView( HiModalView ):

    MAX_LIMIT = 100
    DEFAULT_LIMIT = 20
    PAGE_SIZE_CHOICES = (20, 50, 100)

    # ItemType → (owner model, attribute model, owner FK field name).
    ATTRIBUTE_OWNER_MODELS = {
        ItemType.ENTITY: (Entity, EntityAttribute, 'entity'),
        ItemType.LOCATION: (Location, LocationAttribute, 'location'),
    }

    MODAL_TEMPLATE_NAME = 'integrations/referencer/picker_modal.html'
    BODY_TEMPLATE_NAME = 'integrations/referencer/picker_body.html'

    def get_template_name(self) -> str:
        return self.MODAL_TEMPLATE_NAME

    # ---- GET: render the full modal ------------------------------

    def get(self, request, *args, **kwargs):
        integration_data_list = self._get_referencer_integration_data_list()
        if not integration_data_list:
            raise Http404( request )

        item_type = self._parse_item_type( request.GET.get( WireField.ITEM_TYPE ) )
        item_id = self._parse_item_id( request.GET.get( WireField.ITEM_ID ) )
        owner = self._resolve_owner( item_type=item_type, item_id=item_id )

        # Default to the first configured referencer. The user can
        # switch via the picker's integration <select> when more than
        # one referencer is configured.
        integration_data = integration_data_list[0]
        context = self._build_context(
            integration_data_list=integration_data_list,
            integration_data=integration_data,
            item_type=item_type,
            owner=owner,
            query='',
            limit=self.DEFAULT_LIMIT,
            selections=[],
            results=[],
        )
        return self.modal_response( request, context=context )

    # ---- POST: search re-render OR attach ------------------------

    def post(self, request, *args, **kwargs):
        integration_data_list = self._get_referencer_integration_data_list()
        if not integration_data_list:
            raise Http404( request )
        integration_data = self._resolve_integration_data(
            integration_data_list=integration_data_list,
            integration_id=request.POST.get( WireField.INTEGRATION_ID ),
        )
        referencer = self._require_referencer( integration_data, request )
        item_type = self._parse_item_type( request.POST.get( WireField.ITEM_TYPE ) )
        item_id = self._parse_item_id( request.POST.get( WireField.ITEM_ID ) )
        owner = self._resolve_owner( item_type=item_type, item_id=item_id )

        query = ( request.POST.get( WireField.QUERY ) or '' ).strip()
        limit = self._parse_limit( request.POST.get( WireField.LIMIT ) )

        # Run the integration search once per POST. The results
        # drive both the re-render and the title lookup for any
        # newly-checked result URLs that aren't in the existing
        # selections_json.
        results = self._search( referencer=referencer, query=query, limit=limit )

        selections = self._compute_selections( request=request, results=results )

        if request.POST.get( WireField.ACTION ) == WireField.ACTION_ATTACH:
            self._create_attributes(
                item_type=item_type, owner=owner, selections=selections,
            )
            return antinode.refresh_response()

        context = self._build_context(
            integration_data_list=integration_data_list,
            integration_data=integration_data,
            item_type=item_type,
            owner=owner,
            query=query,
            limit=limit,
            selections=selections,
            results=results,
        )
        body_html = render_to_string(
            self.BODY_TEMPLATE_NAME, context, request=request,
        )
        return antinode.response( main_content=body_html )

    # ---- helpers -------------------------------------------------

    @staticmethod
    def _get_referencer_integration_data_list() -> List[ IntegrationData ]:
        """All currently-enabled integrations that advertise the
        ATTRIBUTE_REFERENCE capability. Returned in label order
        (the manager already sorts by label)."""
        return IntegrationManager().get_integration_data_list(
            enabled_only=True,
            capabilities=frozenset({ IntegrationCapability.ATTRIBUTE_REFERENCE }),
        )

    @staticmethod
    def _resolve_integration_data(
            integration_data_list: List[ IntegrationData ],
            integration_id: str,
    ) -> IntegrationData:
        """Map the form's posted integration_id to one of the
        currently-enabled referencer integrations. Rejects unknown
        or now-disabled ids so a stale modal can't drive a search
        against an integration the operator has turned off."""
        if not integration_id:
            raise BadRequest( f'Missing {WireField.INTEGRATION_ID}.' )
        for candidate in integration_data_list:
            if candidate.integration_id == integration_id:
                return candidate
        raise BadRequest( f'Unknown {WireField.INTEGRATION_ID}: {integration_id!r}' )

    def _require_referencer(
            self, integration_data, request,
    ) -> IntegrationAttributeReferencer:
        referencer = integration_data.integration_gateway.get_attribute_referencer()
        if referencer is None:
            raise Http404( request )
        return referencer

    def _parse_item_type(self, raw_value: str) -> ItemType:
        try:
            item_type = ItemType.from_name( raw_value )
        except ValueError:
            raise BadRequest( f'Unsupported {WireField.ITEM_TYPE}: {raw_value!r}' )
        if item_type not in self.ATTRIBUTE_OWNER_MODELS:
            raise BadRequest( f'Unsupported {WireField.ITEM_TYPE}: {raw_value!r}' )
        return item_type

    def _parse_item_id(self, raw_value) -> int:
        try:
            return int( raw_value )
        except (TypeError, ValueError):
            raise BadRequest( f'Invalid {WireField.ITEM_ID}.' )

    def _parse_limit(self, raw_limit) -> int:
        try:
            limit = int( raw_limit )
        except (TypeError, ValueError):
            return self.DEFAULT_LIMIT
        if limit not in self.PAGE_SIZE_CHOICES:
            return self.DEFAULT_LIMIT
        return min( limit, self.MAX_LIMIT )

    def _resolve_owner(self, item_type: ItemType, item_id: int):
        owner_model, _attribute_model, _owner_field = self.ATTRIBUTE_OWNER_MODELS[ item_type ]
        try:
            return owner_model.objects.get( id=item_id )
        except owner_model.DoesNotExist:
            raise Http404( f'{item_type.label} not found.' )

    def _search(
            self,
            referencer: IntegrationAttributeReferencer,
            query: str,
            limit: int,
    ) -> List[ AttributeReferenceResult ]:
        if not query:
            return []
        try:
            return referencer.search_references( query=query, limit=limit )
        except Exception:
            logger.exception( 'Attribute-reference search failed.' )
            return []

    def _compute_selections(
            self,
            request,
            results: List[ AttributeReferenceResult ],
    ) -> List[ Dict[str, str] ]:
        # Existing selections from prior renders.
        selections = self._parse_existing_selections( request )

        # An explicit chip-× click removes one URL.
        remove_url = ( request.POST.get( WireField.REMOVE_URL ) or '' ).strip()
        if remove_url:
            selections = [
                s for s in selections
                if s[ WireField.SELECTION_URL ] != remove_url
            ]

        # The visible set is the URLs of result cards rendered in the
        # last view. The checked subset is what the user has currently
        # ticked. Anything visible-and-unchecked should be removed
        # from selections (distinguishes "unchecked a visible card"
        # from "card is no longer visible after a new search").
        visible = set( request.POST.getlist( WireField.VISIBLE_URL ) )
        checked = set( request.POST.getlist( WireField.RESULT_URL ) )
        unchecked_visible = visible - checked
        if unchecked_visible:
            selections = [
                s for s in selections
                if s[ WireField.SELECTION_URL ] not in unchecked_visible
            ]

        # Add any newly-checked URLs that weren't already selected.
        # Titles come from the just-run search results — the URL must
        # be in the current result set to be addable, which is fine
        # because checkboxes are only rendered next to current results.
        existing_urls = { s[ WireField.SELECTION_URL ] for s in selections }
        title_by_url = { r.source_url: r.title for r in results }
        for url in checked:
            if url in existing_urls:
                continue
            title = title_by_url.get( url )
            if not title:
                continue
            selections.append( {
                WireField.SELECTION_TITLE: title,
                WireField.SELECTION_URL: url,
            } )
            existing_urls.add( url )

        return selections

    @staticmethod
    def _parse_existing_selections(request) -> List[ Dict[str, str] ]:
        raw = request.POST.get( WireField.SELECTIONS_JSON ) or ''
        if not raw:
            return []
        try:
            decoded = json.loads( raw )
        except json.JSONDecodeError:
            return []
        if not isinstance( decoded, list ):
            return []
        parsed: List[ Dict[str, str] ] = []
        for item in decoded:
            if not isinstance( item, dict ):
                continue
            title = ( item.get( WireField.SELECTION_TITLE ) or '' ).strip()
            url = ( item.get( WireField.SELECTION_URL ) or '' ).strip()
            if not title or not url:
                continue
            parsed.append( {
                WireField.SELECTION_TITLE: title,
                WireField.SELECTION_URL: url,
            } )
        return parsed

    def _create_attributes(
            self,
            item_type: ItemType,
            owner,
            selections: List[ Dict[str, str] ],
    ) -> List[ int ]:
        if not selections:
            return []
        _owner_model, attribute_model, owner_field = self.ATTRIBUTE_OWNER_MODELS[ item_type ]
        created_ids: List[ int ] = []
        with transaction.atomic():
            for selection in selections:
                attr = attribute_model.objects.create( **{
                    owner_field: owner,
                    'name': selection[ WireField.SELECTION_TITLE ][:64],
                    'value': selection[ WireField.SELECTION_URL ],
                    'value_type_str': str( AttributeValueType.TEXT ),
                    'attribute_type_str': str( AttributeType.CUSTOM ),
                    'is_editable': True,
                    'is_required': False,
                } )
                created_ids.append( attr.id )
        return created_ids

    def _build_context(
            self,
            integration_data_list: List[ IntegrationData ],
            integration_data: IntegrationData,
            item_type: ItemType,
            owner,
            query: str,
            limit: int,
            selections: List[ Dict[str, str] ],
            results: List[ AttributeReferenceResult ],
    ) -> Dict:
        selected_urls = { s[ WireField.SELECTION_URL ] for s in selections }
        # The picker body's DOM id is unique-per-render so a re-render
        # produces a fresh target id matching the new form's
        # data-async attribute.
        body_html_id = f'hi-referencer-picker-body-{uuid.uuid4().hex[:8]}'
        return {
            'integration_data_list': integration_data_list,
            'integration_data': integration_data,
            'item_type_value': str( item_type ),
            'item_id': owner.id,
            'query': query,
            'limit': limit,
            'page_size_choices': self.PAGE_SIZE_CHOICES,
            'selections': selections,
            'selections_json': json.dumps( selections ),
            'selected_urls': selected_urls,
            'results': results,
            'body_html_id': body_html_id,
            'WireField': WireField,
        }
