from typing import FrozenSet, Optional

from django.core.exceptions import BadRequest
from django.db.models import Count
from django.http import Http404
from django.shortcuts import render
from django.urls import reverse

from hi.apps.collection.collection_manager import CollectionManager
from hi.apps.collection.models import Collection, CollectionEntity
from hi.apps.entity.entity_placement import PLACEMENT_DEFAULT_HEADING
from hi.apps.entity.models import Entity, EntityView
from hi.apps.location.location_manager import LocationManager
from hi.apps.location.models import Location, LocationView

from hi.integrations.enums import IntegrationCapability
from hi.integrations.integration_manager import IntegrationManager
from hi.integrations.models import (
    EntityExternalReference,
    LocationExternalReference,
)

from hi.integrations.placement_request import PlacementUrlParams


class IntegrationViewMixin:

    def get_integration_data( self, request, *args, **kwargs ):
        """Resolve the URL-routed integration_id to its IntegrationData.

        Requires ``integration_id`` in kwargs; raises BadRequest if missing
        and Http404 if not registered."""
        integration_id = kwargs.get('integration_id')
        if not integration_id:
            raise BadRequest('Missing integration id.')
        try:
            return IntegrationManager().get_integration_data(
                integration_id = integration_id,
            )
        except KeyError:
            raise Http404(request)

    def get_integration_data_list(
            self,
            enabled_only : bool                                            = False,
            capabilities : Optional[ FrozenSet[ IntegrationCapability ] ]  = None,
    ):
        return IntegrationManager().get_integration_data_list(
            enabled_only = enabled_only,
            capabilities = capabilities,
        )

    def validate_attributes_extra_helper( self,
                                          attr_item_context,
                                          regular_attributes_formset,
                                          error_title ):
        """
        Validate the proposed integration configuration in two stages:
          1. Schema-level check (offline, fast). Catches structural problems
             with the attribute set.
          2. Live access validation with bounded timeout. Catches unreachable
             upstream / bad credentials so the user sees the specific reason
             inline rather than experiencing a silent save followed by a delayed
             background error.

        Both gateway methods are contractually required to never throw -- they
        convert any internal exception into the appropriate result type
        carrying a human-readable message. We deliberately do NOT wrap their
        invocations in a broad try/except here: that would coerce the gateway's
        specific failure message into a generic catch-all string, and would
        hide genuine programming bugs (which should surface through Django's
        error pipeline rather than be silently translated into a form-level
        error).
        """
        integration_data = attr_item_context.integration_data
        gateway = integration_data.integration_gateway

        integration_attributes = []
        for form in regular_attributes_formset:
            if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                attr_instance = form.instance
                attr_instance.value = form.cleaned_data.get('value', '')
                integration_attributes.append(attr_instance)

        validation_result = gateway.validate_configuration(
            integration_attributes
        )
        if not validation_result.is_valid:
            error_message = validation_result.error_message or 'Configuration is invalid'
            regular_attributes_formset._non_form_errors.append(
                f'{error_title}: {error_message}'
            )
            return

        test_result = gateway.validate_access(
            integration_attributes = integration_attributes,
            timeout_secs = IntegrationManager.HEALTH_CHECK_TIMEOUT_SECS,
        )
        if not test_result.is_success:
            error_message = test_result.message or 'Access validation failed'
            regular_attributes_formset._non_form_errors.append(
                f'{error_title}: {error_message}'
            )
        return


