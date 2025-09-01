import logging
from typing import Any, Dict

from django.db import transaction
from django.core.exceptions import BadRequest
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import render, reverse
from django.template.loader import render_to_string
from django.views.generic import View

import hi.apps.common.antinode as antinode
from hi.apps.common.utils import is_ajax

from hi.constants import DIVID
from hi.enums import ItemType, ViewType
from hi.exceptions import ForceSynchronousException
from hi.hi_async_view import HiModalView
from hi.hi_grid_view import HiGridView
from hi.apps.attribute.views import BaseAttributeHistoryView, BaseAttributeRestoreView
from hi.views import page_not_found_response

from .forms import LocationAttributeUploadForm
from .location_manager import LocationManager
from .models import Location, LocationView, LocationAttribute
from .view_mixins import LocationViewMixin
from .location_attribute_edit_context import LocationAttributeEditContext
from .location_edit_form_handler import LocationEditFormHandler
from .location_edit_response_renderer import LocationEditResponseRenderer

logger = logging.getLogger(__name__)


class LocationViewDefaultView( View ):

    def get(self, request, *args, **kwargs):
        try:
            location_view = LocationManager().get_default_location_view( request = request )
            request.view_parameters.view_type = ViewType.LOCATION_VIEW
            request.view_parameters.update_location_view( location_view )
            request.view_parameters.to_session( request )
            redirect_url = reverse(
                'location_view',
                kwargs = { 'location_view_id': location_view.id }
            )
        except LocationView.DoesNotExist:
            redirect_url = reverse( 'start' )
            
        return HttpResponseRedirect( redirect_url )

    
class LocationViewView( HiGridView, LocationViewMixin ):

    def get_main_template_name( self ) -> str:
        return self.LOCATION_VIEW_TEMPLATE_NAME

    def get_main_template_context( self, request, *args, **kwargs ):
        location_view = self.get_location_view( request, *args, **kwargs )

        if self.should_force_sync_request(
                request = request,
                next_view_type = ViewType.LOCATION_VIEW,
                next_id = location_view.id ):
            raise ForceSynchronousException()
        
        request.view_parameters.view_type = ViewType.LOCATION_VIEW
        request.view_parameters.update_location_view( location_view )
        request.view_parameters.to_session( request )

        location_view_data = LocationManager().get_location_view_data(
            location_view = location_view,
            include_status_display_data = bool( not request.view_parameters.is_editing ),
        )

        return {
            'is_async_request': is_ajax( request ),
            'location_view': location_view,
            'location_view_data': location_view_data,
        }

    
class LocationSwitchView( View, LocationViewMixin ):

    def get(self, request, *args, **kwargs):
        location = self.get_location( request, *args, **kwargs )

        location_view = location.views.order_by( 'order_id' ).first()
        if not location_view:
            raise BadRequest( 'No views defined for this location.' )

        request.view_parameters.view_type = ViewType.LOCATION_VIEW
        request.view_parameters.update_location_view( location_view = location_view )
        request.view_parameters.to_session( request )

        redirect_url = reverse(
            'location_view',
            kwargs = { 'location_view_id': location_view.id }
        )
        return HttpResponseRedirect( redirect_url )


class LocationItemStatusView( View ):

    def get(self, request, *args, **kwargs):
        try:
            ( item_type, item_id ) = ItemType.parse_from_dict( kwargs )
        except ValueError:
            raise BadRequest( 'Bad item id.' )
        
        if item_type == ItemType.ENTITY:
            redirect_url = reverse( 'entity_status', kwargs = { 'entity_id': item_id } )
            return HttpResponseRedirect( redirect_url )
    
        if item_type == ItemType.COLLECTION:
            redirect_url = reverse( 'collection_view', kwargs = { 'collection_id': item_id } )
            return HttpResponseRedirect( redirect_url )

        raise BadRequest( f'Unknown item type "{item_type}".' )


class LocationEditView(HiModalView, LocationViewMixin):
    """Location attribute editing modal with redesigned interface.
    
    This view uses a dual response pattern:
    - get(): Returns full modal using standard modal_response()
    - post(): Returns antinode fragments for async DOM updates
    
    Business logic is delegated to specialized handler classes following
    the "keep views simple" design philosophy.
    """
    
    def get_template_name(self) -> str:
        return 'location/modals/location_edit.html'
    
    def get( self,
             request : HttpRequest,
             *args   : Any,
             **kwargs: Any          ) -> HttpResponse:
        location: Location = self.get_location(request, *args, **kwargs)
        
        # Delegate form creation and context building to handler
        form_handler = LocationEditFormHandler()
        context: Dict[str, Any] = form_handler.create_initial_context(location)
        
        return self.modal_response(request, context)
    
    def post( self,
              request : HttpRequest,
              *args   : Any,
              **kwargs: Any          ) -> HttpResponse:
        location: Location = self.get_location(request, *args, **kwargs)
        
        # Delegate form handling to specialized handlers
        form_handler = LocationEditFormHandler()
        renderer = LocationEditResponseRenderer()
        
        # Create forms with POST data
        (
            location_form,
            file_attributes,
            regular_attributes_formset,
        ) = form_handler.create_location_forms(
            location, request.POST
        )
        
        if form_handler.validate_forms(location_form, regular_attributes_formset):
            # Save forms and process files
            form_handler.save_forms(location_form, regular_attributes_formset, request, location)
            
            # Return success response
            return renderer.render_success_response(request, location)
        else:
            # Return error response
            return renderer.render_error_response(
                request, location, location_form, regular_attributes_formset
            )
    
    def get_success_url_name(self) -> str:
        return 'location_edit'

    
