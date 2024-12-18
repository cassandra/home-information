import logging

from django.core.exceptions import BadRequest
from django.urls import reverse

from hi.apps.config.enums import ConfigPageType
from hi.apps.config.views import ConfigPageView

from hi.exceptions import ForceRedirectException
from hi.hi_async_view import HiModalView

from .forms import IntegrationAttributeFormSet
from .integration_manager import IntegrationManager

logger = logging.getLogger(__name__)


class IntegrationHomeView( ConfigPageView ):

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

    
class IntegrationSelectView( HiModalView ):

    def get_template_name( self ) -> str:
        return 'integrations/modals/integrations_select.html'

    def get( self, request, *args, **kwargs ):
        context = {
            'integration_data_list': IntegrationManager().get_integration_data_list(),
        }
        return self.modal_response( request, context )


class IntegrationEnableView( HiModalView ):

    def get_template_name( self ) -> str:
        return 'integrations/modals/integration_enable.html'

    def get(self, request, *args, **kwargs):
        integration_manager = IntegrationManager()
        integration_id = kwargs.get('integration_id')
        integration_data = integration_manager.get_integration_data(
            integration_id = integration_id,
        )
        if integration_data.integration.is_enabled:
            raise BadRequest( f'{integration_data.label} is already enabled' )

        integration_manager._ensure_all_attributes_exist(
            integration_metadata = integration_data.integration_metadata,
            integration = integration_data.integration,
        )

        integration_attribute_formset = IntegrationAttributeFormSet(
            instance = integration_data.integration,
            prefix = f'integration-{integration_id}',
            form_kwargs = {
                'show_as_editable': True,
            },
        )
        context = {
            'integration_data': integration_data,
            'integration_attribute_formset': integration_attribute_formset,
        }
        return self.modal_response( request, context )

    def post(self, request, *args, **kwargs):
        integration_manager = IntegrationManager()
        integration_id = kwargs.get('integration_id')
        integration_data = integration_manager.get_integration_data(
            integration_id = integration_id,
        )
        if integration_data.integration.is_enabled:
            raise BadRequest( f'{integration_data.label} is already enabled' )
        
        integration_attribute_formset = IntegrationAttributeFormSet(
            request.POST,
            request.FILES,
            instance = integration_data.integration,
            prefix = f'integration-{integration_id}',
        )
        if not integration_attribute_formset.is_valid():
            context = {
                'integration_data': integration_data,
                'integration_attribute_formset': integration_attribute_formset,
            }
            return self.modal_response( request, context, status_code = 400 )

        integration_manager.enable_integration(
            integration_data = integration_data,
            integration_attribute_formset = integration_attribute_formset,
        )
        redirect_url = reverse( 'integrations_home' )
        return self.redirect_response( request, redirect_url )

    
class IntegrationDisableView( HiModalView ):

    def get_template_name( self ) -> str:
        return 'integrations/modals/integration_disable.html'

    def get(self, request, *args, **kwargs):
        integration_id = kwargs.get('integration_id')
        integration_data = IntegrationManager().get_integration_data(
            integration_id = integration_id,
        )
        if not integration_data.integration.is_enabled:
            raise BadRequest( f'{integration_data.label} is already disabled' )

        context = {
            'integration_data': integration_data,
        }
        return self.modal_response( request, context )
    
    def post(self, request, *args, **kwargs):
        integration_manager = IntegrationManager()
        integration_id = kwargs.get('integration_id')
        integration_data = integration_manager.get_integration_data(
            integration_id = integration_id,
        )
        if not integration_data.integration.is_enabled:
            raise BadRequest( f'{integration_data.label} is already disabled' )

        integration_manager.disable_integration(
            integration_data = integration_data,
        )
        redirect_url = reverse( 'integrations_home' )
        return self.redirect_response( request, redirect_url )
        

class IntegrationManageView( ConfigPageView ):

    def config_page_type(self) -> ConfigPageType:
        return ConfigPageType.INTEGRATIONS
    
    def get_main_template_name( self ) -> str:
        return 'integrations/pages/integration_manage.html'

    def get_main_template_context( self, request, *args, **kwargs ):
        integration_manager = IntegrationManager()
        
        integration_id = kwargs.get('integration_id')
        if integration_id:
            integration_data = integration_manager.get_integration_data(
                integration_id = integration_id,
            )
        else:
            integration_data = integration_manager.get_default_integration_data()

        if not integration_data.integration.is_enabled:
            raise BadRequest( f'{integration_data.label} integration is not enabled' )
            
        integration_data_list = integration_manager.get_integration_data_list( enabled_only = True )

        manage_view_pane = integration_data.integration_gateway.get_manage_view_pane()
        template_name = manage_view_pane.get_template_name()
        template_context = manage_view_pane.get_template_context( integration_data = integration_data )
        
        template_context.update({
            # Nest this context to avoid collisions with integration
            # context.  Integrations should not need to know about these.
            'core': {
                'integration_data_list': integration_data_list,
                'integration_data': integration_data,
                'manage_view_pane_template_name': template_name,
            },
        })
        return template_context
    
