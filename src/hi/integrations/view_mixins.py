from django.db.models import Count
from django.http import Http404
from django.urls import reverse

from hi.apps.collection.collection_manager import CollectionManager
from hi.apps.collection.models import Collection, CollectionEntity
from hi.apps.entity.models import EntityView
from hi.apps.location.location_manager import LocationManager
from hi.apps.location.models import Location, LocationView

from .integration_manager import IntegrationManager


class IntegrationViewMixin:

    def get_integration_data( self, integration_id : str ):
        try:
            return IntegrationManager().get_integration_data(
                integration_id = integration_id,
            )
        except KeyError:
            raise Http404()
        return
    
    def get_integration_data_list( self, enabled_only = False ):
        return IntegrationManager().get_integration_data_list(
            enabled_only = enabled_only,
        )
    
    def validate_attributes_extra_helper( self,
                                          attr_item_context,
                                          regular_attributes_formset,
                                          error_title ):
        """
        Validate the proposed integration configuration in two stages:
          1. Schema-level check via gateway.validate_configuration (offline,
             fast). Catches structural problems with the attribute set.
          2. Live connection probe via gateway.test_connection bounded by
             IntegrationManager.HEALTH_CHECK_TIMEOUT_SECS. Catches
             unreachable upstream / bad credentials so the user sees the
             specific reason inline rather than experiencing a silent
             save followed by a delayed background error.

        Both gateway methods are required by their contracts to never
        throw — they convert any internal exception into the appropriate
        result type (IntegrationValidationResult.error /
        ConnectionTestResult.failure) carrying a human-readable message.
        We deliberately do NOT wrap their invocations in a broad try/
        except here: doing so would coerce the gateway's specific
        failure message into a generic catch-all string, and would also
        hide genuine programming bugs (which should surface through
        Django's error pipeline rather than be silently translated into
        a form-level error).
        """
        integration_data = attr_item_context.integration_data
        gateway = integration_data.integration_gateway

        # Get current attribute values from the formset
        integration_attributes = []
        for form in regular_attributes_formset:
            if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                # Create a temporary attribute-like object with the form data
                attr_instance = form.instance
                attr_instance.value = form.cleaned_data.get('value', '')
                integration_attributes.append(attr_instance)

        # Stage 1: schema-only validation.
        validation_result = gateway.validate_configuration(
            integration_attributes
        )
        if not validation_result.is_valid:
            error_message = validation_result.error_message or 'Configuration is invalid'
            regular_attributes_formset._non_form_errors.append(
                f'{error_title}: {error_message}'
            )
            return

        # Stage 2: live connection probe with bounded timeout.
        test_result = gateway.test_connection(
            integration_attributes = integration_attributes,
            timeout_secs = IntegrationManager.HEALTH_CHECK_TIMEOUT_SECS,
        )
        if not test_result.is_success:
            error_message = test_result.message or 'Connection test failed'
            regular_attributes_formset._non_form_errors.append(
                f'{error_title}: {error_message}'
            )
        return


