import logging

from django.core.exceptions import BadRequest
from django.urls import reverse
from django.views.generic import View

from hi.apps.common import antinode
from hi.exceptions import ForceRedirectException
from hi.hi_async_view import HiModalView
from hi.views import page_not_found_response

from hi.apps.attribute.response_helpers import AttributeRedirectResponse
from hi.apps.attribute.view_mixins import AttributeEditViewMixin
from hi.apps.config.enums import ConfigPageType
from hi.apps.config.views import ConfigPageView

from .entity_operations import EntityIntegrationOperations
from .enums import IntegrationDisableMode
from .integration_attribute_edit_context import IntegrationAttributeItemEditContext
from .integration_manager import IntegrationManager
from .models import IntegrationAttribute
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


class IntegrationEnableView( HiModalView, IntegrationViewMixin, AttributeEditViewMixin ):

    def get_template_name( self ) -> str:
        return 'integrations/modals/integration_enable.html'

    def get(self, request, *args, **kwargs):

        integration_manager = IntegrationManager()
        integration_id = kwargs.get('integration_id')
        integration_data = self.get_integration_data(
            integration_id = integration_id,
        )
            
        if integration_data.integration.is_enabled:
            raise BadRequest( f'{integration_data.label} is already configured' )

        integration_manager.ensure_all_attributes_exist(
            integration_metadata = integration_data.integration_metadata,
            integration = integration_data.integration,
        )
        attr_item_context = IntegrationAttributeItemEditContext(
            integration_data = integration_data,
            update_button_label = 'CONFIGURE',
            suppress_history = True,
            show_secrets = True,

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
        if integration_data.integration.is_enabled:
            raise BadRequest( f'{integration_data.label} is already configured' )

        attr_item_context = IntegrationAttributeItemEditContext(
            integration_data = integration_data,
            update_button_label = 'CONFIGURE',
            suppress_history = True,
            show_secrets = True,
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

        IntegrationManager().resume_integration( integration_data = integration_data )

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
