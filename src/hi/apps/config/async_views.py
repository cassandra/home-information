from hi.integrations.core.views import IntegrationViewMixin

from hi.constants import DIVID
from hi.hi_async_view import HiAsyncView


class ConfigTabPaneView( HiAsyncView, IntegrationViewMixin ):

    def get_target_div_id( self ) -> str:
        return DIVID['INTEGRATION_TAB']

    def get_template_name( self ) -> str:
        return 'core/panes/integration_config_tab.html'

    def get_template_context( self, request, *args, **kwargs ):
        return self.get_integration_config_tab_context()
