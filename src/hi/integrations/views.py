import logging
from collections import OrderedDict

from django.core.exceptions import BadRequest
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import View

from hi.apps.common import antinode
from hi.enums import ViewMode, ViewType
from hi.exceptions import ForceRedirectException
from hi.hi_async_view import HiModalView
from hi.views import page_not_found_response

from hi.apps.attribute.response_helpers import AttributeRedirectResponse
from hi.apps.attribute.view_mixins import AttributeEditViewMixin
from hi.apps.config.enums import ConfigPageType
from hi.apps.config.views import ConfigPageView
from hi.apps.entity.entity_placement import EntityPlacer
from hi.apps.entity.models import Entity
from hi.apps.location.models import LocationView

from .entity_operations import EntityIntegrationOperations
from .enums import IntegrationDisableMode
from .exceptions import IntegrationConnectionError
from .integration_attribute_edit_context import IntegrationAttributeItemEditContext
from .integration_manager import IntegrationManager
from .models import IntegrationAttribute
from .sync_dispatch import (
    DispatcherOutcome,
    FORM_VALUE_NEW_VIEW,
    FORM_VALUE_SKIP,
    PlacementDecision,
    ViewPlacementSummary,
)
from .view_mixins import IntegrationViewMixin

logger = logging.getLogger(__name__)


class IntegrationHomeView( ConfigPageView, IntegrationViewMixin ):

    def config_page_type(self) -> ConfigPageType:
        return ConfigPageType.INTEGRATIONS

    def get_main_template_name( self ) -> str:
        return 'integrations/pages/no_integrations.html'

    def get_main_template_context( self, request, *args, **kwargs ):

        integration_data = IntegrationManager().get_default_integration_data()
        if not integration_data:
            return dict()

        redirect_url = reverse( 'integrations_manage',
                                kwargs = { 'integration_id': integration_data.integration_id })
        raise ForceRedirectException( redirect_url )

    
class IntegrationSelectView( HiModalView, IntegrationViewMixin ):

    def get_template_name( self ) -> str:
        return 'integrations/modals/integrations_select.html'

    def get( self, request, *args, **kwargs ):
        context = {
            'integration_data_list': self.get_integration_data_list(),
        }
        return self.modal_response( request, context )


class IntegrationHealthStatusView( HiModalView, IntegrationViewMixin ):

    def get_template_name( self ) -> str:
        return 'system/modals/health_status.html'

    def get( self, request, *args, **kwargs ):
        integration_id = kwargs.get('integration_id')
        integration_data = self.get_integration_data(
            integration_id = integration_id,
        )
        health_status_provider = integration_data.integration_gateway.get_health_status_provider()
        context = {
            'health_status_provider': health_status_provider,
        }
        return self.modal_response( request, context )


class IntegrationPreSyncView( HiModalView, IntegrationViewMixin ):
    """
    Pre-sync confirmation modal. Surfaces the synchronizer's
    description and offers Sync / Not now actions. Used as the last
    step of the Configure flow (first-time sync) and from the IMPORT /
    REFRESH button on the integration manage page (subsequent syncs).

    The modal does not display integration health: an unhealthy
    integration's sync attempt will surface its failure inline with a
    useful error message, and rendering health here would also expose
    the brief race window between IntegrationManager.enable_integration
    flipping is_enabled in the DB and the manager singleton's
    notify_settings_changed reload (driven by a 0.1s post-commit
    delayed signal processor — deliberately deferred to avoid a
    different, worse class of problems).

    404s when the integration does not provide a synchronizer (sync is
    opt-in capability — not every integration supports it).
    """

    def get_template_name( self ) -> str:
        return 'integrations/modals/pre_sync_confirm.html'

    def get( self, request, *args, **kwargs ):
        integration_id = kwargs.get('integration_id')
        integration_data = self.get_integration_data(
            integration_id = integration_id,
        )
        synchronizer = integration_data.integration_gateway.get_synchronizer()
        if synchronizer is None:
            return page_not_found_response( request )

        is_initial_import = not Entity.objects.filter(
            integration_id = integration_data.integration_id,
        ).exists()
        sync_url = reverse(
            'integrations_sync',
            kwargs = { 'integration_id': integration_data.integration_id },
        )
        review_config_url = reverse(
            'integrations_enable',
            kwargs = { 'integration_id': integration_data.integration_id },
        )

        context = {
            'integration_data': integration_data,
            'is_initial_import': is_initial_import,
            'sync_description': synchronizer.get_description(
                is_initial_import = is_initial_import,
            ),
            'sync_url': sync_url,
            'review_config_url': review_config_url,
        }
        return self.modal_response( request, context )


