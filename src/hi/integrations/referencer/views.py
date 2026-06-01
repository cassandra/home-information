"""
EXTERNAL_REFERENCE picker -- one HiModal view backed by antinode
partial swaps.

Workflow:

  - GET ``/integrations/referencer/picker/`` with ``item_type`` +
    ``item_id`` query params renders the full picker modal. The
    view discovers all currently-enabled EXTERNAL_REFERENCE
    integrations and lets the operator choose between them via an
    in-modal selector when more than one is configured.

  - POST to ``/integrations/referencer/picker/search/`` re-renders
    the result-cards partial. The form carries ``integration_id``
    as a hidden field so the view knows which referencer to drive
    the search against. The picker JS swaps the partial into the
    modal's results container.

  - POST to ``/integrations/referencer/picker/attach/`` commits the
    operator's selection set. The picker resets selections on
    source-switch, so one submission carries items from one
    integration only; the form-level ``integration_id`` is the
    single source of truth for routing.
"""

import json
import logging
from typing import List

from django.http import Http404, HttpResponse
from django.template.loader import render_to_string
from django.urls import reverse
from django.views.generic import View

from hi.apps.attribute.edit_form_handler import AttributeEditFormHandler
from hi.apps.attribute.edit_response_renderer import AttributeEditResponseRenderer
from hi.apps.attribute.view_mixins import AttributeEditViewMixin
from hi.apps.common import antinode
from hi.apps.config.enums import ConfigPageType
from hi.apps.config.views import ConfigPageView
from hi.constants import DIVID
from hi.enums import ItemType, ViewDataPriority
from hi.exceptions import ForceRedirectException
from hi.hi_async_view import HiModalView

from hi.integrations.enums import IntegrationCapability
from hi.integrations.integration_attribute_edit_context import (
    IntegrationAttributeItemEditContext,
)
from hi.integrations.integration_data import IntegrationData
from hi.integrations.transient_models import IntegrationKey
from hi.integrations.view_mixins import IntegrationViewMixin

from .transient_models import (
    ExternalReferenceAttachBatchOutcome,
    ExternalReferenceAttachOutcome,
    ExternalReferenceResult,
    ExternalReferenceSearchResult,
)
from .view_mixins import ExternalReferenceViewMixin


logger = logging.getLogger(__name__)


_REFERENCER_CAPABILITIES = frozenset({ IntegrationCapability.EXTERNAL_REFERENCE })


class ExternalReferencePickerView(
        HiModalView, IntegrationViewMixin, ExternalReferenceViewMixin ):
    """GET the picker modal. Initial render seeds the result list
    by searching on the owner's name; selection state then lives in
    JS. Subsequent search results arrive via async POST to
    ``integrations_external_reference_search``, and the final
    commit posts to ``integrations_external_reference_attach``."""

    MODAL_TEMPLATE_NAME = 'integrations/referencer/modals/external_reference_picker.html'

    def get_template_name(self) -> str:
        return self.MODAL_TEMPLATE_NAME

    def get(self, request, *args, **kwargs):
        integration_data_list = self.get_integration_data_list(
            enabled_only = True,
            capabilities = _REFERENCER_CAPABILITIES,
        )
        if not integration_data_list:
            raise Http404( request )

        item_type, owner = self.resolve_owner_from_form(
            raw_item_type = request.GET.get( DIVID['REF_PICKER_ITEM_TYPE_FIELD'] ),
            raw_item_id   = request.GET.get( DIVID['REF_PICKER_ITEM_ID_FIELD'] ),
        )

        # Default to the operator's last successfully-used referencer
        # if it's still enabled; otherwise fall back to the first
        # configured one. The session-stored id is set by the attach
        # view on successful link, so the picker re-opens to the
        # source most likely to match what they're working on. The
        # operator can still switch via the picker's integration
        # <select> when more than one referencer is configured.
        integration_data = self._default_integration_data(
            integration_data_list = integration_data_list,
            request = request,
        )

        # Seed the picker with a query based on the owner's name so
        # the operator opens to relevant results without retyping
        # what they're already configuring.
        query = owner.name
        referencer = integration_data.integration_gateway.get_external_referencer()
        if referencer is not None:
            search_result = self.search_upstream(
                referencer = referencer,
                query = query,
                limit = self.DEFAULT_LIMIT,
            )
        else:
            search_result = ExternalReferenceSearchResult( results = [] )

        context = {
            'integration_data_list': integration_data_list,
            'integration_data': integration_data,
            'item_type': item_type,
            'item_id': owner.id,
            'limit': self.DEFAULT_LIMIT,
            'page_size_choices': self.PAGE_SIZE_CHOICES,
            'query': query,
            'results': search_result.results,
            'error_message': search_result.error_message,
        }
        return self.modal_response( request, context = context )

    @staticmethod
    def _default_integration_data( integration_data_list, request ):
        """Pick the initial source for the picker dropdown. Honors
        the session-stored last-successful integration when it's
        still in the enabled list; otherwise falls back to the first
        entry."""
        saved_id = request.view_parameters.ref_picker_integration_id
        if saved_id:
            for candidate in integration_data_list:
                if candidate.integration_id == saved_id:
                    return candidate
        return integration_data_list[0]


