"""
Server-side endpoints powering the ATTRIBUTE_REFERENCE picker.

Two endpoints, both keyed by integration_id in the URL:

  - ``AttributeReferenceSearchView`` (POST) — given a query string,
    dispatches to the integration's ``IntegrationAttributeReferencer``
    and returns the result rows as JSON for the picker UI to render.
  - ``AttributeReferenceAttachView`` (POST) — given a list of selected
    rows and an attribute-owning item (Entity or Location), creates
    one TEXT attribute per selection.

Both views are POST-only and require the standard edit decorator
(the picker is an editing affordance). Item-routing lives in the
POST body rather than the URL so the URL set stays small.
"""

import json
import logging
from dataclasses import asdict
from typing import List

from django.core.exceptions import BadRequest
from django.db import transaction
from django.http import Http404, JsonResponse
from django.utils.decorators import method_decorator
from django.views.generic import View

from hi.apps.attribute.enums import AttributeType, AttributeValueType
from hi.apps.entity.models import Entity, EntityAttribute
from hi.apps.location.models import Location, LocationAttribute
from hi.decorators import edit_required
from hi.enums import ItemType

from hi.integrations.view_mixins import IntegrationViewMixin

from .transient_models import AttributeReferenceResult, WireField


logger = logging.getLogger(__name__)


@method_decorator( edit_required, name='dispatch' )
class AttributeReferenceSearchView( View, IntegrationViewMixin ):
    """POST a query + limit for an integration; return matching
    result rows for the picker. JSON-only response — the picker
    UI renders client-side."""

    # Per-call upper bound on results returned to the picker. The
    # picker's page-size dropdown (20/50/100) sends one of these
    # in the POST; the max is a server-side ceiling so a hostile
    # or buggy client can't request a huge page.
    MAX_LIMIT = 100
    DEFAULT_LIMIT = 20

    def post( self, request, *args, **kwargs ):
        integration_data = self.get_integration_data( request, *args, **kwargs )
        referencer = integration_data.integration_gateway.get_attribute_referencer()
        if referencer is None:
            raise Http404( request )

        query = ( request.POST.get( WireField.QUERY ) or '' ).strip()
        limit = self._parse_limit( request.POST.get( WireField.LIMIT ) )

        if not query:
            return JsonResponse( { WireField.RESULTS: [] } )

        try:
            results: List[ AttributeReferenceResult ] = referencer.search_references(
                query=query, limit=limit,
            )
        except Exception as e:
            logger.exception(
                f'Attribute-reference search failed for integration '
                f'{integration_data.integration_id!r}.'
            )
            return JsonResponse( { WireField.ERROR: str( e ) }, status=502 )

        return JsonResponse( {
            WireField.RESULTS: [ asdict( row ) for row in results ],
        } )

    def _parse_limit( self, raw_limit ) -> int:
        try:
            limit = int( raw_limit )
        except (TypeError, ValueError):
            return self.DEFAULT_LIMIT
        if limit < 1:
            return self.DEFAULT_LIMIT
        return min( limit, self.MAX_LIMIT )