class IntegrationSyncView( HiModalView, IntegrationViewMixin ):
    """
    Framework sync execution view. Invokes the integration's
    synchronizer; on success transitions into the dispatcher modal
    (Phase 3) for post-sync entity placement. Errors and empty
    results fall back to the legacy result modal so the operator
    sees what happened either way.
    """

    def get_template_name( self ) -> str:
        return 'integrations/modals/dispatcher.html'

    def post( self, request, *args, **kwargs ):
        integration_id = kwargs.get('integration_id')
        integration_data = self.get_integration_data(
            integration_id = integration_id,
        )
        synchronizer = integration_data.integration_gateway.get_synchronizer()
        if synchronizer is None:
            return page_not_found_response( request )

        # Compute the operator-flow flag BEFORE running sync so the
        # entities the sync is about to create don't change the
        # answer. is_initial_import = "no entities for this
        # integration before this sync ran"; the value is threaded
        # through the dispatcher form so the post-dispatch modal
        # can title itself consistently with the pre-sync intent.
        is_initial_import = not Entity.objects.filter(
            integration_id = integration_data.integration_id,
        ).exists()

        sync_result = synchronizer.sync()

        # Errors or no new entities → render the legacy result modal.
        # Refresh-with-no-new-items lands here naturally because each
        # synchronizer only populates groups/ungrouped_items from
        # newly-created entities, not from updates.
        if sync_result.error_list or not _sync_result_has_entities( sync_result ):
            return self.modal_response(
                request,
                context = { 'sync_result': sync_result },
                template_name = 'integrations/modals/sync_result.html',
            )

        location_view_groups = _build_location_view_groups()
        dispatch_url = reverse(
            'integrations_dispatch',
            kwargs = { 'integration_id': integration_data.integration_id },
        )
        return self.modal_response(
            request,
            context = {
                'integration_data': integration_data,
                'sync_result': sync_result,
                'location_view_groups': location_view_groups,
                'dispatch_url': dispatch_url,
                'is_initial_import': is_initial_import,
            },
        )


def _sync_result_has_entities( sync_result ) -> bool:
    if sync_result.ungrouped_items:
        return True
    return any( group.items for group in sync_result.groups )


def _build_location_view_groups():
    """Build the dispatcher's existing-views dropdown source: a list
    of (Location, [LocationView]) tuples ordered by Location.order_id
    with views ordered by LocationView.order_id within each. Always
    grouped (never flat) so multi-Location deployments can
    disambiguate views with shared names.

    Single SQL query joining LocationView ↔ Location; insertion-order
    in the dict preserves the (location.order_id, view.order_id) sort
    that came from the database. Empty Locations (no views) drop
    out, which is the right behavior for a dropdown source.
    """
    queryset = LocationView.objects.select_related('location').order_by(
        'location__order_id', 'order_id',
    )
    groups : dict = {}
    for view in queryset:
        groups.setdefault( view.location, [] ).append( view )
    return list( groups.items() )


