import logging

from django.core.exceptions import BadRequest
from django.urls import reverse
from django.views.generic import View

from hi.apps.common import antinode
from hi.apps.common.utils import str_to_bool
from hi.exceptions import ForceRedirectException
from hi.hi_async_view import HiModalView
from hi.views import page_not_found_response

from hi.apps.attribute.response_helpers import AttributeRedirectResponse
from hi.apps.attribute.view_mixins import AttributeEditViewMixin
from hi.apps.config.enums import ConfigPageType
from hi.apps.config.views import ConfigPageView
from hi.apps.entity.models import Entity
from hi.apps.sense.sensor_response_manager import SensorResponseManager

from hi.integrations.enums import IntegrationCapability, IntegrationDisableMode
from hi.integrations.exceptions import IntegrationConnectionError
from hi.integrations.integration_manager import IntegrationManager
from hi.integrations.integration_metadata_cache import IntegrationMetadataCache

from hi.integrations.entity_operations import EntityIntegrationOperations
from hi.integrations.integration_attribute_edit_context import IntegrationAttributeItemEditContext
from .sync_check import IntegrationSyncCheck
from hi.integrations.view_mixins import IntegrationViewMixin
from hi.integrations.connector.view_mixins import ConnectorViewMixin
from hi.integrations.views import CapabilityConfigureView

logger = logging.getLogger(__name__)


class IntegrationHomeView( ConfigPageView, IntegrationViewMixin ):

    def config_page_type(self) -> ConfigPageType:
        return ConfigPageType.INTEGRATIONS_CONNECT

    def get_main_template_name( self ) -> str:
        return 'integrations/connector/pages/no_integrations.html'

    def get_main_template_context( self, request, *args, **kwargs ):

        integration_data = IntegrationManager().get_default_integration_data(
            capabilities = frozenset({ IntegrationCapability.CONNECT }),
        )
        if not integration_data:
            return dict()

        redirect_url = reverse( 'integrations_connect_manage',
                                kwargs = { 'integration_id': integration_data.integration_id })
        raise ForceRedirectException( redirect_url )


class IntegrationSelectView( HiModalView, IntegrationViewMixin ):

    def get_template_name( self ) -> str:
        return 'integrations/connector/modals/integrations_select.html'

    def get( self, request, *args, **kwargs ):
        context = {
            'integration_data_list': self.get_integration_data_list(
                capabilities = frozenset({ IntegrationCapability.CONNECT }),
            ),
        }
        return self.modal_response( request, context )


class IntegrationHealthStatusView( HiModalView, IntegrationViewMixin ):

    def get_template_name( self ) -> str:
        return 'system/modals/health_status.html'

    def get( self, request, *args, **kwargs ):
        integration_data = self.get_integration_data( request, *args, **kwargs )
        health_status_provider = integration_data.integration_gateway.get_connector().get_health_status_provider()
        context = {
            'health_status_provider': health_status_provider,
        }
        return self.modal_response( request, context )


class IntegrationPreSyncView( HiModalView, IntegrationViewMixin ):
    """
    Pre-sync confirmation modal for the manage-page UPDATE button.
    Surfaces the synchronizer's description and offers Sync / Not now
    actions. Not used in the first-time sync enable flow.

    On the update-check path the modal additionally surfaces the same
    SAFE / ALL policy choice the disable modal does when the integration
    has any user-data entities -- the operator's choice expresses the
    policy applied at sync execution if any drops carry user data.

    404s when the integration does not provide a connector (sync is
    opt-in capability -- not every integration supports it).
    """

    def get_template_name( self ) -> str:
        return 'integrations/connector/modals/pre_sync_confirm.html'

    def get( self, request, *args, **kwargs ):
        integration_data = self.get_integration_data( request, *args, **kwargs )
        connector = integration_data.integration_gateway.get_connector()
        if connector is None:
            return page_not_found_response( request )

        is_initial_connect = not Entity.objects.filter(
            integration_id = integration_data.integration_id,
        ).exists()
        sync_url = reverse(
            'integrations_connect_sync',
            kwargs = { 'integration_id': integration_data.integration_id },
        )

        removal_summary = None
        if not is_initial_connect:
            removal_summary = EntityIntegrationOperations.summarize_for_removal(
                integration_id = integration_data.integration_id,
            )

        context = {
            'integration_data': integration_data,
            'is_initial_connect': is_initial_connect,
            'sync_description': connector.get_sync_description(
                is_initial_connect = is_initial_connect,
            ),
            'sync_url': sync_url,
            'removal_summary': removal_summary,
        }
        return self.modal_response( request, context )


