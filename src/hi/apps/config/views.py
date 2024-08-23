from django.shortcuts import render
from django.views.generic import View

from hi.integrations.core.enums import IntegrationType
from hi.integrations.core.integration_manager import IntegrationManager


class ConfigHomePaneView( View ):

    def get(self, request, *args, **kwargs):

        context = {
            'integration_list': IntegrationManager().get_all_integrations(),
        }
        return render( request, 'config/panes/home.html', context )

    
class ConfigIntegrationView( View ):

    def post(self, request, *args, **kwargs):

        action = kwargs.get('action')
        integration_type = IntegrationType.from_name( kwargs.get('name') )

        integration =  IntegrationManager().get_integration( integration_type = integration_type )
        
        
        if action == 'enable':
            zzz
        elif action == 'disable':
            zzz
        elif action == 'sync':
            zzz
        else:
            raise ValueError( f'Unknown integration action "{action}". )
        
        
        context = {
        }
        return render( request, 'config/panes/home.html', context )
    