class IntegrationPlacementViewMixin:
    """Modal context builders shared across the placement /
    dismiss-confirm / post-dispatch views. Knows UI conventions
    (URL routing for the integration placement flow, location-view
    dropdown shape) but no business logic."""

    def render_placement( self,
                          request,
                          integration_data,
                          placement_input,
                          is_initial_connect : bool,
                          entity_id_filter = None ):
        """Render the placement modal seeded with an ``EntityPlacementInput``.
        Dropdowns offer both LocationView and Collection targets; the top
        dropdown additionally offers '+ New view' and '+ New collection'
        sentinels.

        Computes two presentation aids in the view rather than the template:
        a smart default for the top dropdown (``top_default_value``) and an
        inventory preview line shown beneath it (``inventory_preview``).
        """
        location_view_groups = self._build_location_view_groups()
        collection_list = self._build_collection_list()
        new_view_name, new_collection_name = self._derive_new_target_names(
            request = request,
            integration_label = integration_data.label,
        )
        top_default_value = self._compute_top_default_value(
            integration_id = integration_data.integration_id,
            is_initial_connect = is_initial_connect,
        )
        # Decompose the tagged value into per-kind ids so the
        # template can do direct integer comparisons in the
        # existing-view / existing-collection option loops.
        top_default_view_id = None
        top_default_collection_id = None
        if top_default_value.startswith( 'view:' ):
            top_default_view_id = int( top_default_value[ len('view:') : ] )
        elif top_default_value.startswith( 'collection:' ):
            top_default_collection_id = int( top_default_value[ len('collection:') : ] )
        inventory_preview = self._build_inventory_preview(
            placement_input = placement_input,
        )
        # Suppress the column-header heading when the grouping dimension is
        # the implicit default ("Item Type") -- it adds no information. The
        # heading still renders when an integration override conveys context
        # (e.g. "HomeBox Location").
        grouping_heading = (
            placement_input.heading
            if placement_input.heading != PLACEMENT_DEFAULT_HEADING
            else None
        )
        # Form posts back to the same URL that rendered the modal -- single
        # CBV, GET renders / POST processes.
        placement_url = reverse(
            'integrations_placement',
            kwargs = { 'integration_id': integration_data.integration_id },
        )
        return self.modal_response(
            request,
            context = {
                'integration_data': integration_data,
                'placement_input': placement_input,
                'location_view_groups': location_view_groups,
                'collection_list': collection_list,
                'top_default_value': top_default_value,
                'top_default_view_id': top_default_view_id,
                'top_default_collection_id': top_default_collection_id,
                'new_view_name': new_view_name,
                'new_collection_name': new_collection_name,
                'inventory_preview': inventory_preview,
                'grouping_heading': grouping_heading,
                'placement_url': placement_url,
                'is_initial_connect': is_initial_connect,
            },
            template_name = 'integrations/modals/placement.html',
        )

    def render_dismiss_confirm( self,
                                request,
                                integration_data,
                                is_initial_connect : bool,
                                entity_ids = None ):
        """Render the dismiss confirmation modal. The back action targets the
        placement GET endpoint with is_initial_connect and (when present) the
        entity-id scope threaded through as query parameters so the operator
        returns to the same set they were viewing."""
        placement_url = PlacementUrlParams(
            is_initial_connect = is_initial_connect,
            entity_ids = list( entity_ids ) if entity_ids else [],
        ).append_to_url( reverse(
            'integrations_placement',
            kwargs = { 'integration_id': integration_data.integration_id },
        ) )
        return self.modal_response(
            request,
            context = {
                'integration_data': integration_data,
                'placement_url': placement_url,
            },
            template_name = 'integrations/modals/placement_dismiss.html',
        )

    def render_post_placement( self,
                               request,
                               integration_data,
                               outcome,
                               is_initial_connect : bool ):
        """Render the post-dispatch summary modal from a ``PlacementOutcome``.

        The primary action targets the view-refinement endpoint for view-
        targeted primary summaries (drag entities into spatial position) and
        the collection-view page for collection-targeted primary summaries
        (no spatial refinement). ``PlacementOutcome.primary_summary`` already
        prefers view-targeted summaries when any exist."""
        primary = outcome.primary_summary
        primary_action = None
        secondary_action_list = []
        if primary is not None:
            primary_action = ( primary, self._summary_url( primary ) )
            for summary in outcome.secondary_summaries:
                secondary_action_list.append(
                    ( summary, self._summary_url( summary ) )
                )
        return self.modal_response(
            request,
            context = {
                'integration_data': integration_data,
                'outcome': outcome,
                'is_initial_connect': is_initial_connect,
                'primary_action': primary_action,
                'secondary_action_list': secondary_action_list,
            },
            template_name = 'integrations/modals/post_placement.html',
        )

    def _build_location_view_groups( self ):
        """Existing-views dropdown source: ``[(Location, [LocationView])]``
        ordered by Location.order_id, views by LocationView.order_id within
        each. Always grouped (never flat) so multi-Location deployments can
        disambiguate views with shared names. Single SQL query joining
        LocationView and Location; insertion-order in the dict preserves the
        sort from the database. Empty Locations drop out."""
        queryset = LocationView.objects.select_related('location').order_by(
            'location__order_id', 'order_id',
        )
        groups : dict = {}
        for view in queryset:
            groups.setdefault( view.location, [] ).append( view )
        return list( groups.items() )

    def _build_collection_list( self ):
        """Existing-collections dropdown source for the placement
        modal. Single optgroup keyed by 'Collections'; ordered by
        Collection.order_id."""
        return list( Collection.objects.order_by('order_id').all() )

    def _summary_url( self, summary ) -> str:
        """URL for each per-summary action. Views go through ``integrations_refine``
        (which lands the operator in edit mode for that view); collections link
        to the read-only ``collection_view`` page."""
        if summary.is_view:
            return reverse(
                'integrations_refine',
                kwargs = { 'location_view_id': summary.location_view.id },
            )
        return reverse(
            'collection_view',
            kwargs = { 'collection_id': summary.collection.id },
        )

    def _compute_top_default_value( self,
                                    integration_id    : str,
                                    is_initial_connect : bool ) -> str:
        """Smart default for the placement's top dropdown.

        On Initial Connect the operator has no existing target -- pre-select
        '+ New view' so they can apply without further input.

        On update check, prefer whichever existing target (LocationView OR
        Collection) currently holds the most entities for this integration.
        Ties broken by id ascending (deterministic). Falls back to '' (no
        default) when no existing target holds any of this integration's
        entities -- operator picks.
        """
        if is_initial_connect:
            return '__new_view__'

        view_counts = list(
            EntityView.objects
            .filter( entity__integration_id = integration_id )
            .values( 'location_view_id' )
            .annotate( count = Count( 'id' ) )
            .order_by( '-count', 'location_view_id' )
        )
        collection_counts = list(
            CollectionEntity.objects
            .filter( entity__integration_id = integration_id )
            .values( 'collection_id' )
            .annotate( count = Count( 'id' ) )
            .order_by( '-count', 'collection_id' )
        )

        top_view = view_counts[0] if view_counts else None
        top_collection = collection_counts[0] if collection_counts else None

        if top_view and top_collection:
            view_count = top_view['count']
            collection_count = top_collection['count']
            if view_count > collection_count:
                return f'view:{top_view["location_view_id"]}'
            if collection_count > view_count:
                return f'collection:{top_collection["collection_id"]}'
            # Equal counts -- prefer lower target type ordinal. Views before
            # collections is an arbitrary but deterministic tiebreak; the
            # operator's own count was already a true tie so either answer is fine.
            return f'view:{top_view["location_view_id"]}'

        if top_view:
            return f'view:{top_view["location_view_id"]}'
        if top_collection:
            return f'collection:{top_collection["collection_id"]}'
        return ''

    def _derive_new_target_names( self, request, integration_label : str ) -> tuple:
        """Pre-resolve the names that the '+ New view' / '+ New collection'
        options would actually produce on Apply, so the dropdown labels match
        the operator's eventual reality.

        Without this, an operator who already has a view named 'Home Assistant'
        would see the option 'New view: "Home Assistant"' but get a view named
        'Home Assistant (2)' on save -- confusing.

        Returns ``(new_view_name, new_collection_name)``. Falls back to
        ``integration_label`` for the view name when no default Location is
        configured (the apply path will raise BadRequest in that case; the
        modal label just shows the un-disambiguated label).

        Race-condition note: another operator could create a same-named
        view/collection between render and submit, in which case the apply-time
        disambiguation produces a different suffix than the modal advertised.
        This is rare and the apply-time logic always picks a free name, so no
        special handling is needed.
        """
        try:
            location = LocationManager().get_default_location( request = request )
            new_view_name = LocationManager().resolve_unique_view_name(
                location = location,
                requested_name = integration_label,
            )
        except Location.DoesNotExist:
            new_view_name = integration_label
        new_collection_name = CollectionManager().resolve_unique_collection_name(
            requested_name = integration_label,
        )
        return new_view_name, new_collection_name

    def _build_inventory_preview( self, placement_input ) -> list:
        """Compact label/count summary of what's about to be placed.

        Used as a single-line preview beneath the top dropdown when the
        operator has the group rows collapsed.

        Returns an empty list for the truly-ungrouped case (no groups, only
        ``ungrouped_items``). Callers should hide the preview entirely in that
        case, since restating the count is just noise.
        """
        if not placement_input.groups:
            return []
        return [
            { 'label': group.label, 'count': len( group.items ) }
            for group in placement_input.groups
        ]


