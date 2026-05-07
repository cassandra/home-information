import logging

from django.core.exceptions import BadRequest
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import View

from hi.apps.common import antinode
from hi.apps.common.utils import str_to_bool
from hi.enums import ViewMode, ViewType
from hi.exceptions import ForceRedirectException
from hi.hi_async_view import HiModalView
from hi.views import page_not_found_response

from hi.apps.attribute.response_helpers import AttributeRedirectResponse
from hi.apps.attribute.view_mixins import AttributeEditViewMixin
from hi.apps.config.enums import ConfigPageType
from hi.apps.config.views import ConfigPageView
from hi.apps.entity.entity_placement import EntityPlacementService
from hi.apps.entity.models import Entity
from hi.apps.location.models import LocationView

from .placement_request import PlacementFormParser, PlacementUrlParams
from .entity_operations import EntityIntegrationOperations
from .enums import IntegrationDisableMode
from .exceptions import IntegrationConnectionError
from .integration_attribute_edit_context import IntegrationAttributeItemEditContext
from .integration_manager import IntegrationManager
from .models import IntegrationAttribute
from .sync_check import IntegrationSyncCheck
from .view_mixins import IntegrationPlacementViewMixin, IntegrationViewMixin

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

        # Refresh path: surface the same SAFE / ALL policy choice the
        # disable modal does when the integration has any user-data
        # entities. The summary is the integration's full footprint
        # (not a per-sync prediction): the operator's choice
        # expresses the policy applied at sync execution if any
        # drops carry user data, which is the same question the
        # disable modal asks. Skipped on the first-time import path
        # since no entities exist yet.
        removal_summary = None
        if not is_initial_import:
            removal_summary = EntityIntegrationOperations.summarize_for_removal(
                integration_id = integration_data.integration_id,
            )

        context = {
            'integration_data': integration_data,
            'is_initial_import': is_initial_import,
            'sync_description': synchronizer.get_description(
                is_initial_import = is_initial_import,
            ),
            'sync_url': sync_url,
            'review_config_url': review_config_url,
            'removal_summary': removal_summary,
        }
        return self.modal_response( request, context )


class IntegrationSyncView( HiModalView, IntegrationViewMixin ):
    """
    Framework sync execution view. Invokes the integration's
    synchronizer and always renders the sync result modal — the
    operator's single end-of-sync surface. When the sync produced
    new entities to place, the result modal exposes a primary
    'Place N new items' CTA that navigates (via antinode modal-to-
    modal) to the placement GET endpoint where the operator picks
    targets. When there are no new entities (refresh-with-updates,
    refresh-with-removes, errors, or nothing-new), the result modal
    shows just a dismissal action.

    This shape was chosen so updates and removes are never silently
    swallowed by an automatic transition to the placement: the
    operator always sees what changed, and only opts into placement
    when there's actually something to place.
    """

    def get_template_name( self ) -> str:
        return 'integrations/modals/sync_result.html'

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
        # integration before this sync ran"; threaded through to the
        # placement GET URL so a downstream Place-items click
        # carries the same operator intent.
        is_initial_import = not Entity.objects.filter(
            integration_id = integration_data.integration_id,
        ).exists()

        # Operator's per-Refresh policy for items that would be
        # dropped. True ("Refresh and Retain") preserves user-data
        # entities by detaching them; False ("Refresh and Remove")
        # hard-deletes everything dropped. Defaults to True — the
        # safe value when the choice was not surfaced (no user-data
        # entities) or the field was absent for any reason.
        preserve_user_data = str_to_bool(
            request.POST.get( 'preserve_user_data', 'true' ),
        )

        sync_result = synchronizer.sync(
            is_initial_import = is_initial_import,
            preserve_user_data = preserve_user_data,
        )

        # Scope the placement to just the entities this sync created.
        # Without scoping, the placement's GET endpoint queries every
        # unplaced entity for the integration, including pre-existing
        # ones from prior incomplete placements.
        new_entity_ids = (
            sync_result.placement_input.all_entity_ids()
            if sync_result.placement_input is not None else []
        )
        placement_url = PlacementUrlParams(
            is_initial_import = is_initial_import,
            entity_ids = new_entity_ids,
        ).append_to_url( reverse(
            'integrations_placement',
            kwargs = { 'integration_id': integration_data.integration_id },
        ) )

        return self.modal_response(
            request,
            context = {
                'sync_result': sync_result,
                'integration_data': integration_data,
                'is_initial_import': is_initial_import,
                'placement_url': placement_url,
            },
            template_name = 'integrations/modals/sync_result.html',
        )


