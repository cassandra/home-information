"""
Framework-level integration views shared across capabilities.
"""
import logging

from django.core.exceptions import BadRequest
from django.db import transaction
from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import View

from hi.apps.attribute.view_mixins import AttributeEditViewMixin
from hi.apps.entity.entity_placement import EntityPlacementService
from hi.apps.location.models import LocationView
from hi.constants import DIVID
from hi.enums import ViewMode, ViewType
from hi.hi_async_view import HiModalView
from hi.views import page_not_found_response

from hi.integrations.connector.sync_result import IntegrationSyncResult
from hi.integrations.enums import IntegrationCapability
from hi.integrations.integration_attribute_edit_context import (
    IntegrationAttributeItemEditContext,
)
from hi.integrations.integration_manager import IntegrationManager
from hi.integrations.models import IntegrationAttribute
from hi.integrations.placement_request import PlacementFormParser, PlacementUrlParams
from hi.integrations.view_mixins import (
    CapabilityBlockViewMixin,
    ExternalReferenceCardViewMixin,
    IntegrationPlacementViewMixin,
    IntegrationViewMixin,
)


logger = logging.getLogger(__name__)


class ExternalReferenceRenameView( View, ExternalReferenceCardViewMixin ):
    """POST endpoint: rename a single external-reference card. The
    title is operator-controlled and persists across upserts on
    re-attach."""

    def post( self, request, owner_type, reference_id, *args, **kwargs ):
        reference = self.get_external_reference_or_404(
            owner_type = owner_type, reference_id = reference_id,
        )
        new_title = ( request.POST.get(
            DIVID['EXT_REF_TITLE_FIELD']
        ) or '' ).strip()
        if not new_title:
            raise BadRequest( 'Title must be non-empty.' )
        reference.title = new_title[:255]
        reference.save( update_fields = [ 'title', 'updated_datetime' ] )
        return self.render_grid_replace(
            request, owner_type, getattr( reference, owner_type ),
        )


class ExternalReferenceDeleteView( View, ExternalReferenceCardViewMixin ):
    """POST endpoint: unlink (delete) a single external-reference
    card. Best-effort thumbnail-file cleanup is the model's
    responsibility."""

    def post( self, request, owner_type, reference_id, *args, **kwargs ):
        reference = self.get_external_reference_or_404(
            owner_type = owner_type, reference_id = reference_id,
        )
        # Capture the owner before delete; the row's FK accessor is
        # unreliable after delete().
        owner = getattr( reference, owner_type )
        reference.delete()
        return self.render_grid_replace( request, owner_type, owner )


class ExternalReferenceReorderView( View, ExternalReferenceCardViewMixin ):
    """POST endpoint: move a single external-reference card one slot
    left or right. Re-normalizes order_ids of the affected siblings
    so the new ordering survives subsequent reorders without
    accumulating gaps."""

    def post( self, request, owner_type, reference_id, *args, **kwargs ):
        direction = request.POST.get( DIVID['EXT_REF_DIRECTION_FIELD'] )
        if direction not in (
                DIVID['EXT_REF_DIRECTION_LEFT'],
                DIVID['EXT_REF_DIRECTION_RIGHT'],
        ):
            raise BadRequest( 'Invalid direction.' )

        reference = self.get_external_reference_or_404(
            owner_type = owner_type, reference_id = reference_id,
        )
        model = self.EXTERNAL_REFERENCE_MODELS[ owner_type ]
        owner = getattr( reference, owner_type )

        # The read + renumber + writes run inside one transaction
        # with row locks on the sibling set so concurrent reorders
        # serialize. Without this, two simultaneous POSTs each see
        # a stale ordering and the second writer clobbers the
        # first, occasionally leaving duplicate ``order_id`` values
        # the ordering meta can't disambiguate.
        with transaction.atomic():
            siblings = list(
                model.objects.select_for_update().filter(
                    **{ owner_type: owner },
                ).order_by( 'order_id', '-created_datetime' )
            )
            try:
                current_idx = next(
                    i for i, r in enumerate(siblings) if r.pk == reference.pk
                )
            except StopIteration:
                raise Http404

            if direction == DIVID['EXT_REF_DIRECTION_LEFT'] and current_idx > 0:
                siblings[current_idx], siblings[current_idx - 1] = (
                    siblings[current_idx - 1], siblings[current_idx],
                )
            elif (
                    direction == DIVID['EXT_REF_DIRECTION_RIGHT']
                    and current_idx < len(siblings) - 1
            ):
                siblings[current_idx], siblings[current_idx + 1] = (
                    siblings[current_idx + 1], siblings[current_idx],
                )
            # Re-normalize order_ids based on the new ordering. Rows
            # whose position didn't change get no DB write (cheap +
            # avoids unnecessary updated_datetime bumps).
            for new_index, sibling in enumerate(siblings):
                if sibling.order_id != new_index:
                    sibling.order_id = new_index
                    sibling.save( update_fields = [ 'order_id', 'updated_datetime' ] )

        return self.render_grid_replace( request, owner_type, owner )