class IntegrationSyncView( HiModalView, IntegrationViewMixin, ConnectorViewMixin ):
    """
    Framework sync execution view. Invokes the integration's connector
    and always renders the sync result modal -- the operator's single
    end-of-sync surface. When the sync produced new entities to place,
    the result modal exposes a primary 'Place N new items' CTA that
    navigates to the placement GET endpoint where the operator picks
    targets. When there are no new entities (refresh-with-updates,
    refresh-with-removes, errors, or nothing-new), the result modal
    shows just a dismissal action.

    This shape was chosen so updates and removes are never silently
    swallowed by an automatic transition to placement: the operator
    always sees what changed, and only opts into placement when
    there's actually something to place.
    """

    def get_template_name( self ) -> str:
        return 'integrations/connector/modals/sync_result.html'

    def post( self, request, *args, **kwargs ):
        integration_data = self.get_integration_data( request, *args, **kwargs )
        # Operator's per-Refresh policy for items that would be
        # dropped. True ("Refresh and Retain") preserves user-data
        # entities by detaching them; False ("Refresh and Remove")
        # hard-deletes everything dropped. Defaults to True -- the
        # safe value when the choice was not surfaced (no user-data
        # entities) or the field was absent for any reason.
        preserve_user_data = str_to_bool(
            request.POST.get( 'preserve_user_data', 'true' ),
        )
        return self.render_sync_result(
            request = request,
            integration_data = integration_data,
            preserve_user_data = preserve_user_data,
        )


class ConnectorConfigureView( CapabilityConfigureView, ConnectorViewMixin ):

    capability    = IntegrationCapability.CONNECT
    button_label  = 'CONNECT'
    template_name = 'integrations/connector/modals/integration_enable.html'
    error_title   = 'Cannot configure integration.'

    def get_capability_gateway( self, integration_data ):
        return integration_data.integration_gateway.get_connector()

    def handle_post_success(self, request, integration_data):
        IntegrationManager().enable_integration(
            integration_data = integration_data,
        )

        # Connect-side managers gate client (re)build on
        # integration.is_enabled, so the notify MUST fire after
        # enable_integration -- otherwise the manager reloads with
        # is_enabled=False, nulls its client, and the immediately-
        # following sync sees no client. Calling unconditionally also
        # covers the re-Configure path (already enabled), where
        # enable_integration early-returns without nudging.
        try:
            integration_data.integration_gateway.notify_settings_changed()
        except Exception as e:
            logger.warning(
                f'Synchronous notify_settings_changed failed for '
                f'{integration_data.integration_id}: {e}'
            )

        # When the integration supports sync, run it inline and render
        # the sync-result modal directly so CONNECT is one click.
        # Connector-less integrations redirect to the manage page.
        connector = integration_data.integration_gateway.get_connector()
        if connector is not None:
            return self.render_sync_result(
                request = request,
                integration_data = integration_data,
            )

        redirect_url = reverse(
            'integrations_connect_manage',
            kwargs = { 'integration_id': integration_data.integration_id },
        )
        return AttributeRedirectResponse( url = redirect_url )