class ExternalReferenceSearchView(
        View, IntegrationViewMixin, ExternalReferenceViewMixin ):
    """POST endpoint that runs an upstream search and returns only
    the result-cards HTML partial. The external-reference-picker JS swaps the
    returned markup into the picker's results container, then
    re-applies checkbox state from its in-memory selection set.

    Empty / whitespace queries short-circuit to an empty result
    partial (no upstream call)."""

    RESULTS_TEMPLATE_NAME = 'integrations/referencer/panes/external_reference_picker_results.html'
    MAX_LIMIT = 100

    def post(self, request, *args, **kwargs):
        integration_data_list = self.get_integration_data_list(
            enabled_only = True,
            capabilities = _REFERENCER_CAPABILITIES,
        )
        if not integration_data_list:
            raise Http404( request )
        integration_data = self.resolve_integration_data(
            integration_data_list = integration_data_list,
            integration_id = request.POST.get(
                DIVID['REF_PICKER_INTEGRATION_ID_FIELD'],
            ),
        )
        referencer = integration_data.integration_gateway.get_external_referencer()
        if referencer is None:
            raise Http404( request )
        query = (
            request.POST.get( DIVID['REF_PICKER_QUERY_FIELD'] ) or ''
        ).strip()
        limit = self._parse_limit(
            request.POST.get( DIVID['REF_PICKER_LIMIT_FIELD'] ),
        )
        search_result = self.search_upstream(
            referencer = referencer, query = query, limit = limit,
        )
        html = render_to_string(
            self.RESULTS_TEMPLATE_NAME,
            {
                'query': query,
                'results': search_result.results,
                'error_message': search_result.error_message,
            },
            request = request,
        )
        return HttpResponse( html )

    def _parse_limit(self, raw_limit) -> int:
        try:
            limit = int( raw_limit )
        except (TypeError, ValueError):
            return self.DEFAULT_LIMIT
        if limit not in self.PAGE_SIZE_CHOICES:
            return self.DEFAULT_LIMIT
        return min( limit, self.MAX_LIMIT )