class IntegrationDispatcherView( HiModalView, IntegrationViewMixin ):
    """
    Applies operator placement choices from the dispatcher modal.
    Reads form input (group view + per-item drill-down + ungrouped),
    expands to per-entity ``PlacementDecision`` values, places
    entities into their chosen views via ``EntityPlacer``, and
    returns the post-dispatch summary modal.
    """

    def get_template_name( self ) -> str:
        return 'integrations/modals/post_dispatch.html'

    def post( self, request, *args, **kwargs ):
        integration_id = kwargs.get('integration_id')
        integration_data = self.get_integration_data(
            integration_id = integration_id,
        )

        decisions = self._build_decisions(
            request = request, integration_data = integration_data )
        # Carried forward from the sync flow's pre-sync state — see
        # IntegrationSyncView.post. No DB query here; the form field
        # is the authoritative signal of operator intent.
        is_initial_import = ( request.POST.get('is_initial_import') == '1' )

        outcome = self._apply_decisions( decisions = decisions )

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
        )

    def _build_decisions( self, request, integration_data ) -> list:
        """Parse form input into a list of PlacementDecision values
        applying three-level inheritance (top → group → entity).

        Form-input contract (matches dispatcher.html):

        * ``top_view`` — top-level default for every imported entity.
          Values: '' (skip all), '__new__' (create a fresh view),
          or '<view_id>' (existing view).
        * For each group i:
            - ``all_group_{i}_entity_ids`` lists every entity id.
            - ``group_view_{i}`` is the group choice. Values: ''
              (use top), '__skip__' (explicit skip), '<view_id>'.
            - ``group_{i}_entity_{E}_view`` is the per-entity
              override. Values: '' (use group), '__skip__', '<view_id>'.
        * For ungrouped:
            - ``ungrouped_entity_ids`` lists every entity.
            - ``ungrouped_entity_{E}_view`` is the per-entity choice
              against the top default. Values: '' (use top),
              '__skip__', '<view_id>'.

        New-view creation: when ``top_view == FORM_VALUE_NEW_VIEW``,
        a fresh LocationView is created (named after the integration
        label) and used as the top-level resolved view. Group/entity
        overrides to other existing views still apply.
        """
        decisions = []
        view_lookup = self._build_view_lookup()

        top_value = request.POST.get('top_view', '').strip()
        top_view = self._resolve_top_view(
            request = request,
            top_value = top_value,
            view_lookup = view_lookup,
            integration_data = integration_data,
        )

        # Discover group indices by scanning POST keys.
        group_indices = sorted({
            int(k.split('_')[2])
            for k in request.POST.keys()
            if k.startswith('all_group_') and k.endswith('_entity_ids')
        })
        for group_index in group_indices:
            group_value = request.POST.get(
                f'group_view_{group_index}', '' ).strip()
            group_choice = self._resolve_child_choice(
                form_value = group_value,
                parent_view = top_view,
                view_lookup = view_lookup,
            )
            entity_id_list = request.POST.getlist(
                f'all_group_{group_index}_entity_ids' )
            entities = list( Entity.objects.filter(
                id__in = [int(e) for e in entity_id_list]
            ) )
            entity_by_id = { e.id: e for e in entities }
            for entity_id_str in entity_id_list:
                entity = entity_by_id.get( int(entity_id_str) )
                if entity is None:
                    continue
                entity_value = request.POST.get(
                    f'group_{group_index}_entity_{entity.id}_view', '' ).strip()
                entity_choice = self._resolve_child_choice(
                    form_value = entity_value,
                    parent_view = group_choice,
                    view_lookup = view_lookup,
                )
                decisions.append( PlacementDecision(
                    entity = entity, location_view = entity_choice,
                ) )

        # Ungrouped items: no group level — entity inherits from top.
        ungrouped_ids = request.POST.getlist( 'ungrouped_entity_ids' )
        if ungrouped_ids:
            ungrouped = list( Entity.objects.filter(
                id__in = [int(e) for e in ungrouped_ids]
            ) )
            ungrouped_by_id = { e.id: e for e in ungrouped }
            for entity_id_str in ungrouped_ids:
                entity = ungrouped_by_id.get( int(entity_id_str) )
                if entity is None:
                    continue
                entity_value = request.POST.get(
                    f'ungrouped_entity_{entity.id}_view', '' ).strip()
                entity_choice = self._resolve_child_choice(
                    form_value = entity_value,
                    parent_view = top_view,
                    view_lookup = view_lookup,
                )
                decisions.append( PlacementDecision(
                    entity = entity, location_view = entity_choice,
                ) )

        return decisions

    def _resolve_top_view( self,
                           request,
                           top_value        : str,
                           view_lookup      : dict,
                           integration_data ):
        """Top-level form value → resolved LocationView (or None for skip).

        Three valid top values: ''=skip-all, '__new__'=create fresh
        view, '<id>'=existing view. Creation of the new view is the
        side effect of '__new__'; the new view becomes the top
        default for everything else.
        """
        if top_value == FORM_VALUE_NEW_VIEW:
            return self._create_new_view(
                request = request, integration_data = integration_data )
        if top_value == '':
            return None
        return view_lookup.get( top_value )

    def _resolve_child_choice( self,
                               form_value   : str,
                               parent_view,
                               view_lookup  : dict ):
        """Group/entity form value → resolved LocationView (or None
        for skip). Empty inherits from parent; '__skip__' is an
        explicit no-op that overrides any inherited parent value;
        otherwise it's an explicit existing-view id."""
        if form_value == '':
            return parent_view
        if form_value == FORM_VALUE_SKIP:
            return None
        return view_lookup.get( form_value )

    def _create_new_view( self, request, integration_data ):
        """Create a single LocationView named after the integration
        label, attached to the operator's current default Location
        (per session view_parameters). LocationManager's
        get_default_location handles the session-first lookup with a
        DB-order fallback when nothing is set."""
        from hi.apps.location.location_manager import LocationManager
        from hi.apps.location.models import Location
        try:
            location = LocationManager().get_default_location( request = request )
        except Location.DoesNotExist:
            raise BadRequest(
                'Cannot create a new view: no Location is configured.'
            )
        return LocationManager().create_location_view(
            location = location,
            name = integration_data.label,
        )

    def _build_view_lookup(self) -> dict:
        return { str(v.id): v for v in LocationView.objects.all() }

    def _apply_decisions( self, decisions : list ) -> DispatcherOutcome:
        outcome = DispatcherOutcome()
        # Group decisions by location_view (preserving first-seen
        # order so the post-dispatch summary lists views in the
        # order the operator's groups produced them).
        by_view = OrderedDict()
        for decision in decisions:
            if decision.location_view is None:
                outcome.skipped_entity_count += 1
                continue
            by_view.setdefault( decision.location_view.id, [] ).append( decision )
            continue
        for view_id, decision_list in by_view.items():
            location_view = decision_list[0].location_view
            entities = [ d.entity for d in decision_list ]
            EntityPlacer().place_entities_in_view(
                entities = entities, location_view = location_view,
            )
            outcome.summaries.append( ViewPlacementSummary(
                location_view = location_view,
                placed_entity_count = len( entities ),
            ) )
            continue
        return outcome

    def _refine_url( self, location_view : LocationView ) -> str:
        return reverse(
            'integrations_refine',
            kwargs = { 'location_view_id': location_view.id },
        )


