import logging
import json
from typing import Any, Dict

from django.db import transaction
from django.core.exceptions import BadRequest
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import render, reverse
from django.template.loader import render_to_string
from django.views.generic import View

from hi.apps.common.utils import is_ajax

from hi.apps.attribute.views import BaseAttributeHistoryView, BaseAttributeRestoreView
from hi.apps.attribute.views_base import AttributeEditViewMixin
from hi.apps.attribute.response_helpers import AttributeResponseBuilder, UpdateMode
from hi.apps.attribute.response_constants import DefaultMessages, HTTPHeaders

from hi.enums import ItemType, ViewType
from hi.exceptions import ForceSynchronousException
from hi.hi_async_view import HiModalView
from hi.hi_grid_view import HiGridView
from hi.views import page_not_found_response

from .forms import LocationAttributeUploadForm
from .location_manager import LocationManager
from .models import Location, LocationView, LocationAttribute
from .view_mixins import LocationViewMixin
from .location_attribute_edit_context import LocationAttributeItemEditContext

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


class LocationEditView( HiModalView, LocationViewMixin, AttributeEditViewMixin ):
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
        location = self.get_location(request, *args, **kwargs)
        attr_item_context = LocationAttributeItemEditContext( location = location )
        template_context = self.create_initial_template_context(
            attr_item_context= attr_item_context,
        )
        return self.modal_response( request, template_context )
    
    def post( self,
              request : HttpRequest,
              *args   : Any,
              **kwargs: Any          ) -> HttpResponse:
        location = self.get_location(request, *args, **kwargs)
        attr_item_context = LocationAttributeItemEditContext( location = location )
        return self.post_attribute_form(
            request = request,
            attr_item_context = attr_item_context,
        )

    
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
            from hi.apps.location.location_attribute_edit_context import LocationAttributeItemEditContext
            attr_item_context = LocationAttributeItemEditContext(location)
            context = {'attribute': location_attribute, 'location': location}
            context.update(attr_item_context.to_template_context())
            
            file_card_html: str = render_to_string(
                'attribute/components/file_card.html',
                context,
                request=request
            )
            
            # Build JSON response for successful file upload
            response_data = {
                "success": True,
                "updates": [
                    {
                        "target": f"#{attr_item_context.file_grid_html_id}",
                        "html": file_card_html,
                        "mode": "append"
                    }
                ],
                "message": "File uploaded successfully"
            }
            
            return HttpResponse(
                json.dumps(response_data),
                content_type='application/json'
            )
        else:
            # Render error message to status area
            error_html: str = render_to_string(
                'attribute/components/status_message.html',
                {
                    'error_message': DefaultMessages.UPLOAD_ERROR,
                    'form_errors': location_attribute_upload_form.errors
                }
            )
            
            # Build JSON error response for failed file upload
            return (AttributeResponseBuilder()
                    .error()
                    .add_update(
                        target=f'#{attr_item_context.status_msg_html_id}',
                        html=error_html,
                        mode=UpdateMode.REPLACE
                    )
                    .with_message(DefaultMessages.UPLOAD_ERROR)
                    .build_http_response())


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
        attr_item_context = LocationAttributeItemEditContext(attribute.location)
        
        context: Dict[str, Any] = {
            'location': attribute.location,
            'attribute': attribute,
            'history_records': history_records,
            'history_url_name': self.get_history_url_name(),
            'restore_url_name': self.get_restore_url_name(),
        }
        
        # Merge in the context variables from AttributeItemEditContext
        context.update(attr_item_context.to_template_context())
        
        # Check if this is an AJAX request and return JSON response
        if request.headers.get(HTTPHeaders.X_REQUESTED_WITH) == HTTPHeaders.XML_HTTP_REQUEST:
            # Render the template to HTML string
            html_content = render_to_string(
                template_name=self.get_template_name(), 
                context=context, 
                request=request
            )
            
            # Build JSON response with target selector for history content
            return (AttributeResponseBuilder()
                    .success()
                    .add_update(
                        target=f"#{attr_item_context.history_target_id(attribute.id)}",
                        html=html_content,
                        mode=UpdateMode.REPLACE
                    )
                    .with_message(f"History for {attribute.name}")
                    .build_http_response())
        else:
            # Use Django render shortcut for non-AJAX requests
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