class ExternalReferenceAttachView(
        View, IntegrationViewMixin, ExternalReferenceViewMixin ):
    """POST endpoint that dispatches the operator's selected
    references to the source integration for attach. The picker
    resets selection state on source-switch, so one submission
    always carries items from one integration; the form-level
    ``integration_id`` hidden field is the single source of truth
    for routing.

    Response branches on whether any selection failed:
      * all-success -- delegate to the owner's edit view's GET so
                       the operator sees the edit modal with the
                       new cards already in the grid.
      * any-failure -- render the error modal with the per-failure
                       messages plus LINK MORE / DISMISS actions.
                       Modals swap one-at-a-time via the antinode
                       ``modal`` response key.
    """

    ERRORS_MODAL_TEMPLATE_NAME = (
        'integrations/modals/external_reference_attach_errors.html'
    )

    def post(self, request, *args, **kwargs):
        integration_data_list = self.get_integration_data_list(
            enabled_only = True,
            capabilities = _REFERENCER_CAPABILITIES,
        )
        if not integration_data_list:
            raise Http404( request )
        integration_data = self.resolve_integration_data(
            integration_data_list = integration_data_list,
            integration_id = request.POST.get(
                DIVID['REF_PICKER_INTEGRATION_ID_FIELD'],
            ),
        )
        item_type, owner = self.resolve_owner_from_form(
            raw_item_type = request.POST.get( DIVID['REF_PICKER_ITEM_TYPE_FIELD'] ),
            raw_item_id   = request.POST.get( DIVID['REF_PICKER_ITEM_ID_FIELD'] ),
        )
        selections = self._parse_selections_json(
            raw = request.POST.get(
                DIVID['REF_PICKER_SELECTIONS_JSON_FIELD'],
            ) or '',
            integration_id = integration_data.integration_id,
        )
        batch = self._dispatch_attach(
            owner = owner,
            integration_data = integration_data,
            selections = selections,
        )
        # Remember the chosen referencer on any successful link so
        # the next picker open defaults to the same source. Partial-
        # failure batches still count -- the operator picked this
        # integration and at least some items attached.
        if batch.success_count > 0:
            request.view_parameters.ref_picker_integration_id = (
                integration_data.integration_id
            )
            request.view_parameters.to_session( request )
        if batch.has_failures:
            return self._render_errors_modal(
                request, item_type, owner, batch,
            )
        return self._render_owner_edit_modal( request, item_type, owner )

    def _parse_selections_json(
            self,
            raw            : str,
            integration_id : str,
    ) -> List[ExternalReferenceResult]:
        """Parse the JS-built ``selections_json`` payload into
        ``ExternalReferenceResult`` instances. All selections in
        one submission share the same ``integration_id`` (taken
        from the form-level hidden field) because the picker
        resets its selection state on source-switch; the per-record
        JSON carries only the upstream identifier. Skips records
        with missing title / source_url / integration_name and
        falls back to an empty list on any decode error."""
        if not raw:
            return []
        try:
            decoded = json.loads( raw )
        except json.JSONDecodeError:
            return []
        if not isinstance( decoded, list ):
            return []
        parsed: List[ExternalReferenceResult] = []
        for item in decoded:
            if not isinstance( item, dict ):
                continue
            title = ( item.get(
                DIVID['REF_PICKER_SELECTION_TITLE_KEY']
            ) or '' ).strip()
            url = ( item.get(
                DIVID['REF_PICKER_SELECTION_URL_KEY']
            ) or '' ).strip()
            integration_name = ( item.get(
                DIVID['REF_PICKER_SELECTION_INTEGRATION_NAME_KEY']
            ) or '' ).strip()
            mime_type = ( item.get(
                DIVID['REF_PICKER_SELECTION_MIME_TYPE_KEY']
            ) or '' ).strip()
            if not title or not url or not integration_name:
                continue
            parsed.append( ExternalReferenceResult(
                integration_key = IntegrationKey(
                    integration_id = integration_id,
                    integration_name = integration_name,
                ),
                title = title,
                source_url = url,
                mime_type = mime_type or None,
            ) )
        return parsed

    def _dispatch_attach(
            self,
            owner,
            integration_data : IntegrationData,
            selections       : List[ExternalReferenceResult],
    ) -> ExternalReferenceAttachBatchOutcome:
        """Call the integration's ``attach_references`` for all
        selections in one submission. The picker resets selection
        state on source-switch (see ``external-reference-picker.js``), so one
        submission always carries items from a single integration
        -- no grouping needed.

        Returns the integration's
        ``ExternalReferenceAttachBatchOutcome`` directly, or a
        synthesized all-failure batch when the integration has no
        enabled referencer (every input selection still contributes
        exactly one outcome)."""
        if not selections:
            return ExternalReferenceAttachBatchOutcome()
        referencer = integration_data.integration_gateway.get_external_referencer()
        if referencer is None:
            logger.warning(
                f'External reference attach skipped {len(selections)} '
                f'selections: integration '
                f'{integration_data.integration_id!r} has no enabled '
                f'referencer.'
            )
            return ExternalReferenceAttachBatchOutcome(
                outcomes = [
                    ExternalReferenceAttachOutcome(
                        success = False,
                        error_message = (
                            f'Integration '
                            f'{integration_data.integration_id!r} '
                            f'is not available.'
                        ),
                    )
                    for _ in selections
                ],
            )
        return referencer.attach_references( owner, selections )

    @staticmethod
    def _render_owner_edit_modal(request, item_type : ItemType, owner):
        """Delegate to the owner's existing edit view so we don't
        duplicate its context-building logic. CBVs are designed to
        be called this way once you have the request in hand. The
        ``data_priority`` override lands the operator on Tab 3
        (Linked Content) so the just-attached references are
        immediately visible regardless of what the data-derived
        default would have picked."""
        from hi.apps.entity.views import EntityEditView
        from hi.apps.location.views import LocationEditView
        priority_kwarg = ViewDataPriority.REFERENCE.name
        if item_type.is_entity:
            return EntityEditView().get(
                request, entity_id = owner.id,
                data_priority = priority_kwarg,
            )
        return LocationEditView().get(
            request, location_id = owner.id,
            data_priority = priority_kwarg,
        )

    def _render_errors_modal(
            self, request, item_type : ItemType, owner, batch,
    ):
        picker_url = (
            reverse( 'integrations_external_reference_picker' )
            + f'?{DIVID["REF_PICKER_ITEM_TYPE_FIELD"]}={item_type}'
            + f'&{DIVID["REF_PICKER_ITEM_ID_FIELD"]}={owner.id}'
        )
        if item_type.is_entity:
            owner_edit_url = reverse(
                'entity_edit', kwargs = { 'entity_id': owner.id },
            )
        else:
            owner_edit_url = reverse(
                'location_edit_location_edit',
                kwargs = { 'location_id': owner.id },
            )
        modal_html = render_to_string(
            self.ERRORS_MODAL_TEMPLATE_NAME,
            {
                'batch'          : batch,
                'item_type'      : item_type,
                'item_id'        : owner.id,
                'picker_url'     : picker_url,
                'owner_edit_url' : owner_edit_url,
            },
            request = request,
        )
        return antinode.response( modal_content = modal_html )


