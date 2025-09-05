import logging

from django.core.exceptions import BadRequest
from django.urls import reverse
from django.views.generic import View

from hi.exceptions import ForceRedirectException
from hi.hi_async_view import HiModalView
from hi.views import page_not_found_response

from hi.apps.attribute.views import BaseAttributeHistoryView, BaseAttributeRestoreView
from hi.apps.attribute.view_mixins import AttributeEditViewMixin
from hi.apps.config.enums import ConfigPageType
from hi.apps.config.views import ConfigPageView

from .forms import IntegrationAttributeRegularFormSet
from .integration_attribute_edit_context import IntegrationAttributeItemEditContext
from .integration_manager import IntegrationManager
from .models import IntegrationAttribute

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

        integration_attribute_formset = IntegrationAttributeRegularFormSet(
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
        
        integration_attribute_formset = IntegrationAttributeRegularFormSet(
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

        redirect_url = reverse( 'integrations_manage',
                                kwargs = { 'integration_id': integration_id } )
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

    
class IntegrationManageView( ConfigPageView, AttributeEditViewMixin ):

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
            
        attr_item_context = IntegrationAttributeItemEditContext(
            integration_data = integration_data,
        )
        integration_data_list = integration_manager.get_integration_data_list( enabled_only = True )

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
            },
        })
        return template_context

    def post( self, request,*args, **kwargs ):
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

        attr_item_context = IntegrationAttributeItemEditContext(
            integration_data = integration_data,
        )
        return self.post_attribute_form(
            request = request,
            attr_item_context = attr_item_context,
        )
    
        
class IntegrationAttributeHistoryInlineView( View, AttributeEditViewMixin ):

    def get(self, request, integration_id, attribute_id, *args, **kwargs):
        # Validate that the attribute belongs to this integration for security
        try:
            attribute = IntegrationAttribute.objects.select_related('integration').get(
                pk = attribute_id, integration_id = integration_id )
        except IntegrationAttribute.DoesNotExist:
            return page_not_found_response(request, "Attribute not found.")

        integration_manager = IntegrationManager()
        integration_data = integration_manager.get_integration_data(
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


class IntegrationAttributeRestoreInlineView( View, AttributeEditViewMixin ):
    """View for restoring IntegrationAttribute values from history inline."""
    
    def get(self, request, integration_id, attribute_id, history_id, *args, **kwargs):
        """ Need to do restore in a GET since nested in main form and cannot have a form in a form """
        try:
            attribute = IntegrationAttribute.objects.select_related('integration').get(
                pk = attribute_id, integration_id = integration_id
            )
        except IntegrationAttribute.DoesNotExist:
            return page_not_found_response(request, "Attribute not found.")

        integration_manager = IntegrationManager()
        integration_data = integration_manager.get_integration_data(
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






    


        

class IntegrationManageView_ORIGINAL( ConfigPageView ):

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
                'manage_view_info_template_name': template_name,
            },
        })
        return template_context

    
class IntegrationAttributeHistoryView(BaseAttributeHistoryView):
    """View for displaying IntegrationAttribute history in a modal."""
    
    def get_attribute_model_class(self):
        return IntegrationAttribute
    
    def get_history_url_name(self):
        return 'integration_attribute_history'
    
    def get_restore_url_name(self):
        return 'integration_attribute_restore'


class IntegrationAttributeRestoreView(BaseAttributeRestoreView):
    """View for restoring IntegrationAttribute values from history."""
    
    def get_attribute_model_class(self):
        return IntegrationAttribute