class CapabilityConfigureView( HiModalView,
                               IntegrationViewMixin,
                               CapabilityBlockViewMixin,
                               AttributeEditViewMixin ):
    """Base for the per-capability credentials Configure modal.

    Subclasses set the four class-level constants and override
    ``handle_post_success`` to define what happens after credentials save.
    The base owns:
      * the GET render flow (block check -> ensure_all_attributes_exist ->
        build edit context -> render modal)
      * the POST save flow (post_attribute_form -> delegate to subclass)
      * the ``validate_attributes_extra`` hook for AttributeEditViewMixin.

    Subclasses own the timing of ``notify_settings_changed()`` because the
    right moment is capability-specific: Connect-side managers gate client
    (re)build on ``integration.is_enabled``, so the notify must fire AFTER
    ``enable_integration``; Import flows fire it before reading candidates.
    """

    capability    : IntegrationCapability  = None
    button_label  : str                    = None
    template_name : str                    = None
    error_title   : str                    = None

    def get_template_name( self ) -> str:
        return self.template_name

    def get_capability_gateway( self, integration_data ):
        """Return the ``CapabilityGateway`` instance for this configure view's
        capability. Subclasses implement by calling the appropriate
        per-capability getter on the gateway. The base deliberately does not
        enumerate capabilities -- each subclass already knows its own."""
        raise NotImplementedError('Subclasses must override this method')

    def _build_attr_item_context( self, integration_data ):
        return IntegrationAttributeItemEditContext(
            integration_data       = integration_data,
            capability_gateway     = self.get_capability_gateway( integration_data ),
            update_button_label    = self.button_label,
            suppress_history       = True,
            show_secrets           = True,
        )

    def get(self, request, *args, **kwargs):
        integration_manager = IntegrationManager()
        integration_data = self.get_integration_data( request, *args, **kwargs )

        block_response = self.render_capability_block_if_conflict(
            request = request,
            integration_data = integration_data,
            capability_being_initiated = self.capability,
        )
        if block_response is not None:
            return block_response

        integration_manager.ensure_all_attributes_exist(
            integration_metadata = integration_data.integration_metadata,
            integration = integration_data.integration,
        )
        attr_item_context = self._build_attr_item_context( integration_data )
        template_context = self.create_initial_template_context(
            attr_item_context = attr_item_context,
        )
        return self.modal_response( request, template_context )

    def post(self, request, *args, **kwargs):
        integration_data = self.get_integration_data( request, *args, **kwargs )

        # Re-check the mode-switch invariant on POST. The GET path
        # already runs this, but a direct POST (cached form, replayed
        # request) would otherwise bypass it.
        block_response = self.render_capability_block_if_conflict(
            request = request,
            integration_data = integration_data,
            capability_being_initiated = self.capability,
        )
        if block_response is not None:
            return block_response

        attr_item_context = self._build_attr_item_context( integration_data )
        response = self.post_attribute_form(
            request = request,
            attr_item_context = attr_item_context,
        )
        # Errors re-render the form with messages.
        if response.status_code > 299:
            return response
        return self.handle_post_success( request, integration_data )

    def handle_post_success( self, request, integration_data ):
        raise NotImplementedError( 'Subclasses must override.' )

    def validate_attributes_extra( self,
                                   attr_item_context,
                                   regular_attributes_formset,
                                   request ):
        self.validate_attributes_extra_helper(
            attr_item_context,
            regular_attributes_formset,
            error_title = self.error_title,
        )
        return