class IntegrationDispatcherViewMixin:
    """Modal context builders shared across the dispatcher /
    dismiss-confirm / post-dispatch views. Knows UI conventions
    (URL routing for the integration dispatcher flow, location-view
    dropdown shape) but no business logic.

    Designed to be mixed into ``HiModalView`` subclasses so the
    rendering methods can call ``self.modal_response(...)`` directly.
    """

    def render_dispatcher( self,
                           request,
                           integration_data,
                           placement_input,
                           is_initial_import : bool ):
        """Render the dispatcher modal seeded with an
        ``EntityPlacementInput``. Dropdowns offer both LocationView
        and Collection targets; the top dropdown additionally offers
        '+ New view' and '+ New collection' sentinels.

        Computes two presentation aids in the view rather than the
        template: a smart default for the top dropdown
        (``top_default_value``) and an inventory preview line shown
        beneath it (``inventory_preview``). The template is then a
        thin renderer of these and the placement_input itself.
        """
        location_view_groups = self._build_location_view_groups()
        collection_list = self._build_collection_list()
        new_view_name, new_collection_name = self._derive_new_target_names(
            request = request,
            integration_label = integration_data.label,
        )
        top_default_value = self._compute_top_default_value(
            integration_id = integration_data.integration_id,
            is_initial_import = is_initial_import,
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
        apply_url = reverse(
            'integrations_apply_placements',
            kwargs = { 'integration_id': integration_data.integration_id },
        )
        dismiss_url = reverse(
            'integrations_dispatcher_dismiss',
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
                'apply_url': apply_url,
                'dismiss_url': dismiss_url,
                'is_initial_import': is_initial_import,
            },
            template_name = 'integrations/modals/dispatcher.html',
        )

    def render_dismiss_confirm( self,
                                request,
                                integration_data,
                                is_initial_import : bool ):
        """Render the NOT NOW confirmation modal. GO BACK targets
        the dispatcher GET endpoint, with is_initial_import threaded
        through as a query parameter."""
        dispatcher_url = reverse(
            'integrations_dispatcher',
            kwargs = { 'integration_id': integration_data.integration_id },
        )
        if is_initial_import:
            dispatcher_url = f'{dispatcher_url}?is_initial_import=1'
        return self.modal_response(
            request,
            context = {
                'integration_data': integration_data,
                'dispatcher_url': dispatcher_url,
            },
            template_name = 'integrations/modals/dispatcher_dismiss.html',
        )

    def render_post_dispatch( self,
                              request,
                              integration_data,
                              outcome,
                              is_initial_import : bool ):
        """Render the post-dispatch summary modal from a
        ``PlacementOutcome``.

        The primary action button is REFINE for view-targeted
        primary summaries (drag entities into spatial position) and
        REVIEW for collection-targeted primary summaries (no spatial
        refinement; the link just lands on the collection's view
        page). ``PlacementOutcome.primary_summary`` already prefers
        view-targeted summaries when any exist, so the REFINE path
        is taken whenever the operator placed at least one entity
        into a LocationView."""
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
                'is_initial_import': is_initial_import,
                'primary_action': primary_action,
                'secondary_action_list': secondary_action_list,
            },
            template_name = 'integrations/modals/post_dispatch.html',
        )

    def _build_location_view_groups( self ):
        """Existing-views dropdown source: ``[(Location,
        [LocationView])]`` ordered by Location.order_id, views by
        LocationView.order_id within each. Always grouped (never
        flat) so multi-Location deployments can disambiguate views
        with shared names. Single SQL query joining LocationView ↔
        Location; insertion-order in the dict preserves the sort
        from the database. Empty Locations drop out, which is the
        right behavior for a dropdown source."""
        queryset = LocationView.objects.select_related('location').order_by(
            'location__order_id', 'order_id',
        )
        groups : dict = {}
        for view in queryset:
            groups.setdefault( view.location, [] ).append( view )
        return list( groups.items() )

    def _build_collection_list( self ):
        """Existing-collections dropdown source for the dispatcher
        modal. Single optgroup keyed by 'Collections'; ordered by
        Collection.order_id."""
        return list( Collection.objects.order_by('order_id').all() )

    def _summary_url( self, summary ) -> str:
        """URL for the post-dispatch modal's per-summary action.
        Views go through ``integrations_refine`` (which lands the
        operator in edit mode for that view); collections link to
        the read-only ``collection_view`` page."""
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
                                    is_initial_import : bool ) -> str:
        """Smart default for the dispatcher's top dropdown.

        On Initial Import the operator has no existing target — pre-
        select '+ New view' so they can click APPLY without further
        input.

        On Refresh, prefer whichever existing target (LocationView
        OR Collection) currently holds the most entities for this
        integration. Ties broken by id ascending (deterministic).
        Falls back to '' (Don't place) when no existing target holds
        any of this integration's entities — operator picks.
        """
        if is_initial_import:
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
            # Equal counts — prefer lower target type ordinal. Views
            # before collections is an arbitrary but deterministic
            # tiebreak; the operator's own count was already a true
            # tie so either answer is fine.
            return f'view:{top_view["location_view_id"]}'

        if top_view:
            return f'view:{top_view["location_view_id"]}'
        if top_collection:
            return f'collection:{top_collection["collection_id"]}'
        return ''

    def _derive_new_target_names( self, request, integration_label : str ) -> tuple:
        """Pre-resolve the names that the '+ New view' / '+ New
        collection' options would actually produce on Apply, so the
        dropdown labels match the operator's eventual reality.

        Without this, an operator who already has a view named
        'Home Assistant' would see the option 'New view: "Home
        Assistant"' but get a view named 'Home Assistant (2)' on
        save — confusing.

        Returns ``(new_view_name, new_collection_name)``. Falls
        back to ``integration_label`` for the view name when no
        default Location is configured (the apply path will raise
        BadRequest in that case anyway; the modal label just shows
        the un-disambiguated label).

        Race-condition note: another operator could create a same-
        named view/collection between render and submit, in which
        case the apply-time disambiguation produces a different
        suffix than the modal advertised. This is an extremely rare
        case and the apply-time logic always picks a free name, so
        no special handling is needed.
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

        Used as a single-line preview beneath the top dropdown when
        the operator has the group rows collapsed — preserves the
        'free preview of what's about to be imported' signal that
        the always-visible group cards previously provided.

        Returns an empty list for the all-ungrouped case (HomeBox-
        style). Callers should hide the preview entirely in that
        case, since restating the count is just noise.
        """
        if not placement_input.groups:
            return []
        return [
            { 'label': group.label, 'count': len( group.items ) }
            for group in placement_input.groups
        ]