class ExternalReferenceCardViewMixin:
    """Helpers for the per-card external-reference action views
    (rename, delete, reorder). Centralizes the owner_type-to-model
    binding and the post-mutation grid-replace render. The
    owner_type URL segment doubles as the foreign-key attribute
    name on the row, so the binding is a flat string -> model
    dict."""

    EXTERNAL_REFERENCE_MODELS = {
        'entity'  : EntityExternalReference,
        'location': LocationExternalReference,
    }
    GRID_TEMPLATE = 'integrations/panes/external_reference_grid.html'

    def get_external_reference_or_404( self, owner_type : str, reference_id : int ):
        """Resolve a row by (owner_type, id). Raises Http404 on an
        unknown owner type or a missing row -- the same response
        either way so probing the wrong path never reveals whether a
        row exists under the other type."""
        model = self.EXTERNAL_REFERENCE_MODELS.get( owner_type )
        if model is None:
            raise Http404
        try:
            return model.objects.get( pk = reference_id )
        except model.DoesNotExist:
            raise Http404

    def render_grid_replace( self, request, owner_type : str, owner ):
        """Re-render the grid as plain HTML. The action source
        elements (per-card inputs / buttons) carry
        ``data-async="#<grid_id>"`` and ``data-mode="replace"``, so
        antinode's ``replaceWith`` swaps the targeted grid element
        with this response. View and template never duplicate the
        target id -- the template owns it. Owner is passed
        explicitly so the delete view (whose row is gone
        post-mutation) can use the same path."""
        model = self.EXTERNAL_REFERENCE_MODELS[ owner_type ]
        external_references = model.objects.filter(
            **{ owner_type: owner },
        ).order_by( 'order_id', '-created_datetime' )
        return render(
            request,
            self.GRID_TEMPLATE,
            {
                'external_references': external_references,
                'owner_type'         : owner_type,
                'owner_id'           : owner.id,
            },
        )