class IntegrationRefineView( View ):
    """
    Convenience entry to edit-mode for a specific LocationView,
    used by the post-dispatch modal's REFINE button(s). Sets the
    session's current LocationView, flips view mode to EDIT, and
    redirects to the location view page.
    """

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


class IntegrationEnableView( HiModalView, IntegrationViewMixin, AttributeEditViewMixin ):

    def get_template_name( self ) -> str:
        return 'integrations/modals/integration_enable.html'

    def get(self, request, *args, **kwargs):

        integration_manager = IntegrationManager()
        integration_id = kwargs.get('integration_id')
        integration_data = self.get_integration_data(
            integration_id = integration_id,
        )

        # Both first-time Configure (is_enabled=False) and Review Config
        # from the pre-sync modal (is_enabled=True) land here. Review
        # mode swaps CONFIGURE→UPDATE for the action button and replaces
        # the dismiss-CANCEL with a CONTINUE that returns to pre-sync.
        is_review_mode = integration_data.integration.is_enabled
        pre_sync_url = (
            reverse(
                'integrations_pre_sync',
                kwargs = { 'integration_id': integration_data.integration_id },
            ) if is_review_mode else None
        )

        integration_manager.ensure_all_attributes_exist(
            integration_metadata = integration_data.integration_metadata,
            integration = integration_data.integration,
        )
        attr_item_context = IntegrationAttributeItemEditContext(
            integration_data = integration_data,
            update_button_label = 'UPDATE' if is_review_mode else 'CONFIGURE',
            suppress_history = True,
            show_secrets = True,
            is_review_mode = is_review_mode,
            pre_sync_url = pre_sync_url,
        )
        template_context = self.create_initial_template_context(
            attr_item_context= attr_item_context,
        )
        return self.modal_response( request, template_context )

    def post(self, request, *args, **kwargs):
        integration_manager = IntegrationManager()
        integration_id = kwargs.get('integration_id')
        integration_data = self.get_integration_data(
            integration_id = integration_id,
        )

        # Both first-time Configure (is_enabled=False) and Review Config
        # from the pre-sync modal (is_enabled=True) post here. Review
        # mode flags drive the button label and the cancel→continue
        # swap on form-error rerenders. enable_integration is
        # idempotent, so the call below is safe in both contexts.
        is_review_mode = integration_data.integration.is_enabled
        pre_sync_url = (
            reverse(
                'integrations_pre_sync',
                kwargs = { 'integration_id': integration_data.integration_id },
            ) if is_review_mode else None
        )

        attr_item_context = IntegrationAttributeItemEditContext(
            integration_data = integration_data,
            update_button_label = 'UPDATE' if is_review_mode else 'CONFIGURE',
            suppress_history = True,
            show_secrets = True,
            is_review_mode = is_review_mode,
            pre_sync_url = pre_sync_url,
        )
        response = self.post_attribute_form(
            request = request,
            attr_item_context = attr_item_context,
        )

        # Errors just dynamically populate modal content with form errors.
        if response.status_code > 299:
            return response

        integration_manager.enable_integration(
            integration_data = integration_data,
        )

        # Configure flow last step: when the integration supports sync,
        # transition directly into the pre-sync confirmation modal
        # instead of redirecting to the manage page. attr.js's response
        # handler (extended for `data.modal`) closes the Configure
        # modal and opens the new modal in its place via antinode's
        # AN.displayModal — same lifecycle antinode applies to its own
        # modal-to-modal transitions.
        synchronizer = integration_data.integration_gateway.get_synchronizer()
        if synchronizer is not None:
            is_initial_import = not Entity.objects.filter(
                integration_id = integration_data.integration_id,
            ).exists()
            sync_url = reverse(
                'integrations_sync',
                kwargs = { 'integration_id': integration_data.integration_id },
            )
            review_config_url = reverse(
                'integrations_enable',
                kwargs = { 'integration_id': integration_data.integration_id },
            )
            return self.modal_response(
                request,
                context = {
                    'integration_data': integration_data,
                    'is_initial_import': is_initial_import,
                    'sync_description': synchronizer.get_description(
                        is_initial_import = is_initial_import,
                    ),
                    'sync_url': sync_url,
                    'review_config_url': review_config_url,
                },
                template_name = 'integrations/modals/pre_sync_confirm.html',
            )

        # Integrations without a synchronizer keep the original
        # redirect-to-manage-page behavior.
        redirect_url = reverse( 'integrations_manage',
                                kwargs = { 'integration_id': integration_id } )
        return AttributeRedirectResponse( url = redirect_url )

    def validate_attributes_extra( self,
                                   attr_item_context,
                                   regular_attributes_formset,
                                   request ):
        """ Override for AttributeEditViewMixin """
        self.validate_attributes_extra_helper(
            attr_item_context,
            regular_attributes_formset,
            error_title = 'Cannot configure integration.' )
        return

    