class IntegrationPlacementView( HiModalView, IntegrationViewMixin,
                                IntegrationPlacementViewMixin ):
    """Placement modal — single CBV handling both the GET (render)
    and POST (form submission) paths on one URL.

    GET queries currently-unplaced entities for the integration
    (optionally scoped by ``entity_ids`` URL param), runs them
    through the synchronizer's ``group_entities_for_placement``,
    and renders the placement modal. Empty result falls back to
    a brief acknowledgement modal so the operator isn't dropped
    onto an empty placement.

    POST processes the placement form. The form has two submit
    buttons — APPLY and NOT NOW — sharing ``name="action"`` with
    distinct values; this view branches on the value to render
    either the post-dispatch summary modal (apply path) or the
    dismiss-confirm modal (not-now path).
    """

    DISMISS_ACTION_VALUE = 'dismiss'

    def get_template_name( self ) -> str:
        return 'integrations/modals/placement.html'

    def get( self, request, *args, **kwargs ):
        integration_id = kwargs.get('integration_id')
        integration_data = self.get_integration_data(
            integration_id = integration_id,
        )
        synchronizer = integration_data.integration_gateway.get_synchronizer()
        if synchronizer is None:
            return page_not_found_response( request )

        url_params = PlacementUrlParams.from_data( request.GET )
        is_initial_import = url_params.is_initial_import
        entity_id_filter = set( url_params.entity_ids ) if url_params.entity_ids else None

        entities = EntityPlacementService.query_unplaced_entities(
            integration_id = integration_data.integration_id,
        )
        # When the caller scoped the URL to specific entity ids
        # (sync-result CTA), narrow the unplaced set to those.
        # Without scoping, the placement operates on the full
        # unplaced set for the integration (recovery flow).
        if entity_id_filter is not None:
            entities = [ e for e in entities if e.id in entity_id_filter ]

        placement_input = synchronizer.group_entities_for_placement(
            entities = entities,
        )
        if placement_input.is_empty():
            return self._render_empty(
                request = request,
                integration_data = integration_data,
                synchronizer = synchronizer,
                is_initial_import = is_initial_import,
            )
        return self.render_placement(
            request = request,
            integration_data = integration_data,
            placement_input = placement_input,
            is_initial_import = is_initial_import,
            entity_id_filter = entity_id_filter,
        )

    def post( self, request, *args, **kwargs ):
        integration_id = kwargs.get('integration_id')
        integration_data = self.get_integration_data(
            integration_id = integration_id,
        )
        url_params = PlacementUrlParams.from_data( request.POST )
        is_initial_import = url_params.is_initial_import

        if request.POST.get('action') == self.DISMISS_ACTION_VALUE:
            entity_ids = self._extract_placement_entity_ids( request )
            return self.render_dismiss_confirm(
                request = request,
                integration_data = integration_data,
                entity_ids = entity_ids,
                is_initial_import = is_initial_import,
            )

        decisions = PlacementFormParser.parse(
            request = request, integration_data = integration_data,
        )
        outcome = EntityPlacementService.apply_decisions( decisions = decisions )
        return self.render_post_placement(
            request = request,
            integration_data = integration_data,
            outcome = outcome,
            is_initial_import = is_initial_import,
        )

    @staticmethod
    def _extract_placement_entity_ids( request ):
        """Pull the entity ids the placement form just posted.
        The placement renders ``all_group_<i>_entity_ids`` per
        group plus a single ``ungrouped_entity_ids`` field — both
        carry the entity ids regardless of whether the operator
        opened any drill-down."""
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
                       synchronizer, is_initial_import : bool ):
        """No-unplaced-items acknowledgement: render the result
        modal with the integration's icon + a brief 'no items'
        info note rather than an empty placement. Counts stay
        zero so the modal lead reads 'Nothing new.'"""
        from hi.integrations.sync_result import IntegrationSyncResult
        sync_result = IntegrationSyncResult(
            title = synchronizer.get_result_title(
                is_initial_import = is_initial_import,
            ),
            info_list = [ 'No items left to place.' ],
        )
        return self.modal_response(
            request,
            context = {
                'sync_result': sync_result,
                'integration_data': integration_data,
                'is_initial_import': is_initial_import,
            },
            template_name = 'integrations/modals/sync_result.html',
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

        # Issue #283 sync-check state.
        #   * sync_check_result drives the banner and the Refresh
        #     button emphasis on the active integration's manage
        #     page.
        #   * sidebar_items pairs each integration with its current
        #     sync-check result so the sidebar template iterates one
        #     pre-resolved list instead of looking up per-integration
        #     state mid-render.
        sync_check_result = IntegrationSyncCheck.get_state(
            integration_data.integration_id,
        )
        sidebar_items = [
            {
                'integration_data': data,
                'sync_check_result': IntegrationSyncCheck.get_state(
                    data.integration_id,
                ),
            }
            for data in integration_data_list
        ]

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
                'sync_check_result': sync_check_result,
                'sidebar_items': sidebar_items,
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
