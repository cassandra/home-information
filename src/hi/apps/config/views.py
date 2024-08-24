from django.shortcuts import render
from django.views.generic import View

from hi.integrations.core.views import IntegrationViewMixin


class ConfigHomePaneView( View, IntegrationViewMixin ):

    def get(self, request, *args, **kwargs):

        context = {
        }
        context.update( self.get_integration_config_tab_context() )
        return render( request, 'config/panes/home.html', context )
