from django.shortcuts import render
from django.views.generic import View

from .enums import IntegrationType
from .integration_factory import IntegrationFactory


class IntegrationViewMixin:

    def get_integration_config_tab_context(self):
        return {
            'integration_list': IntegrationFactory().get_all_integrations(),
        }

    
class IntegrationConfigTabView( View, IntegrationViewMixin ):

    def post(self, request, *args, **kwargs):

        error_message = None
        try:        
            integration_type = IntegrationType.from_name( kwargs.get('name') )
            action = kwargs.get('action')

            integration_gateway = IntegrationFactory().get_integration_gateway(
                integration_type = integration_type,
            )
        
            if action == 'enable':
                return integration_gateway.enable( request = request )
            elif action == 'disable':
                return integration_gateway.disable( request = request )

            error_message = f'Unknown integration config action "{action}".'
        except Exception as e:
            error_message = str(e)
            
        context = {
            'error_message': error_message,
        }
        context.update( self.get_integration_config_tab_context() )
        return render( request, 'core/panes/config_tab.html', context )

    
class IntegrationManageView( View, IntegrationViewMixin ):

    def get(self, request, *args, **kwargs):

        error_message = None
        try:        
            integration_type = IntegrationType.from_name( kwargs.get('name') )
            integration_gateway = IntegrationFactory().get_integration_gateway(
                integration_type = integration_type,
            )
            return integration_gateway.manage( request = request, *args, **kwargs )
        except Exception as e:
            error_message = str(e)
            
        context = {
            'error_message': error_message,
        }
        context.update( self.get_integration_config_tab_context() )
        return render( request, 'core/panes/config_tab.html', context )
    
    def post(self, request, *args, **kwargs):
        return self.get( request, *args, **kwargs)
