import logging
from typing import Any, Dict

from django.db import transaction
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.views.generic import View

from hi.apps.attribute.response_helpers import AttributeResponseBuilder, UpdateMode
from hi.apps.attribute.response_constants import DefaultMessages, HTTPHeaders

from hi.apps.attribute.views import BaseAttributeHistoryView, BaseAttributeRestoreView
from hi.apps.attribute.views_base import AttributeEditViewMixin
from hi.apps.control.controller_history_manager import ControllerHistoryManager
from hi.apps.monitor.status_display_manager import StatusDisplayManager
from hi.apps.sense.sensor_history_manager import SensorHistoryMixin

from hi.views import page_not_found_response
from hi.hi_async_view import HiModalView

from . import forms
from .models import Entity, EntityAttribute
from .transient_models import EntityStateHistoryData
from .view_mixins import EntityViewMixin
from .entity_attribute_edit_context import EntityAttributeItemEditContext


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


class EntityEditView( HiModalView, EntityViewMixin, AttributeEditViewMixin ):
    """
    This view uses a dual response pattern:
      - get(): Returns full modal using standard modal_response()
      - post(): Returns custom JSON response with HTML fragments for async DOM updates
    """
    
    def get_template_name(self) -> str:
        return 'entity/modals/entity_edit.html'
    
    def get( self,
             request : HttpRequest,
             *args   : Any,
             **kwargs: Any          ) -> HttpResponse:
        entity = self.get_entity(request, *args, **kwargs)
        attr_item_context = EntityAttributeItemEditContext( entity = entity )
        template_context = self.create_initial_template_context(
            attr_item_context= attr_item_context,
        )
        return self.modal_response( request, template_context )
    
    def post( self,
              request : HttpRequest,
              *args   : Any,
              **kwargs: Any          ) -> HttpResponse:
        entity = self.get_entity(request, *args, **kwargs)
        attr_item_context = EntityAttributeItemEditContext( entity = entity )
        return self.post_attribute_form(
            request = request,
            attr_item_context = attr_item_context,
        )


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
            attr_item_context = EntityAttributeItemEditContext(entity)
            context = {'attribute': entity_attribute, 'entity': entity}
            context.update(attr_item_context.to_template_context())
            
            file_card_html: str = render_to_string(
                'attribute/components/file_card.html',
                context,
                request=request
            )
            
            # Build JSON response for successful file upload
            return (
                AttributeResponseBuilder()
                .success()
                .add_update(
                    target=f"#{attr_item_context.file_grid_html_id}",
                    html=file_card_html,
                    mode=UpdateMode.APPEND
                )
                .with_message(DefaultMessages.UPLOAD_SUCCESS)
                .build_http_response()
            )
        else:
            # Render error message to status area
            error_html: str = render_to_string(
                'attribute/components/status_message.html',
                {
                    'error_message': DefaultMessages.UPLOAD_ERROR,
                    'form_errors': entity_attribute_upload_form.errors
                }
            )

            # Build JSON error response for failed file upload
            return (
                AttributeResponseBuilder()
                .error()
                .add_update(
                    target=f'#{attr_item_context.status_msg_html_id}',
                    html=error_html,
                    mode=UpdateMode.REPLACE
                )
                .with_message(DefaultMessages.UPLOAD_ERROR)
                .build_http_response()
            )


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
        attr_item_context = EntityAttributeItemEditContext(attribute.entity)
        
        context: Dict[str, Any] = {
            'entity': attribute.entity,
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
            return (
                AttributeResponseBuilder()
                .success()
                .add_update(
                    target=f"#{attr_item_context.history_target_id(attribute.id)}",
                    html=html_content,
                    mode=UpdateMode.REPLACE
                )
                .with_message(f"History for {attribute.name}")
                .build_http_response()
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
        """ Need to do restore in a GET since nested in main form and cannot have a form in a form """
        
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
