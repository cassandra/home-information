import logging
from typing import Any, Dict

from django.db import transaction
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
import json
from django.template.loader import render_to_string
from django.views.generic import View

from hi.apps.attribute.views import BaseAttributeHistoryView, BaseAttributeRestoreView
import hi.apps.common.antinode as antinode
from hi.apps.control.controller_history_manager import ControllerHistoryManager
from hi.apps.monitor.status_display_manager import StatusDisplayManager
from hi.apps.sense.sensor_history_manager import SensorHistoryMixin

from hi.views import page_not_found_response
from hi.hi_async_view import HiModalView

from hi.constants import DIVID

from .entity_edit_form_handler import EntityEditFormHandler
from .entity_edit_response_renderer import EntityEditResponseRenderer
from . import forms
from .models import Entity, EntityAttribute
from .transient_models import EntityStateHistoryData
from .view_mixins import EntityViewMixin
from .entity_attribute_edit_context import EntityAttributeEditContext


logger = logging.getLogger(__name__)


class EntityStatusView( HiModalView, EntityViewMixin ):

    def get_template_name( self ) -> str:
        return 'entity/modals/entity_status.html'

    def get( self,
             request : HttpRequest,
             *args   : Any,
             **kwargs: Any          ) -> HttpResponse:
        entity: Entity = self.get_entity( request, *args, **kwargs )

        entity_status_data = StatusDisplayManager().get_entity_status_data( entity = entity )
        if not entity_status_data.entity_state_status_data_list:
            return EntityEditView().get( request, *args, **kwargs )
        
        context: Dict[str, Any] = entity_status_data.to_template_context()
        return self.modal_response( request, context )


class EntityEditView(HiModalView, EntityViewMixin):
    """Entity attribute editing modal with redesigned interface.
    
    This view uses a dual response pattern:
    - get(): Returns full modal using standard modal_response()
    - post(): Returns antinode fragments for async DOM updates
    
    Business logic is delegated to specialized handler classes following
    the "keep views simple" design philosophy.
    """
    
    def get_template_name(self) -> str:
        return 'entity/modals/entity_edit.html'
    
    def get( self,
             request : HttpRequest,
             *args   : Any,
             **kwargs: Any          ) -> HttpResponse:
        entity: Entity = self.get_entity(request, *args, **kwargs)
        
        # Delegate form creation and context building to handler
        form_handler: EntityEditFormHandler = EntityEditFormHandler()
        context: Dict[str, Any] = form_handler.create_initial_context(entity)
        
        return self.modal_response(request, context)
    
    def post( self,
              request : HttpRequest,
              *args   : Any,
              **kwargs: Any          ) -> HttpResponse:
        entity: Entity = self.get_entity(request, *args, **kwargs)
        
        # Delegate form handling to specialized handlers
        form_handler: EntityEditFormHandler = EntityEditFormHandler()
        renderer: EntityEditResponseRenderer = EntityEditResponseRenderer()
        
        # Create forms with POST data
        entity_form, file_attributes, regular_attributes_formset = form_handler.create_entity_forms(
            entity, request.POST
        )
        
        if form_handler.validate_forms(entity_form, regular_attributes_formset):
            # Save forms and process files
            form_handler.save_forms(entity_form, regular_attributes_formset, request, entity)
            
            # Return success response
            return renderer.render_success_response(request, entity)
        else:
            # Return error response
            return renderer.render_error_response(request, entity, entity_form, regular_attributes_formset)
    
    def get_success_url_name(self) -> str:
        return 'entity_edit'


class EntityStateHistoryView( HiModalView, EntityViewMixin, SensorHistoryMixin ):

    ENTITY_STATE_HISTORY_ITEM_MAX = 5
    
    def get_template_name( self ) -> str:
        return 'entity/modals/entity_state_history.html'

    def get( self,
             request : HttpRequest,
             *args   : Any,
             **kwargs: Any          ) -> HttpResponse:
        entity: Entity = self.get_entity( request, *args, **kwargs )
        sensor_history_list_map = self.sensor_history_manager().get_latest_entity_sensor_history(
            entity = entity,
            max_items = self.ENTITY_STATE_HISTORY_ITEM_MAX,
        )
        controller_history_list_map = ControllerHistoryManager().get_latest_entity_controller_history(
            entity = entity,
            max_items = self.ENTITY_STATE_HISTORY_ITEM_MAX,
        )        
        entity_state_history_data = EntityStateHistoryData(
            entity = entity,
            sensor_history_list_map = sensor_history_list_map,
            controller_history_list_map = controller_history_list_map,
        )
        context: Dict[str, Any] = entity_state_history_data.to_template_context()
        return self.modal_response( request, context )


