from hi.hi_grid_view import HiGridView
from hi.integrations.core.views import IntegrationViewMixin


class ConfigHomePaneView( HiGridView, IntegrationViewMixin ):

    def get(self, request, *args, **kwargs):

        context = {
        }
        context.update( self.get_integration_config_tab_context() )
        return self.hi_grid_response( 
            request = request,
            context = context,
            main_template_name = 'config/panes/home.html',
            push_url_name = 'config_home_pane',
        )
