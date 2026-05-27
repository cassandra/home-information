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
from typing import Dict, List

from django.core.exceptions import BadRequest
from django.db import transaction
from django.http import Http404, HttpResponse
from django.template.loader import render_to_string
from django.urls import reverse
from django.views.generic import View

from hi.apps.attribute.edit_form_handler import AttributeEditFormHandler
from hi.apps.attribute.edit_response_renderer import AttributeEditResponseRenderer
from hi.apps.attribute.enums import AttributeType, AttributeValueType
from hi.apps.attribute.view_mixins import AttributeEditViewMixin
from hi.apps.common import antinode
from hi.apps.config.enums import ConfigPageType
from hi.apps.config.views import ConfigPageView
from hi.apps.entity.models import Entity, EntityAttribute
from hi.apps.location.models import Location, LocationAttribute
from hi.constants import DIVID
from hi.enums import ItemType
from hi.exceptions import ForceRedirectException
from hi.hi_async_view import HiModalView

from hi.integrations.enums import IntegrationCapability
from hi.integrations.integration_attribute_edit_context import (
    IntegrationAttributeItemEditContext,
)
from hi.integrations.integration_data import IntegrationData
from hi.integrations.integration_manager import IntegrationManager
from hi.integrations.view_mixins import IntegrationViewMixin

from .integration_referencer import IntegrationAttributeReferencer
from .transient_models import AttributeReferenceResult


logger = logging.getLogger(__name__)


_PAGE_SIZE_CHOICES = (20, 50, 100)
_DEFAULT_LIMIT = 20
_MAX_LIMIT = 100

# ItemType → (owner model, attribute model, owner FK field name).
_ATTRIBUTE_OWNER_MODELS = {
    ItemType.ENTITY: (Entity, EntityAttribute, 'entity'),
    ItemType.LOCATION: (Location, LocationAttribute, 'location'),
}


def _get_referencer_integration_data_list() -> List[ IntegrationData ]:
    """All currently-enabled integrations that advertise the
    ATTRIBUTE_REFERENCE capability. Returned in label order
    (the manager already sorts by label)."""
    return IntegrationManager().get_integration_data_list(
        enabled_only=True,
        capabilities=frozenset({ IntegrationCapability.ATTRIBUTE_REFERENCE }),
    )


def _resolve_integration_data(
        integration_data_list: List[ IntegrationData ],
        integration_id: str,
) -> IntegrationData:
    """Map the form's posted integration_id to one of the
    currently-enabled referencer integrations. Rejects unknown
    or now-disabled ids so a stale modal can't drive a search
    against an integration the operator has turned off."""
    if not integration_id:
        raise BadRequest(
            f'Missing {DIVID["ATTR_PICKER_INTEGRATION_ID_FIELD"]}.',
        )
    for candidate in integration_data_list:
        if candidate.integration_id == integration_id:
            return candidate
    raise BadRequest(
        f'Unknown {DIVID["ATTR_PICKER_INTEGRATION_ID_FIELD"]}: '
        f'{integration_id!r}',
    )


def _require_referencer(
        integration_data: IntegrationData,
        request,
) -> IntegrationAttributeReferencer:
    referencer = integration_data.integration_gateway.get_attribute_referencer()
    if referencer is None:
        raise Http404( request )
    return referencer


def _parse_item_type(raw_value: str) -> ItemType:
    try:
        item_type = ItemType.from_name( raw_value )
    except ValueError:
        raise BadRequest(
            f'Unsupported {DIVID["ATTR_PICKER_ITEM_TYPE_FIELD"]}: {raw_value!r}',
        )
    if item_type not in _ATTRIBUTE_OWNER_MODELS:
        raise BadRequest(
            f'Unsupported {DIVID["ATTR_PICKER_ITEM_TYPE_FIELD"]}: {raw_value!r}',
        )
    return item_type


def _parse_item_id(raw_value) -> int:
    try:
        return int( raw_value )
    except (TypeError, ValueError):
        raise BadRequest(
            f'Invalid {DIVID["ATTR_PICKER_ITEM_ID_FIELD"]}.',
        )


def _parse_limit(raw_limit) -> int:
    try:
        limit = int( raw_limit )
    except (TypeError, ValueError):
        return _DEFAULT_LIMIT
    if limit not in _PAGE_SIZE_CHOICES:
        return _DEFAULT_LIMIT
    return min( limit, _MAX_LIMIT )


def _resolve_owner(item_type: ItemType, item_id: int):
    owner_model, _attribute_model, _owner_field = _ATTRIBUTE_OWNER_MODELS[ item_type ]
    try:
        return owner_model.objects.get( id=item_id )
    except owner_model.DoesNotExist:
        raise Http404( f'{item_type.label} not found.' )