class IntegrationPlacementView( HiModalView, IntegrationViewMixin,
                                IntegrationPlacementViewMixin ):
    """Placement modal -- single CBV handling both the GET (render) and
    POST (form submission) paths on one URL.

    GET queries currently-unplaced entities for the integration
    (optionally scoped by ``entity_ids`` URL param), runs them through
    the connector's ``group_entities_for_placement``, and renders the
    placement modal. Empty result falls back to a brief acknowledgement
    modal so the operator isn't dropped onto an empty placement.

    POST processes the placement form. The form has two submit buttons
    sharing ``name="action"`` with distinct values (apply vs dismiss);
    this view branches on the value to render either the post-dispatch
    summary modal or the dismiss-confirm modal.
    """

    DISMISS_ACTION_VALUE = 'dismiss'

    def get_template_name( self ) -> str:
        return 'integrations/modals/placement.html'

    def get( self, request, *args, **kwargs ):
        integration_data = self.get_integration_data( request, *args, **kwargs )
        connector = integration_data.integration_gateway.get_connector()
        if connector is None:
            return page_not_found_response( request )

        url_params = PlacementUrlParams.from_data( request.GET )
        is_initial_connect = url_params.is_initial_connect
        entity_id_filter = set( url_params.entity_ids ) if url_params.entity_ids else None

        entities = EntityPlacementService.query_unplaced_entities(
            integration_id = integration_data.integration_id,
        )
        # When the caller scoped the URL to specific entity ids, narrow the
        # unplaced set to those. Without scoping, the placement operates on the
        # full unplaced set for the integration.
        if entity_id_filter is not None:
            entities = [ e for e in entities if e.id in entity_id_filter ]

        placement_input = integration_data.integration_gateway.group_entities_for_placement(
            entities = entities,
        )
        if placement_input.is_empty():
            return self._render_empty(
                request = request,
                integration_data = integration_data,
                connector = connector,
                is_initial_connect = is_initial_connect,
            )
        return self.render_placement(
            request = request,
            integration_data = integration_data,
            placement_input = placement_input,
            is_initial_connect = is_initial_connect,
            entity_id_filter = entity_id_filter,
        )

    def post( self, request, *args, **kwargs ):
        integration_data = self.get_integration_data( request, *args, **kwargs )
        url_params = PlacementUrlParams.from_data( request.POST )
        is_initial_connect = url_params.is_initial_connect

        if request.POST.get('action') == self.DISMISS_ACTION_VALUE:
            entity_ids = self._extract_placement_entity_ids( request )
            return self.render_dismiss_confirm(
                request = request,
                integration_data = integration_data,
                entity_ids = entity_ids,
                is_initial_connect = is_initial_connect,
            )

        decisions = PlacementFormParser.parse(
            request = request, integration_data = integration_data,
        )
        outcome = EntityPlacementService.apply_decisions( decisions = decisions )
        return self.render_post_placement(
            request = request,
            integration_data = integration_data,
            outcome = outcome,
            is_initial_connect = is_initial_connect,
        )

    @staticmethod
    def _extract_placement_entity_ids( request ):
        """Pull the entity ids the placement form just posted. The form
        renders ``all_group_<i>_entity_ids`` per group plus a single
        ``ungrouped_entity_ids`` field -- both carry the entity ids regardless
        of whether the operator opened any drill-down."""
        ids = []
        for key, values in request.POST.lists():
            if key == 'ungrouped_entity_ids' or (
                key.startswith( 'all_group_' )
                and key.endswith( '_entity_ids' )
            ):
                for value in values:
                    try:
                        ids.append( int(value) )
                    except (TypeError, ValueError):
                        continue
        return ids

    def _render_empty( self, request, integration_data,
                       connector, is_initial_connect : bool ):
        """No-unplaced-items acknowledgement: render the result modal with
        the integration's icon and a brief 'no items' info note rather than
        an empty placement."""
        sync_result = IntegrationSyncResult(
            title = connector.get_result_title(
                is_initial_connect = is_initial_connect,
            ),
            info_list = [ 'No items left to place.' ],
        )
        return self.modal_response(
            request,
            context = {
                'sync_result': sync_result,
                'integration_data': integration_data,
                'is_initial_connect': is_initial_connect,
            },
            template_name = 'integrations/connector/modals/sync_result.html',
        )