@method_decorator( edit_required, name='dispatch' )
class AttributeReferenceAttachView( View, IntegrationViewMixin ):
    """POST an attribute-owning item (Entity or Location) and a
    list of selections; create one TEXT attribute per selection.

    Body shape:
      - ``item_type``: ``str(ItemType.ENTITY)`` or ``str(ItemType.LOCATION)``
      - ``item_id``: int
      - ``selections``: JSON-encoded list of
        ``[ { "title": str, "source_url": str }, ... ]``
    """

    # Item-type → (owner model, attribute model, owner field name).
    # Restricts the attach view to the two attribute-owning models
    # (per #232 design: EntityAttribute + LocationAttribute only)
    # and keeps the type-resolution table in one place.
    ATTRIBUTE_OWNER_MODELS = {
        ItemType.ENTITY: (Entity, EntityAttribute, 'entity'),
        ItemType.LOCATION: (Location, LocationAttribute, 'location'),
    }

    def post( self, request, *args, **kwargs ):
        integration_data = self.get_integration_data( request, *args, **kwargs )
        # Refuse to create attributes referencing a capability the
        # integration doesn't advertise — guards against a stale
        # picker or a hostile client targeting a disabled integration.
        referencer = integration_data.integration_gateway.get_attribute_referencer()
        if referencer is None:
            raise Http404( request )

        item_type = self._parse_item_type( request.POST.get( WireField.ITEM_TYPE ) )
        item_id = self._parse_item_id( request )
        owner = self._resolve_owner( item_type=item_type, item_id=item_id )
        selections = self._parse_selections( request )

        if not selections:
            return JsonResponse( {
                WireField.CREATED_COUNT: 0,
                WireField.CREATED_IDS: [],
            } )

        created_ids = self._create_attributes(
            item_type=item_type, owner=owner, selections=selections,
        )
        return JsonResponse( {
            WireField.CREATED_COUNT: len( created_ids ),
            WireField.CREATED_IDS: created_ids,
        } )

    def _parse_item_type( self, raw_value: str ) -> ItemType:
        """Reject anything outside the supported attribute-owning
        set. The wire form is ``str(ItemType.X)`` — the enum name
        lower-cased (per LabeledEnum.__str__)."""
        try:
            item_type = ItemType.from_name( raw_value )
        except ValueError:
            raise BadRequest( f'Unsupported {WireField.ITEM_TYPE}: {raw_value!r}' )
        if item_type not in self.ATTRIBUTE_OWNER_MODELS:
            raise BadRequest( f'Unsupported {WireField.ITEM_TYPE}: {raw_value!r}' )
        return item_type

    def _parse_item_id( self, request ) -> int:
        raw = request.POST.get( WireField.ITEM_ID )
        try:
            return int( raw )
        except (TypeError, ValueError):
            raise BadRequest( f'Invalid {WireField.ITEM_ID}.' )

    def _resolve_owner( self, item_type: ItemType, item_id: int ):
        owner_model, _attribute_model, _owner_field = self.ATTRIBUTE_OWNER_MODELS[ item_type ]
        try:
            return owner_model.objects.get( id=item_id )
        except owner_model.DoesNotExist:
            raise Http404( f'{item_type.label} not found.' )

    def _parse_selections( self, request ) -> List[ dict ]:
        raw = request.POST.get( WireField.SELECTIONS )
        if not raw:
            return []
        try:
            decoded = json.loads( raw )
        except json.JSONDecodeError:
            raise BadRequest( f'{WireField.SELECTIONS} must be a JSON-encoded list.' )
        if not isinstance( decoded, list ):
            raise BadRequest( f'{WireField.SELECTIONS} must be a list.' )
        validated: List[ dict ] = []
        for index, item in enumerate( decoded ):
            if not isinstance( item, dict ):
                raise BadRequest(
                    f'{WireField.SELECTIONS}[{index}] must be an object.'
                )
            title = ( item.get( WireField.SELECTION_TITLE ) or '' ).strip()
            source_url = ( item.get( WireField.SELECTION_URL ) or '' ).strip()
            if not title or not source_url:
                raise BadRequest(
                    f'{WireField.SELECTIONS}[{index}] requires non-empty '
                    f'{WireField.SELECTION_TITLE} + {WireField.SELECTION_URL}.'
                )
            validated.append( {
                WireField.SELECTION_TITLE: title,
                WireField.SELECTION_URL: source_url,
            } )
        return validated

    def _create_attributes(
            self,
            item_type: ItemType,
            owner,
            selections: List[ dict ],
    ) -> List[ int ]:
        _owner_model, attribute_model, owner_field = self.ATTRIBUTE_OWNER_MODELS[ item_type ]
        created_ids: List[ int ] = []
        with transaction.atomic():
            for selection in selections:
                attr = attribute_model.objects.create( **{
                    owner_field: owner,
                    'name': selection[ WireField.SELECTION_TITLE ][:64],  # model max_length
                    'value': selection[ WireField.SELECTION_URL ],
                    'value_type_str': str( AttributeValueType.TEXT ),
                    'attribute_type_str': str( AttributeType.CUSTOM ),
                    'is_editable': True,
                    'is_required': False,
                } )
                created_ids.append( attr.id )
        return created_ids
