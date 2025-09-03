import logging


from django.conf import settings
from django.http import JsonResponse, HttpResponseRedirect
from django.urls import reverse
from django.views.generic import View

import hi.apps.common.antinode as antinode

from hi.enums import ViewMode, ViewType
from hi.hi_grid_view import HiGridView
from hi.apps.attribute.views import BaseAttributeHistoryView, BaseAttributeRestoreView

from .enums import ConfigPageType
from .models import SubsystemAttribute
from .settings_mixins import SettingsMixin
from .config_edit_form_handler import ConfigEditFormHandler
from .config_edit_response_renderer import ConfigEditResponseRenderer

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

    
class ConfigSettingsView( ConfigPageView, SettingsMixin ):

    @property
    def config_page_type(self) -> ConfigPageType:
        return ConfigPageType.SETTINGS
    
    def get_main_template_name( self ) -> str:
        return 'config/panes/settings.html'

    def get_main_template_context( self, request, *args, **kwargs ):
        """Delegate form creation and context building to handler."""
        form_handler = ConfigEditFormHandler()
        subsystem_id = kwargs.get('subsystem_id')
        return form_handler.create_initial_context(selected_subsystem_id=subsystem_id)

    def post( self, request, *args, **kwargs ):
        """Handle unified form submission using helper classes."""
        
        # Delegate form handling to specialized handlers
        form_handler = ConfigEditFormHandler()
        renderer = ConfigEditResponseRenderer()
        subsystem_id = kwargs.get('subsystem_id')
        
        # Create formsets with POST data
        subsystem_formset_list = form_handler.create_config_forms(
            request.POST, request.FILES
        )

        # Validate all formsets
        if form_handler.validate_all_formsets(subsystem_formset_list):
            # Save all formsets
            form_handler.save_all_formsets(subsystem_formset_list, request)
            
            # Return success response with fresh data
            return renderer.render_success_response(request, selected_subsystem_id=subsystem_id)
        else:
            # Return error response with validation errors
            return renderer.render_error_response(request, subsystem_formset_list, selected_subsystem_id=subsystem_id)
       
        
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


class SubsystemAttributeHistoryInlineView(BaseAttributeHistoryView):
    """View for displaying SubsystemAttribute history inline within the edit interface."""
    ATTRIBUTE_HISTORY_VIEW_LIMIT = 50
    
    def get_template_name(self):
        return 'attribute/components/attribute_history_inline.html'
    
    def get_attribute_model_class(self):
        return SubsystemAttribute
    
    def get_history_url_name(self):
        return 'subsystem_attribute_history_inline'
    
    def get_restore_url_name(self):
        return 'subsystem_attribute_restore_inline'
    
    def get(self, request, subsystem_id, attribute_id, *args, **kwargs):
        """Custom get implementation that creates the SubsystemAttributeEditContext."""
        # Validate that the attribute belongs to this subsystem for security
        try:
            attribute = SubsystemAttribute.objects.get(pk=attribute_id, subsystem_id=subsystem_id)
        except SubsystemAttribute.DoesNotExist:
            from hi.views import page_not_found_response
            return page_not_found_response(request, "Attribute not found.")
        
        # Get history records for this attribute
        history_model_class = attribute._get_history_model_class()
        if history_model_class:
            history_records = history_model_class.objects.filter(
                attribute=attribute
            ).order_by('-changed_datetime')[:self.ATTRIBUTE_HISTORY_VIEW_LIMIT]
        else:
            history_records = []
        
        # Create the attribute edit context for template generalization
        from .subsystem_attribute_edit_context import SubsystemAttributeEditContext
        attr_context = SubsystemAttributeEditContext(attribute.subsystem)
        
        context = {
            'subsystem': attribute.subsystem,
            'attribute': attribute,
            'history_records': history_records,
            'history_url_name': self.get_history_url_name(),
            'restore_url_name': self.get_restore_url_name(),
        }
        
        # Merge in the context variables from AttributeEditContext
        context.update(attr_context.to_template_context())
        
        # Check if this is an AJAX request and return JSON response
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            from django.template.loader import render_to_string
            from django.http import HttpResponse
            import json
            
            # Render the template to HTML string
            html_content = render_to_string(self.get_template_name(), context, request=request)
            
            # Build JSON response with target selector for history content
            response_data = {
                "success": True,
                "updates": [
                    {
                        "target": f"#{attr_context.history_target_id(attribute.id)}",
                        "html": html_content,
                        "mode": "replace"
                    }
                ],
                "message": f"History for {attribute.name}"
            }
            
            return HttpResponse(
                json.dumps(response_data),
                content_type='application/json'
            )
        else:
            # Use Django render shortcut for non-AJAX requests
            from django.shortcuts import render
            return render(request, self.get_template_name(), context)


class SubsystemAttributeRestoreInlineView(BaseAttributeRestoreView):
    """View for restoring SubsystemAttribute values from history inline."""
    
    def get_attribute_model_class(self):
        return SubsystemAttribute
    
    def get(self, request, subsystem_id, attribute_id, history_id, *args, **kwargs):
        """Custom get implementation for restoring from history."""
        # Validate that the attribute belongs to this subsystem for security
        try:
            attribute = SubsystemAttribute.objects.get(pk=attribute_id, subsystem_id=subsystem_id)
        except SubsystemAttribute.DoesNotExist:
            from hi.views import page_not_found_response
            return page_not_found_response(request, "Attribute not found.")
        
        # Get the history record to restore from
        history_model_class = attribute._get_history_model_class()
        if not history_model_class:
            from hi.views import page_not_found_response
            return page_not_found_response(request, "No history available for this attribute type.")
        
        try:
            history_record = history_model_class.objects.get(pk=history_id, attribute=attribute)
        except history_model_class.DoesNotExist:
            from hi.views import page_not_found_response
            return page_not_found_response(request, "History record not found.")
        
        # Restore the value from the history record
        attribute.value = history_record.value
        attribute.save()  # This will create a new history record
        
        # Return updated content using ConfigEditResponseRenderer
        from .config_edit_response_renderer import ConfigEditResponseRenderer
        renderer = ConfigEditResponseRenderer()
        return renderer.render_success_response(request, selected_subsystem_id=str(subsystem_id))
