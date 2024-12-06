from django.db import transaction
from django.shortcuts import render

import hi.apps.common.antinode as antinode

from hi.enums import ViewMode, ViewType
from hi.hi_grid_view import HiGridView

from .enums import ConfigPageType
from .forms import SubsystemAttributeFormSet
from .settings_manager import SettingsManager


class ConfigPageView( HiGridView ):
    """
    The app's config/admin page is shown in the main area of the HiGridView
    layout. It is a tabbed pane with one tab for each separate
    configuration concern.  We want them to share some standard state
    tracking and consistent page rendering for each individual
    configuration concern.  However, we also want the different config
    areas to remain somewhat independent.

    We do this with these:

      - ConfigPageType (enum) - An entry for each configuration concern,
        coupled only by the URL name for its main/entry page.

      - ConfigPageView (this view) - Each enum or section (tab) of the
        configuration/admin view should subclass this. It contains some state
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
        if self.should_force_sync_request(
                request = request,
                next_view_type = ViewType.CONFIGURATION,
                next_id = None ):
            redirect_url = request.get_full_path()
            return antinode.redirect_response( redirect_url )
        
        request.view_parameters.view_type = ViewType.CONFIGURATION
        request.view_parameters.view_mode = ViewMode.MONITOR
        request.view_parameters.to_session( request )

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
        
        subsystem_list = SettingsManager().get_subsystems()

        subsystem_attribute_formset_list = list()
        for subsystem in subsystem_list:
            subsystem_attribute_formset = SubsystemAttributeFormSet(
                instance = subsystem,
                prefix = f'subsystem-{subsystem.id}',
                form_kwargs = {
                    'show_as_editable': True,
                },
            )
            subsystem_attribute_formset_list.append( subsystem_attribute_formset )
            continue
        
        return {
            'subsystem_attribute_formset_list': subsystem_attribute_formset_list,
        }

    def post( self, request, *args, **kwargs ):

        subsystem_list = SettingsManager().get_subsystems()

        all_valid = True
        subsystem_attribute_formset_list = list()
        for subsystem in subsystem_list:
            subsystem_attribute_formset = SubsystemAttributeFormSet(
                request.POST,
                request.FILES,
                instance = subsystem,
                prefix = f'subsystem-{subsystem.id}',
            )
            if not subsystem_attribute_formset.is_valid():
                all_valid = False
            subsystem_attribute_formset_list.append( subsystem_attribute_formset )           
            continue

        if all_valid:
            with transaction.atomic():
                for subsystem_attribute_formset in subsystem_attribute_formset_list:
                    subsystem_attribute_formset.save()
                    continue

        context = {
            'subsystem_attribute_formset_list': subsystem_attribute_formset_list,
        }
        return render( request, 'config/panes/settings_form.html', context )
        