class CapabilityBlockViewMixin:
    """Block IMPORT initiation when the integration has active Connect
    entities, directing the user to disable the integration first.

    The asymmetry is principled. CONNECT does not need a symmetric block:
    sync's reconnect-then-create order will adopt any pre-existing
    detached/imported rows for the same integration into the live Connect
    session, so no collision is possible. IMPORT creates new HI-owned rows,
    which would collide with active-Connect rows unless we block this entry
    point.
    """

    def render_capability_block_if_conflict(
            self,
            request,
            integration_data,
            capability_being_initiated : IntegrationCapability,
    ):
        if capability_being_initiated != IntegrationCapability.IMPORT:
            return None
        capabilities = integration_data.integration_metadata.capabilities
        if IntegrationCapability.CONNECT not in capabilities:
            return None

        existing_count = Entity.objects.external_for(
            integration_id = integration_data.integration_id,
        ).count()
        if existing_count == 0:
            return None

        return self.modal_response(
            request,
            context = {
                'integration_data': integration_data,
                'my_label': 'Import',
                'existing_count': existing_count,
                'existing_mode_clause': (
                    'already configured as a Connector with'
                ),
                'desired_action_clause': (
                    f'use {integration_data.label} as a Data Importer'
                ),
                'remediation_clause': (
                    f'disable the {integration_data.label} '
                    f'Connector'
                ),
                'link_url': reverse( 'integrations_connect_home' ),
                'link_label': 'GO TO CONNECTORS',
            },
            template_name = 'integrations/modals/capability_blocked.html',
        )
