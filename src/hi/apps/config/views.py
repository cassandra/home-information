from django.urls import reverse

import hi.apps.common.antinode as antinode
from hi.apps.common.utils import is_ajax
from hi.enums import ViewMode, ViewType
from hi.hi_grid_view import HiGridView
from hi.integrations.core.views import IntegrationViewMixin


class ConfigHomePaneView( HiGridView, IntegrationViewMixin ):

    def get(self, request, *args, **kwargs):

        view_type_changed = bool( request.view_parameters.view_type != ViewType.CONFIGURATION )
        request.view_parameters.view_type = ViewType.CONFIGURATION
        request.view_parameters.view_mode = ViewMode.MONITOR
        request.view_parameters.to_session( request )

        if view_type_changed and is_ajax( request ):
            sync_url = reverse('config_home_pane')
            return antinode.redirect_response( url = sync_url )

        context = {
        }
        context.update( self.get_integration_config_tab_context() )
        return self.hi_grid_response( 
            request = request,
            context = context,
            main_template_name = 'config/panes/home.html',
            push_url_name = 'config_home_pane',
        )