class IntegrationDisableView( HiModalView, IntegrationViewMixin ):
    """
    Remove confirmation dialog. Classifies attached entities on GET to
    decide between a single DELETE action (no user-data entities exist) or
    DELETE SAFE / DELETE ALL variants (some entities have user-added data).
    POST dispatches to disable_integration with the chosen mode.
    """

    def get_template_name( self ) -> str:
        return 'integrations/modals/integration_disable.html'

    def get(self, request, *args, **kwargs):
        integration_data = self._get_validated_integration_data( kwargs )
        context = self._build_remove_context( integration_data )
        return self.modal_response( request, context )

    def post(self, request, *args, **kwargs):
        integration_data = self._get_validated_integration_data( kwargs )
        mode = IntegrationDisableMode.from_name_safe( request.POST.get('mode', '') )
        IntegrationManager().disable_integration(
            integration_data = integration_data,
            mode = mode,
        )
        redirect_url = reverse( 'integrations_home' )
        return self.redirect_response( request, redirect_url )

    def _get_validated_integration_data(self, kwargs):
        integration_id = kwargs.get('integration_id')
        integration_data = self.get_integration_data( integration_id = integration_id )
        if not integration_data.integration.is_enabled:
            raise BadRequest( f'{integration_data.label} is not configured' )
        return integration_data

    def _build_remove_context(self, integration_data):
        summary = EntityIntegrationOperations.summarize_for_removal(
            integration_id = integration_data.integration_id,
        )
        return {
            'integration_data': integration_data,
            'removal_summary': summary,
            'disable_mode_safe': IntegrationDisableMode.SAFE.name,
            'disable_mode_all': IntegrationDisableMode.ALL.name,
        }

    
