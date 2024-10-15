from django.urls import reverse

from hi.apps.common.utils import is_ajax

from hi.integrations.core.views import IntegrationViewMixin

from hi.enums import ViewMode, ViewType
from hi.exceptions import ForceRedirectException
from hi.hi_grid_view import HiGridView


class ConfigHomePaneView( HiGridView, IntegrationViewMixin ):

    def get_main_template_name( self ) -> str:
        return 'config/panes/home.html'

    def get_template_context( self, request, *args, **kwargs ):

        view_type_changed = bool( request.view_parameters.view_type != ViewType.CONFIGURATION )
        request.view_parameters.view_type = ViewType.CONFIGURATION
        request.view_parameters.view_mode = ViewMode.MONITOR
        request.view_parameters.to_session( request )

        if view_type_changed and is_ajax( request ):
            redirect_url = reverse('config_home_pane')
            raise ForceRedirectException( url = redirect_url )

        return self.get_integration_config_tab_context()