class IntegrationRefineView( View ):
    """Convenience entry to edit-mode for a specific LocationView. Sets the
    session's current LocationView, flips view mode to EDIT, and redirects
    to the location view page."""

    def get(self, request, *args, **kwargs):
        try:
            location_view_id = int( kwargs.get('location_view_id') )
        except (TypeError, ValueError):
            raise BadRequest( 'Invalid location_view_id' )
        try:
            location_view = LocationView.objects.get( id = location_view_id )
        except LocationView.DoesNotExist:
            return page_not_found_response( request )

        request.view_parameters.view_type = ViewType.LOCATION_VIEW
        request.view_parameters.update_location_view( location_view )
        request.view_parameters.view_mode = ViewMode.EDIT
        request.view_parameters.to_session( request )

        return redirect( reverse(
            'location_view',
            kwargs = { 'location_view_id': location_view.id },
        ) )


class IntegrationAttributeHistoryInlineView( View,
                                             IntegrationViewMixin,
                                             AttributeEditViewMixin ):

    def get(self, request, integration_id, attribute_id, *args, **kwargs):
        # Validate that the attribute belongs to this integration for security
        try:
            attribute = IntegrationAttribute.objects.select_related('integration').get(
                pk = attribute_id, integration_id = integration_id )
        except IntegrationAttribute.DoesNotExist:
            return page_not_found_response(request, "Attribute not found.")

        integration_data = IntegrationManager().get_integration_data(
            integration_id = attribute.integration.integration_id,
        )
        # History inline ops target a specific attribute by id; the
        # capability filter inside the edit context is not consulted
        # here, so no capability gateway is needed.
        attr_item_context = IntegrationAttributeItemEditContext(
            integration_data = integration_data,
            capability_gateway = None,
        )
        return self.get_history(
            request = request,
            attribute = attribute,
            attr_item_context = attr_item_context,
        )


class IntegrationAttributeRestoreInlineView( View,
                                             IntegrationViewMixin,
                                             AttributeEditViewMixin ):

    def get(self, request, integration_id, attribute_id, history_id, *args, **kwargs):
        """ Need to do restore in a GET since nested in main form and cannot have a form in a form """
        try:
            attribute = IntegrationAttribute.objects.select_related('integration').get(
                pk = attribute_id, integration_id = integration_id
            )
        except IntegrationAttribute.DoesNotExist:
            return page_not_found_response(request, "Attribute not found.")

        integration_data = IntegrationManager().get_integration_data(
            integration_id = attribute.integration.integration_id,
        )

        # Restore inline ops target a specific attribute by id; the
        # capability filter inside the edit context is not consulted
        # here, so no capability gateway is needed.
        attr_item_context = IntegrationAttributeItemEditContext(
            integration_data = integration_data,
            capability_gateway = None,
        )
        return self.post_restore(
            request = request,
            attribute = attribute,
            history_id = history_id,
            attr_item_context = attr_item_context,
        )