class IntegrationPauseView( View, IntegrationViewMixin ):

    def post(self, request, *args, **kwargs):
        integration_id = kwargs.get('integration_id')
        integration_data = self.get_integration_data(
            integration_id = integration_id,
        )
        if not integration_data.integration.is_enabled:
            raise BadRequest( f'{integration_data.label} integration is not configured' )

        IntegrationManager().pause_integration( integration_data = integration_data )

        redirect_url = reverse( 'integrations_manage',
                                kwargs = { 'integration_id': integration_id } )
        return antinode.redirect_response( redirect_url )


class IntegrationResumeView( View, IntegrationViewMixin ):

    def post(self, request, *args, **kwargs):
        integration_id = kwargs.get('integration_id')
        integration_data = self.get_integration_data(
            integration_id = integration_id,
        )
        if not integration_data.integration.is_enabled:
            raise BadRequest( f'{integration_data.label} integration is not configured' )

        try:
            IntegrationManager().resume_integration( integration_data = integration_data )
        except IntegrationConnectionError as e:
            raise BadRequest(
                f'{integration_data.label} could not resume: {e}'
            )

        redirect_url = reverse( 'integrations_manage',
                                kwargs = { 'integration_id': integration_id } )
        return antinode.redirect_response( redirect_url )


class IntegrationManageView( ConfigPageView, IntegrationViewMixin, AttributeEditViewMixin ):

    def config_page_type(self) -> ConfigPageType:
        return ConfigPageType.INTEGRATIONS
    
    def get_main_template_name( self ) -> str:
        return 'integrations/pages/integration_manage.html'

    def get_main_template_context( self, request, *args, **kwargs ):
        integration_manager = IntegrationManager()
        
        integration_id = kwargs.get('integration_id')
        if integration_id:
            integration_data = self.get_integration_data(
                integration_id = integration_id,
            )
        else:
            integration_data = integration_manager.get_default_integration_data()
        
        if not integration_data.integration.is_enabled:
            raise BadRequest( f'{integration_data.label} integration is not configured' )
            
        # Get health status from the integration gateway
        health_status_provider = integration_data.integration_gateway.get_health_status_provider()
        
        attr_item_context = IntegrationAttributeItemEditContext(
            integration_data = integration_data,
            health_status = health_status_provider.health_status,
        )
        integration_data_list = self.get_integration_data_list( enabled_only = True )

        manage_view_pane = integration_data.integration_gateway.get_manage_view_pane()
        manage_template_name = manage_view_pane.get_template_name()
        template_context = manage_view_pane.get_template_context( integration_data = integration_data )

        template_context.update(
            self.create_initial_template_context(
                attr_item_context= attr_item_context,
            )
        )
        has_entities = Entity.objects.filter(
            integration_id = integration_data.integration_id,
        ).exists()

        template_context.update({
            # Extra needed on initial view only for tabbed navigation. Not
            # needed for attribute edit operations.
            #
            # Nest this context to avoid collisions with integration
            # context.  Integrations should not need to know about these.
            'core': {
                'integration_data_list': integration_data_list,
                'integration_data': integration_data,
                'manage_view_template_name': manage_template_name,
                'health_status': health_status_provider.health_status,
                'has_entities': has_entities,
            },
        })
        return template_context

    def post( self, request,*args, **kwargs ):
        integration_manager = IntegrationManager()
        
        integration_id = kwargs.get('integration_id')
        if integration_id:
            integration_data = self.get_integration_data(
                integration_id = integration_id,
            )
        else:
            integration_data = integration_manager.get_default_integration_data()

        if not integration_data.integration.is_enabled:
            raise BadRequest( f'{integration_data.label} integration is not configured' )

        # Get health status from the integration gateway
        health_status_provider = integration_data.integration_gateway.get_health_status_provider()
                
        attr_item_context = IntegrationAttributeItemEditContext(
            integration_data = integration_data,
            health_status = health_status_provider.health_status,
        )
        
        return self.post_attribute_form(
            request = request,
            attr_item_context = attr_item_context,
        )

    def validate_attributes_extra( self,
                                   attr_item_context,
                                   regular_attributes_formset,
                                   request ):
        """ Override for AttributeEditViewMixin """
        self.validate_attributes_extra_helper(
            attr_item_context,
            regular_attributes_formset,
            error_title = 'Cannot save settings.' )            
        return

    
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

        integration_data = self.get_integration_data(
            integration_id = attribute.integration.integration_id,
        )
        attr_item_context = IntegrationAttributeItemEditContext(
            integration_data = integration_data,
        )
        return self.get_history(
            request = request,
            attribute = attribute,
            attr_item_context = attr_item_context,
        )


class IntegrationAttributeRestoreInlineView( View,
                                             IntegrationViewMixin,
                                             AttributeEditViewMixin ):
    """View for restoring IntegrationAttribute values from history inline."""
    
    def get(self, request, integration_id, attribute_id, history_id, *args, **kwargs):
        """ Need to do restore in a GET since nested in main form and cannot have a form in a form """
        try:
            attribute = IntegrationAttribute.objects.select_related('integration').get(
                pk = attribute_id, integration_id = integration_id
            )
        except IntegrationAttribute.DoesNotExist:
            return page_not_found_response(request, "Attribute not found.")

        integration_data = self.get_integration_data(
            integration_id = attribute.integration.integration_id,
        )
            
        attr_item_context = IntegrationAttributeItemEditContext(
            integration_data = integration_data,
        )
        return self.post_restore(
            request = request,
            attribute = attribute,
            history_id = history_id,
            attr_item_context = attr_item_context,
        )