class IntegrationDisableView( HiModalView, IntegrationViewMixin ):
    """
    Remove confirmation dialog. Classifies attached entities on GET to
    decide between a single DELETE action (no user-data entities exist)
    or DELETE SAFE / DELETE ALL variants (some entities have user-added
    data). POST dispatches to disable_integration with the chosen mode.
    """

    def get_template_name( self ) -> str:
        return 'integrations/connector/modals/integration_disable.html'

    def get(self, request, *args, **kwargs):
        integration_data = self._get_validated_integration_data( request, *args, **kwargs )
        context = self._build_remove_context( integration_data )
        return self.modal_response( request, context )

    def post(self, request, *args, **kwargs):
        integration_data = self._get_validated_integration_data( request, *args, **kwargs )
        mode = IntegrationDisableMode.from_name_safe( request.POST.get('mode', '') )
        try:
            IntegrationManager().disable_integration(
                integration_data = integration_data,
                mode = mode,
            )
        finally:
            # Disable removes EntityStates whose ``integration_key``s
            # may still be cached; invalidate so subsequent reads
            # don't return stale entries that reference deleted
            # rows. Symmetric with the post-sync invalidation.
            IntegrationMetadataCache().invalidate()
            SensorResponseManager().invalidate_local_sensor_cache()
        redirect_url = reverse( 'integrations_connect_home' )
        return self.redirect_response( request, redirect_url )

    def _get_validated_integration_data(self, request, *args, **kwargs):
        integration_data = self.get_integration_data( request, *args, **kwargs )
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
        integration_data = self.get_integration_data( request, *args, **kwargs )
        if not integration_data.integration.is_enabled:
            raise BadRequest( f'{integration_data.label} integration is not configured' )

        IntegrationManager().pause_integration( integration_data = integration_data )

        redirect_url = reverse(
            'integrations_connect_manage',
            kwargs = { 'integration_id': integration_data.integration_id },
        )
        return antinode.redirect_response( redirect_url )


class IntegrationResumeView( View, IntegrationViewMixin ):

    def post(self, request, *args, **kwargs):
        integration_data = self.get_integration_data( request, *args, **kwargs )
        if not integration_data.integration.is_enabled:
            raise BadRequest( f'{integration_data.label} integration is not configured' )

        try:
            IntegrationManager().resume_integration( integration_data = integration_data )
        except IntegrationConnectionError as e:
            raise BadRequest(
                f'{integration_data.label} could not resume: {e}'
            )

        redirect_url = reverse(
            'integrations_connect_manage',
            kwargs = { 'integration_id': integration_data.integration_id },
        )
        return antinode.redirect_response( redirect_url )


class ConnectorManageView( ConfigPageView, IntegrationViewMixin, AttributeEditViewMixin ):

    def config_page_type(self) -> ConfigPageType:
        return ConfigPageType.INTEGRATIONS_CONNECT

    def get_main_template_name( self ) -> str:
        return 'integrations/connector/pages/integration_manage.html'

    def get_main_template_context( self, request, *args, **kwargs ):
        integration_manager = IntegrationManager()

        integration_id = kwargs.get('integration_id')
        if integration_id:
            integration_data = self.get_integration_data( request, *args, **kwargs )
        else:
            integration_data = integration_manager.get_default_integration_data(
                capabilities = frozenset({ IntegrationCapability.CONNECT }),
            )

        if not integration_data.integration.is_enabled:
            raise BadRequest( f'{integration_data.label} integration is not configured' )

        health_status_provider = integration_data.integration_gateway.get_connector().get_health_status_provider()

        attr_item_context = IntegrationAttributeItemEditContext(
            integration_data = integration_data,
            capability_gateway = integration_data.integration_gateway.get_connector(),
            health_status = health_status_provider.health_status,
        )
        integration_data_list = self.get_integration_data_list(
            enabled_only = True,
            capabilities = frozenset({ IntegrationCapability.CONNECT }),
        )

        template_context = self.create_initial_template_context(
            attr_item_context = attr_item_context,
        )
        has_entities = Entity.objects.filter(
            integration_id = integration_data.integration_id,
        ).exists()

        # Sync-check state for the manage page:
        #   * sync_check_result drives the banner and the Refresh
        #     button emphasis on the active integration's manage page.
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
            integration_data = self.get_integration_data( request, *args, **kwargs )
        else:
            integration_data = integration_manager.get_default_integration_data(
                capabilities = frozenset({ IntegrationCapability.CONNECT }),
            )

        if not integration_data.integration.is_enabled:
            raise BadRequest( f'{integration_data.label} integration is not configured' )

        health_status_provider = integration_data.integration_gateway.get_connector().get_health_status_provider()

        attr_item_context = IntegrationAttributeItemEditContext(
            integration_data = integration_data,
            capability_gateway = integration_data.integration_gateway.get_connector(),
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
        self.validate_attributes_extra_helper(
            attr_item_context,
            regular_attributes_formset,
            error_title = 'Cannot save settings.' )
        return