class EntityAttributeUploadView( View, EntityViewMixin ):

    def post( self,
              request : HttpRequest,
              *args   : Any,
              **kwargs: Any          ) -> HttpResponse:
        entity: Entity = self.get_entity( request, *args, **kwargs )
        entity_attribute: EntityAttribute = EntityAttribute( entity = entity )
        entity_attribute_upload_form: forms.EntityAttributeUploadForm = forms.EntityAttributeUploadForm(
            request.POST,
            request.FILES,
            instance = entity_attribute,
        )
        
        if entity_attribute_upload_form.is_valid():
            with transaction.atomic():
                entity_attribute_upload_form.save()   
            
            # Render new file card HTML to append to file grid
            attr_context = EntityAttributeEditContext(entity)
            context = {'attribute': entity_attribute, 'entity': entity}
            context.update(attr_context.to_template_context())
            
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
                        "target": f"#{DIVID['ATTR_V2_FILE_GRID']}",
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
                    'error_message': 'File upload failed. Please check the file and try again.',
                    'form_errors': entity_attribute_upload_form.errors
                }
            )
            
            # Build JSON error response for failed file upload
            response_data = {
                "success": False,
                "updates": [
                    {
                        "target": f"#{DIVID['ATTR_V2_STATUS_MSG']}",
                        "html": error_html,
                        "mode": "replace"
                    }
                ],
                "message": "File upload failed. Please check the file and try again."
            }
            
            return HttpResponse(
                json.dumps(response_data),
                content_type='application/json',
                status=400
            )


class EntityAttributeHistoryInlineView(BaseAttributeHistoryView):
    """View for displaying EntityAttribute history inline within the edit modal."""

    ATTRIBUTE_HISTORY_VIEW_LIMIT = 50
    
    def get_template_name(self):
        return 'attribute/components/attribute_history_inline.html'
    
    def get_attribute_model_class(self):
        return EntityAttribute
    
    def get_history_url_name(self):
        return 'entity_attribute_history_inline'
    
    def get_restore_url_name(self):
        return 'entity_attribute_restore_inline'
    
    def get( self,
             request      : HttpRequest,
             entity_id    : int,
             attribute_id : int,
             *args        : Any,
             **kwargs     : Any          ) -> HttpResponse:
        # Validate that the attribute belongs to this entity for security
        try:
            attribute: EntityAttribute = EntityAttribute.objects.get(pk=attribute_id, entity_id=entity_id)
        except EntityAttribute.DoesNotExist:
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
        attr_context = EntityAttributeEditContext(attribute.entity)
        
        context: Dict[str, Any] = {
            'entity': attribute.entity,
            'attribute': attribute,
            'history_records': history_records,
            'history_url_name': self.get_history_url_name(),
            'restore_url_name': self.get_restore_url_name(),
        }
        
        # Merge in the context variables from AttributeEditContext
        context.update(attr_context.to_template_context())
        
        # Check if this is an AJAX request and return JSON response
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
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
            return render(request, self.get_template_name(), context)


class EntityAttributeRestoreInlineView(BaseAttributeRestoreView):
    """View for restoring EntityAttribute values from history within the edit modal."""
    
    def get_attribute_model_class(self):
        return EntityAttribute
    
    def get( self,
             request      : HttpRequest,
             entity_id    : int,
             attribute_id : int,
             history_id   : int,
             *args        : Any,
             **kwargs     : Any          ) -> HttpResponse:
        # Validate that the attribute belongs to this entity for security  
        try:
            attribute: EntityAttribute = EntityAttribute.objects.get(pk=attribute_id, entity_id=entity_id)
        except EntityAttribute.DoesNotExist:
            return page_not_found_response(request, "Attribute not found.")
        
        # Get the history record to restore from
        history_model_class = attribute._get_history_model_class()
        if not history_model_class:
            return page_not_found_response(request, "No history available for this attribute type.")
        
        try:
            history_record = history_model_class.objects.get(pk=history_id, attribute=attribute)
        except history_model_class.DoesNotExist:
            return page_not_found_response(request, "History record not found.")
        
        # Restore the value from the history record
        attribute.value = history_record.value
        attribute.save()  # This will create a new history record
        
        # Delegate to EntityEditView logic to return updated modal content
        entity: Entity = attribute.entity
        
        # Use EntityEditResponseRenderer to return updated modal content
        from .entity_edit_response_renderer import EntityEditResponseRenderer
        renderer: EntityEditResponseRenderer = EntityEditResponseRenderer()
        return renderer.render_success_response(
            request = request,
            entity = entity,
        )
