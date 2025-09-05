import logging

from django.conf import settings
from django.http import JsonResponse, HttpResponseRedirect
from django.urls import reverse
from django.views.generic import View

import hi.apps.common.antinode as antinode
from hi.views import page_not_found_response

from hi.enums import ViewMode, ViewType
from hi.hi_grid_view import HiGridView
from hi.apps.attribute.view_mixins import AttributeMultiEditViewMixin

from .enums import ConfigPageType
from .models import SubsystemAttribute
from .settings_mixins import SubsystemAttributeMixin
from .subsystem_attribute_edit_context import (
    SubsystemAttributeItemEditContext,
    SubsystemAttributePageEditContext,
)

logger = logging.getLogger('__name__')


class ConfigHomeView( View ):

    def get( self, request, *args, **kwargs ):
        redirect_url = reverse( ConfigPageType.default().url_name )
        return HttpResponseRedirect( redirect_url )        

    
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

    
class ConfigInternalView( View ):

    @classmethod
    def get_config_data(self):
        return {
            'ALLOWED_HOSTS': settings.ALLOWED_HOSTS,
            'DATABASES_NAME_PATH': settings.DATABASES['default']['NAME'],
            'REDIS_HOST': settings.REDIS_HOST,
            'REDIS_PORT': settings.REDIS_PORT,
            'MEDIA_ROOT': settings.MEDIA_ROOT,
            'DEFAULT_FROM_EMAIL': settings.DEFAULT_FROM_EMAIL,
            'SERVER_EMAIL': settings.SERVER_EMAIL,
            'EMAIL_HOST': settings.EMAIL_HOST,
            'EMAIL_PORT': settings.EMAIL_PORT,
            'EMAIL_HOST_USER': settings.EMAIL_HOST_USER,
            'EMAIL_USE_TLS': settings.EMAIL_USE_TLS,
            'EMAIL_USE_SSL': settings.EMAIL_USE_SSL,
            'CORS_ALLOWED_ORIGINS': settings.CORS_ALLOWED_ORIGINS,
            'CSP_DEFAULT_SRC': settings.CSP_DEFAULT_SRC,
            'CSP_CONNECT_SRC': settings.CSP_CONNECT_SRC,
            'CSP_FRAME_SRC': settings.CSP_FRAME_SRC,
            'CSP_SCRIPT_SRC': settings.CSP_SCRIPT_SRC,
            'CSP_STYLE_SRC': settings.CSP_STYLE_SRC,
            'CSP_MEDIA_SRC': settings.CSP_MEDIA_SRC,
            'CSP_IMG_SRC': settings.CSP_IMG_SRC,
            'CSP_CHILD_SRC': settings.CSP_CHILD_SRC,
            'CSP_FONT_SRC': settings.CSP_FONT_SRC,
        }
        
    def get(self, request, *args, **kwargs):
        data = self.get_config_data()
        return JsonResponse( data, safe = False )

    
class ConfigSettingsView( ConfigPageView,
                          SubsystemAttributeMixin,
                          AttributeMultiEditViewMixin ):

    @property
    def config_page_type(self) -> ConfigPageType:
        return ConfigPageType.SETTINGS
    
    def get_main_template_name( self ) -> str:
        return 'config/panes/settings.html'

    def get_main_template_context( self, request, *args, **kwargs ):

        attr_item_context_list = self._create_attr_item_context_list()

        selected_subsystem_id = kwargs.get('subsystem_id')
        if not selected_subsystem_id and attr_item_context_list:
            selected_subsystem_id = str(attr_item_context_list[0].owner_id)

        attr_page_context = SubsystemAttributePageEditContext(
            selected_subsystem_id = selected_subsystem_id,
        )
        return self.create_initial_template_context(
            attr_page_context = attr_page_context,
            attr_item_context_list = attr_item_context_list,
        )
        
    def post( self, request, *args, **kwargs ):

        attr_item_context_list = self._create_attr_item_context_list()

        selected_subsystem_id = kwargs.get('subsystem_id')
        if not selected_subsystem_id and attr_item_context_list:
            selected_subsystem_id = str(attr_item_context_list[0].owner_id)

        attr_page_context = SubsystemAttributePageEditContext(
            selected_subsystem_id = selected_subsystem_id,
        )
            
        return self.post_attribute_form(
            request = request,
            attr_page_context = attr_page_context,
            attr_item_context_list = attr_item_context_list,
        )
        

class SubsystemAttributeHistoryInlineView( View, AttributeMultiEditViewMixin ):

    def get(self, request, subsystem_id, attribute_id, *args, **kwargs):
        # Validate that the attribute belongs to this subsystem for security
        try:
            attribute = SubsystemAttribute.objects.select_related('subsystem').get(
                pk = attribute_id, subsystem_id = subsystem_id )
        except SubsystemAttribute.DoesNotExist:
            return page_not_found_response(request, "Attribute not found.")

        attr_item_context = SubsystemAttributeItemEditContext(
            subsystem = attribute.subsystem,
        )
        return self.get_history(
            request = request,
            attribute = attribute,
            attr_item_context = attr_item_context,
        )


class SubsystemAttributeRestoreInlineView( View,
                                           SubsystemAttributeMixin,
                                           AttributeMultiEditViewMixin ):
    """View for restoring SubsystemAttribute values from history inline."""
    
    def get(self, request, subsystem_id, attribute_id, history_id, *args, **kwargs):
        """ Need to do restore in a GET since nested in main form and cannot have a form in a form """
        try:
            attribute = SubsystemAttribute.objects.select_related('subsystem').get(
                pk = attribute_id, subsystem_id = subsystem_id
            )
        except SubsystemAttribute.DoesNotExist:
            return page_not_found_response(request, "Attribute not found.")

        attr_page_context = SubsystemAttributePageEditContext(
            selected_subsystem_id = subsystem_id,
        )
        attr_item_context_list = self._create_attr_item_context_list()

        return self.post_restore(
            request = request,
            attribute = attribute,
            history_id = history_id,
            attr_page_context = attr_page_context,
            attr_item_context_list = attr_item_context_list,
        )
