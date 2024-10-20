import hi.apps.common.antinode as antinode
from hi.apps.common.utils import is_ajax

from hi.enums import ViewMode, ViewType
from hi.hi_grid_view import HiGridView

from .enums import ConfigPageType


class ConfigPageView( HiGridView ):
    """
    The app's config/admin page is shown as a tabbed pane with one tab for
    each separate configuration concern.  We want them to share some
    standard state tracking and consistent page rendering.  However, we
    also want the different config areas to remain somewhat independent.

    We do this with these:

      - ConfigPageType (enum) - An entry for each configuration concenr,
        coupled only by the URL name for its mian/entry page.

      - ConfigPageView (this view) - Each section (tab) of the
        configuration/admin view should subclass. It contains some state
        management and common needs for rendering itself in the overall
        HiGridView view paradigm.

      - config/pages/config_base.html (template) - The companion template
        for the main/entry view that ensure the config pages are visually
        consistent (appearing as a tabbed pane) with navigation between
        config concerns.

    """
    
    def dispatch( self, request, *args, **kwargs ):
        """
        Override Django dispatch() method to handle dispatching to ensure
        states and views are consistent for all config tab/pages. 
        """

        view_type_changed = bool( request.view_parameters.view_type != ViewType.CONFIGURATION )
        request.view_parameters.view_type = ViewType.CONFIGURATION
        request.view_parameters.view_mode = ViewMode.MONITOR
        request.view_parameters.to_session( request )

        # Especially for editing mode, where it may have editing context in
        # many page sections, we should not asynchronously load the config
        # content without refreshing all areas first.
        #
        if view_type_changed and is_ajax( request ):
            redirect_url = request.get_full_path()
            raise antinode.redirect_response( redirect_url )

        request.config_page_type_list = list( ConfigPageType )
        request.current_config_page_type = self.config_page_type

        return super().dispatch( request, *args, **kwargs )

    @property
    def config_page_type(self) -> ConfigPageType:
        raise NotImplementedError('Subclasses must override this method.')

    
class ConfigSettingsView( ConfigPageView ):

    @property
    def config_page_type(self) -> ConfigPageType:
        return ConfigPageType.SETTINGS
    
    def get_main_template_name( self ) -> str:
        return 'config/panes/settings.html'

    def get_template_context( self, request, *args, **kwargs ):

        return {
        }