# The operator-facing tab label is "Content Sources"; code-side
# naming uses ``reference`` to align with the capability and the
# surrounding referencer/ directory.


class ReferenceHomeView( ConfigPageView, IntegrationViewMixin ):
    """Landing route for the reference-management page. Picks the
    first EXTERNAL_REFERENCE integration (enabled or not) and
    redirects to its manage URL. Returns the empty-state template
    when none are discovered."""

    def config_page_type(self) -> ConfigPageType:
        return ConfigPageType.INTEGRATIONS_REFERENCE

    def get_main_template_name( self ) -> str:
        return 'integrations/referencer/pages/no_integrations.html'

    def get_main_template_context( self, request, *args, **kwargs ):
        integration_data_list = self.get_integration_data_list(
            capabilities = _REFERENCER_CAPABILITIES,
        )
        if not integration_data_list:
            return dict()
        redirect_url = reverse(
            'integrations_reference_manage',
            kwargs = { 'integration_id': integration_data_list[0].integration_id },
        )
        raise ForceRedirectException( redirect_url )


class ReferenceManageView( ConfigPageView, IntegrationViewMixin, AttributeEditViewMixin ):
    """Per-integration attribute-form page for EXTERNAL_REFERENCE
    integrations.

    EXTERNAL_REFERENCE has no monitors and no sync cycle, so the
    page does not surface health status, sync-check state, or
    has_entities. The attribute queryset is filtered to attributes
    the EXTERNAL_REFERENCE capability declares. ``is_enabled =
    False`` integrations are tolerated so the operator can configure
    credentials here before the integration is enabled.
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
        # We deliberately want the access probe on every save so a
        # credential typo on UPDATE-while-enabled is rejected
        # (atomic semantics -- nothing changes on failure).
        self.validate_attributes_extra_helper(
            attr_item_context,
            regular_attributes_formset,
            error_title = 'Cannot save settings.',
        )
        return

    def _resolve( self, integration_id ):
        integration_data_list = self.get_integration_data_list(
            capabilities = _REFERENCER_CAPABILITIES,
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
        # gates -- only the label and the post-save bookkeeping
        # differ.
        update_label = (
            'UPDATE' if integration_data.integration.is_enabled else 'ENABLE'
        )
        return IntegrationAttributeItemEditContext(
            integration_data = integration_data,
            capability_gateway = integration_data.integration_gateway.get_external_referencer(),
            health_status = None,
            update_button_label = update_label,
        )

    @staticmethod
    def _find_integration_data(
            integration_data_list: List[IntegrationData],
            integration_id: str,
    ) -> IntegrationData:
        for candidate in integration_data_list:
            if candidate.integration_id == integration_id:
                return candidate
        return None
