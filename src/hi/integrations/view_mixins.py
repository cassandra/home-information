from django.http import Http404
from django.urls import reverse

from hi.apps.location.models import LocationView

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
        ``EntityPlacementInput``."""
        location_view_groups = self._build_location_view_groups()
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
        ``PlacementOutcome``. Builds the primary REFINE link and a
        list of secondary view links, all pointing at
        ``integrations_refine``."""
        primary = outcome.primary_summary
        primary_refine = None
        secondary_refine_list = []
        if primary is not None:
            primary_refine = ( primary, self._refine_url( primary.location_view ) )
            for summary in outcome.secondary_summaries:
                secondary_refine_list.append(
                    ( summary, self._refine_url( summary.location_view ) )
                )
        return self.modal_response(
            request,
            context = {
                'integration_data': integration_data,
                'outcome': outcome,
                'is_initial_import': is_initial_import,
                'primary_refine': primary_refine,
                'secondary_refine_list': secondary_refine_list,
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

    def _refine_url( self, location_view : LocationView ) -> str:
        return reverse(
            'integrations_refine',
            kwargs = { 'location_view_id': location_view.id },
        )