class LocationAttributeUploadView( View, LocationViewMixin ):

    def post( self,
              request : HttpRequest,
              *args   : Any,
              **kwargs: Any          ) -> HttpResponse:
        location = self.get_location( request, *args, **kwargs )
        location_attribute = LocationAttribute( location = location )
        location_attribute_upload_form = LocationAttributeUploadForm(
            request.POST,
            request.FILES,
            instance = location_attribute,
        )
        
        if location_attribute_upload_form.is_valid():
            with transaction.atomic():
                location_attribute_upload_form.save()   
            
            # Render new file card HTML to append to file grid
            from hi.apps.location.location_attribute_edit_context import LocationAttributeEditContext
            attr_context = LocationAttributeEditContext(location)
            context = {'attribute': location_attribute, 'location': location}
            context.update(attr_context.to_template_context())
            
            file_card_html: str = render_to_string(
                'attribute/components/file_card.html',
                context,
                request=request
            )
            
            return antinode.response(
                append_map={
                    DIVID['ATTR_V2_FILE_GRID']: file_card_html
                },
                scroll_to=DIVID['ATTR_V2_FILE_GRID']
            )
        else:
            # Render error message to status area
            error_html: str = render_to_string(
                'attribute/components/status_message.html',
                {
                    'error_message': 'File upload failed. Please check the file and try again.',
                    'form_errors': location_attribute_upload_form.errors
                }
            )
            
            return antinode.response(
                insert_map={
                    DIVID['ATTR_V2_STATUS_MSG']: error_html
                },
                status=400
            )


class LocationAttributeHistoryInlineView(BaseAttributeHistoryView):
    """View for displaying LocationAttribute history inline within the edit modal."""

    ATTRIBUTE_HISTORY_VIEW_LIMIT = 50
    
    def get_template_name(self):
        return 'attribute/components/attribute_history_inline.html'
    
    def get_attribute_model_class(self):
        return LocationAttribute
    
    def get_history_url_name(self):
        return 'location_attribute_history_inline'
    
    def get_restore_url_name(self):
        return 'location_attribute_restore_inline'
    
    def get( self,
             request       : HttpRequest,
             location_id   : int,
             attribute_id  : int,
             *args         : Any,
             **kwargs      : Any          ) -> HttpResponse:
        # Validate that the attribute belongs to this location for security
        try:
            attribute: LocationAttribute = LocationAttribute.objects.get(
                pk=attribute_id, location_id=location_id
            )
        except LocationAttribute.DoesNotExist:
            return page_not_found_response(request, "Attribute not found.")
        
        # Get history records for this attribute
        history_model_class = attribute._get_history_model_class()
        if history_model_class:
            history_records = history_model_class.objects.filter(
                attribute=attribute
            ).order_by('-changed_datetime')[:self.ATTRIBUTE_HISTORY_VIEW_LIMIT]  # Limit for inline display
        else:
            history_records = []
        
        # Create the attribute edit context for template generalization
        attr_context = LocationAttributeEditContext(attribute.location)
        
        context: Dict[str, Any] = {
            'location': attribute.location,
            'attribute': attribute,
            'history_records': history_records,
            'history_url_name': self.get_history_url_name(),
            'restore_url_name': self.get_restore_url_name(),
        }
        
        # Merge in the context variables from AttributeEditContext
        context.update(attr_context.to_template_context())
        
        # Use Django render shortcut
        return render(request, self.get_template_name(), context)


class LocationAttributeRestoreInlineView(BaseAttributeRestoreView):
    """View for restoring LocationAttribute values from history within the edit modal."""
    
    def get_attribute_model_class(self):
        return LocationAttribute
    
    def get( self,
             request       : HttpRequest,
             location_id   : int,
             attribute_id  : int,
             history_id    : int,
             *args         : Any,
             **kwargs      : Any          ) -> HttpResponse:
        # Validate that the attribute belongs to this location for security  
        try:
            attribute: LocationAttribute = LocationAttribute.objects.get(
                pk=attribute_id, location_id=location_id
            )
        except LocationAttribute.DoesNotExist:
            return page_not_found_response(request, "Attribute not found.")
        
        # Get the history record to restore from
        history_model_class = attribute._get_history_model_class()
        if not history_model_class:
            return page_not_found_response(request, "No history available for this attribute type.")
        
        try:
            history_record = history_model_class.objects.get(
                pk=history_id, attribute=attribute
            )
        except history_model_class.DoesNotExist:
            return page_not_found_response(request, "History record not found.")
        
        # Restore the value from the history record
        attribute.value = history_record.value
        attribute.save()  # This will create a new history record
        
        # Delegate to LocationEditView logic to return updated modal content
        location: Location = attribute.location
        
        # Use LocationEditView's render_success_response logic
        from .location_edit_response_renderer import LocationEditResponseRenderer
        renderer: LocationEditResponseRenderer = LocationEditResponseRenderer()
        return renderer.render_success_response(
            request = request,
            location = location,
        )