def _search_upstream(
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


def _parse_selections_json(raw: str) -> List[ Dict[str, str] ]:
    """Parse the JS-built ``selections_json`` payload submitted on
    attach. Skips records with missing title or source_url and
    falls back to an empty list on any decode error."""
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
        title = ( item.get( DIVID['ATTR_PICKER_SELECTION_TITLE_KEY'] ) or '' ).strip()
        url = ( item.get( DIVID['ATTR_PICKER_SELECTION_URL_KEY'] ) or '' ).strip()
        if not title or not url:
            continue
        parsed.append( {
            DIVID['ATTR_PICKER_SELECTION_TITLE_KEY']: title,
            DIVID['ATTR_PICKER_SELECTION_URL_KEY']: url,
        } )
    return parsed


def _create_attributes(
        item_type: ItemType,
        owner,
        selections: List[ Dict[str, str] ],
) -> List[ int ]:
    if not selections:
        return []
    _owner_model, attribute_model, owner_field = _ATTRIBUTE_OWNER_MODELS[ item_type ]
    created_ids: List[ int ] = []
    with transaction.atomic():
        for selection in selections:
            attr = attribute_model.objects.create( **{
                owner_field: owner,
                'name': selection[ DIVID['ATTR_PICKER_SELECTION_TITLE_KEY'] ][:64],
                'value': selection[ DIVID['ATTR_PICKER_SELECTION_URL_KEY'] ],
                'value_type_str': str( AttributeValueType.TEXT ),
                'attribute_type_str': str( AttributeType.CUSTOM ),
                'is_editable': True,
                'is_required': False,
            } )
            created_ids.append( attr.id )
    return created_ids


class AttributeReferencePickerView( HiModalView ):
    """GET the picker modal. Initial render is empty — no results,
    no selections. Selection state lives in JS (see
    ``static/js/attr-picker.js``); subsequent search results arrive
    via async POST to ``integrations_attribute_reference_search``,
    and the final commit posts to
    ``integrations_attribute_reference_attach``."""

    MODAL_TEMPLATE_NAME = 'integrations/referencer/modals/attr_picker.html'

    def get_template_name(self) -> str:
        return self.MODAL_TEMPLATE_NAME

    def get(self, request, *args, **kwargs):
        integration_data_list = _get_referencer_integration_data_list()
        if not integration_data_list:
            raise Http404( request )

        item_type = _parse_item_type(
            request.GET.get( DIVID['ATTR_PICKER_ITEM_TYPE_FIELD'] ),
        )
        item_id = _parse_item_id(
            request.GET.get( DIVID['ATTR_PICKER_ITEM_ID_FIELD'] ),
        )
        owner = _resolve_owner( item_type=item_type, item_id=item_id )

        # Default to the first configured referencer. The operator
        # can switch via the picker's integration <select> when more
        # than one referencer is configured.
        integration_data = integration_data_list[0]

        # Seed the picker with a query based on the owner's name so
        # the operator opens to relevant results without retyping
        # what they're already configuring. Goes through the same
        # ``_search_upstream`` the search endpoint uses; the body
        # template's results container renders the same
        # ``attr_picker_results.html`` partial the search response
        # returns.
        query = owner.name
        referencer = integration_data.integration_gateway.get_attribute_referencer()
        results = _search_upstream(
            referencer=referencer,
            query=query,
            limit=_DEFAULT_LIMIT,
        ) if referencer is not None else []
        
        context = {
            'integration_data_list': integration_data_list,
            'integration_data': integration_data,
            'item_type_value': str( item_type ),
            'item_id': owner.id,
            'limit': _DEFAULT_LIMIT,
            'page_size_choices': _PAGE_SIZE_CHOICES,
            'query': query,
            'results': results,
        }
        return self.modal_response( request, context=context )


class AttributeReferenceSearchView( View ):
    """POST endpoint that runs an upstream search and returns only
    the result-cards HTML partial. The attr-picker JS swaps the
    returned markup into the picker's results container, then
    re-applies checkbox state from its in-memory selection set.

    Empty / whitespace queries short-circuit to an empty result
    partial (no upstream call)."""

    RESULTS_TEMPLATE_NAME = 'integrations/referencer/panes/attr_picker_results.html'

    def post(self, request, *args, **kwargs):
        integration_data_list = _get_referencer_integration_data_list()
        if not integration_data_list:
            raise Http404( request )
        integration_data = _resolve_integration_data(
            integration_data_list=integration_data_list,
            integration_id=request.POST.get(
                DIVID['ATTR_PICKER_INTEGRATION_ID_FIELD'],
            ),
        )
        referencer = _require_referencer( integration_data, request )
        query = (
            request.POST.get( DIVID['ATTR_PICKER_QUERY_FIELD'] ) or ''
        ).strip()
        limit = _parse_limit(
            request.POST.get( DIVID['ATTR_PICKER_LIMIT_FIELD'] ),
        )
        results = _search_upstream(
            referencer=referencer, query=query, limit=limit,
        )
        html = render_to_string(
            self.RESULTS_TEMPLATE_NAME,
            {
                'query': query,
                'results': results,
            },
            request=request,
        )
        return HttpResponse( html )


class AttributeReferenceAttachView( View ):
    """POST endpoint that creates TEXT attributes for the operator's
    selected references. The JS module serializes its in-memory
    selection set into ``selections_json`` just before the form
    submits.

    Returns ``antinode.refresh_response()`` so the parent page
    reloads and the modal closes naturally."""

    def post(self, request, *args, **kwargs):
        item_type = _parse_item_type(
            request.POST.get( DIVID['ATTR_PICKER_ITEM_TYPE_FIELD'] ),
        )
        item_id = _parse_item_id(
            request.POST.get( DIVID['ATTR_PICKER_ITEM_ID_FIELD'] ),
        )
        owner = _resolve_owner( item_type=item_type, item_id=item_id )
        selections = _parse_selections_json(
            request.POST.get( DIVID['ATTR_PICKER_SELECTIONS_JSON_FIELD'] ) or '',
        )
        _create_attributes(
            item_type=item_type, owner=owner, selections=selections,
        )
        return antinode.refresh_response()


# ----------------------------------------------------------------------
# Reference-capability management page
# ----------------------------------------------------------------------
#
# Parallel to the Connectors page (CONNECT capability) and the Data
# Import page (IMPORT capability). The operator-facing tab label is
# "Content Sources"; code-side naming uses ``reference`` to align
# with the capability and the surrounding referencer/ directory.


class ReferenceHomeView( ConfigPageView, IntegrationViewMixin ):
    """Landing route for the reference-management page. Picks the
    first ATTRIBUTE_REFERENCE integration (enabled or not) and
    redirects to its manage URL. Returns the empty-state template
    when none are discovered (defensive — currently can't happen
    at runtime as long as the paperless app is installed)."""

    def config_page_type(self) -> ConfigPageType:
        return ConfigPageType.INTEGRATIONS_REFERENCE

    def get_main_template_name( self ) -> str:
        return 'integrations/referencer/pages/no_integrations.html'

    def get_main_template_context( self, request, *args, **kwargs ):
        integration_data_list = IntegrationManager().get_integration_data_list(
            capabilities = frozenset({ IntegrationCapability.ATTRIBUTE_REFERENCE }),
        )
        if not integration_data_list:
            return dict()
        redirect_url = reverse(
            'integrations_reference_manage',
            kwargs = { 'integration_id': integration_data_list[0].integration_id },
        )
        raise ForceRedirectException( redirect_url )


class ReferenceManageView( ConfigPageView, IntegrationViewMixin, AttributeEditViewMixin ):
    """Per-integration attribute-form page for ATTRIBUTE_REFERENCE
    integrations.

    Differences from ``ConnectorManageView``:
      - Filters by ATTRIBUTE_REFERENCE (not CONNECT).
      - Does not read health status / sync-check state /
        has_entities; ATTRIBUTE_REFERENCE has no monitors and no
        sync cycle.
      - Passes ``capability = ATTRIBUTE_REFERENCE`` to the attribute
        edit context so the attribute queryset is filtered to the
        attributes the capability declares.
      - Tolerates ``is_enabled = False`` integrations — the operator
        configures credentials here before the integration is
        enabled.
    """

    def config_page_type(self) -> ConfigPageType:
        return ConfigPageType.INTEGRATIONS_REFERENCE

    def get_main_template_name( self ) -> str:
        return 'integrations/referencer/pages/integration_manage.html'

    def get_main_template_context( self, request, *args, **kwargs ):
        integration_data, integration_data_list = self._resolve(
            kwargs.get( 'integration_id' )
        )
        attr_item_context = self._build_attr_item_context( integration_data )

        template_context = self.create_initial_template_context(
            attr_item_context = attr_item_context,
        )
        template_context.update({
            'core': {
                'integration_data_list': integration_data_list,
                'integration_data': integration_data,
            },
        })
        return template_context

    ACTION_DISABLE = 'disable'

    def post( self, request, *args, **kwargs ):
        integration_data, _ = self._resolve( kwargs.get( 'integration_id' ) )
        if request.POST.get( 'action' ) == self.ACTION_DISABLE:
            return self._handle_disable( request, integration_data )
        return self._handle_save( request, integration_data )

    def _handle_disable( self, request, integration_data ):
        """Flip ``is_enabled`` to False; credentials remain in the DB
        so a future ENABLE is one click. Re-renders the form area in
        place so the badge and the submit-button label update via
        antinode partial swap without a full page reload."""
        if integration_data.integration.is_enabled:
            integration_data.integration.is_enabled = False
            integration_data.integration.save(
                update_fields = [ 'is_enabled' ],
            )
        attr_item_context = self._build_attr_item_context( integration_data )
        renderer = AttributeEditResponseRenderer()
        return renderer.render_form_success_response(
            attr_item_context = attr_item_context,
            request = request,
            message = None,
        )

    def _handle_save( self, request, integration_data ):
        # Capture pre-save enabled state so we can flip it on a
        # successful first-time save (the ``ENABLE`` flow).
        was_enabled = integration_data.integration.is_enabled
        attr_item_context = self._build_attr_item_context( integration_data )

        form_handler = AttributeEditFormHandler()
        renderer = AttributeEditResponseRenderer()
        edit_form_data = form_handler.create_edit_form_data(
            attr_item_context = attr_item_context,
            form_data = request.POST,
        )

        forms_valid = form_handler.validate_forms( edit_form_data = edit_form_data )
        if forms_valid:
            # Schema + access check via the shared helper; populates
            # ``_non_form_errors`` on failure so the next is_valid()
            # call returns False.
            self.validate_attributes_extra(
                attr_item_context = attr_item_context,
                regular_attributes_formset = edit_form_data.regular_attributes_formset,
                request = request,
            )
            forms_valid = edit_form_data.regular_attributes_formset.is_valid()

        if not forms_valid:
            return renderer.render_form_error_response(
                attr_item_context = attr_item_context,
                edit_form_data = edit_form_data,
                request = request,
            )

        form_handler.save_forms(
            attr_item_context = attr_item_context,
            edit_form_data = edit_form_data,
            request = request,
        )
        if not was_enabled:
            # First-time ENABLE: credentials just validated upstream
            # via the helper's access probe, so flipping is_enabled
            # to True reflects what's now true on the wire.
            integration_data.integration.is_enabled = True
            integration_data.integration.save(
                update_fields = [ 'is_enabled' ],
            )
            # Rebuild the edit context so the response renders the
            # post-flip state: ``update_button_label`` flips from
            # ENABLE to UPDATE and the action-bar fragment reads
            # ``is_enabled = True``.
            attr_item_context = self._build_attr_item_context( integration_data )

        return renderer.render_form_success_response(
            attr_item_context = attr_item_context,
            request = request,
            message = None,
        )

    def validate_attributes_extra( self, attr_item_context,
                                   regular_attributes_formset, request ):
        # The shared helper runs both gateway.validate_configuration
        # (schema) and gateway.validate_access (live probe) and
        # decorates the formset with the failure message on either
        # failure. We deliberately want the access probe on every
        # save so a credential typo on UPDATE-while-enabled is
        # rejected (atomic semantics — nothing changes on failure).
        self.validate_attributes_extra_helper(
            attr_item_context,
            regular_attributes_formset,
            error_title = 'Cannot save settings.',
        )
        return

    def _resolve( self, integration_id ):
        integration_data_list = IntegrationManager().get_integration_data_list(
            capabilities = frozenset({ IntegrationCapability.ATTRIBUTE_REFERENCE }),
        )
        if not integration_data_list:
            raise Http404( 'No reference integrations are installed.' )
        integration_data = self._find_integration_data(
            integration_data_list = integration_data_list,
            integration_id = integration_id,
        )
        if integration_data is None:
            raise Http404(
                f'Unknown reference integration: {integration_id!r}'
            )
        return integration_data, integration_data_list

    def _build_attr_item_context( self, integration_data ):
        # Button label flips with enabled state: ``ENABLE`` is the
        # first-time activation path; ``UPDATE`` is the
        # already-enabled re-validate-and-save path. Both share the
        # same form-submission endpoint and the same validation
        # gates — only the label and the post-save bookkeeping
        # differ.
        update_label = (
            'UPDATE' if integration_data.integration.is_enabled else 'ENABLE'
        )
        return IntegrationAttributeItemEditContext(
            integration_data = integration_data,
            capability_gateway = integration_data.integration_gateway.get_attribute_referencer(),
            health_status = None,
            update_button_label = update_label,
        )

    @staticmethod
    def _find_integration_data(
            integration_data_list: List[ IntegrationData ],
            integration_id: str,
    ) -> IntegrationData:
        for candidate in integration_data_list:
            if candidate.integration_id == integration_id:
                return candidate
        return None


