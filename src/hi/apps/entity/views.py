import logging
from typing import Any, Dict, Optional, TYPE_CHECKING

from django.db import transaction
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.template.loader import get_template, render_to_string
from django.views.generic import View

from hi.apps.attribute.views import BaseAttributeHistoryView, BaseAttributeRestoreView
import hi.apps.common.antinode as antinode
from hi.apps.control.controller_history_manager import ControllerHistoryManager
from hi.apps.location.location_manager import LocationManager
from hi.apps.monitor.status_display_manager import StatusDisplayManager
from hi.apps.sense.sensor_history_manager import SensorHistoryMixin

from hi.views import page_not_found_response
from hi.hi_async_view import HiModalView, HiSideView

from hi.constants import DIVID

from .entity_edit_form_handler import EntityEditFormHandler
from .entity_edit_response_renderer import EntityEditResponseRenderer
from .entity_manager import EntityManager
from .entity_type_transition_handler import EntityTypeTransitionHandler
from . import forms
from .models import Entity, EntityAttribute
from .transient_models import EntityStateHistoryData
from .view_mixins import EntityViewMixin
from .entity_attribute_edit_context import EntityAttributeEditContext

if TYPE_CHECKING:
    from hi.apps.location.models import LocationView

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

    
class EntityEditModeView( HiSideView, EntityViewMixin ):

    def get_template_name( self ) -> str:
        return 'entity/edit/panes/entity_edit_mode_panel.html'

    def should_push_url( self ) -> bool:
        return True
    
    def get_template_context( self,
                              request : HttpRequest,
                              *args   : Any,
                              **kwargs: Any          ) -> Dict[str, Any]:
        entity: Entity = self.get_entity( request, *args, **kwargs )

        current_location_view: Optional['LocationView'] = None
        if request.view_parameters.view_type.is_location_view:
            current_location_view = LocationManager().get_default_location_view( request = request )

        entity_edit_mode_data = EntityManager().get_entity_edit_mode_data(
            entity = entity,
            location_view = current_location_view,
            is_editing = request.view_parameters.is_editing,
        )
        return entity_edit_mode_data.to_template_context()

    
class EntityPropertiesEditView( View, EntityViewMixin ):
    """Handle entity properties editing (name, type) only - used by sidebar.
    
    Business logic is delegated to EntityTypeTransitionHandler following
    the "keep views simple" design philosophy.
    """

    def post( self,
              request : HttpRequest,
              *args   : Any,
              **kwargs: Any          ) -> HttpResponse:
        entity: Entity = self.get_entity( request, *args, **kwargs )
        
        # Store original entity_type_str to detect changes
        original_entity_type_str: str = entity.entity_type_str

        entity_form: forms.EntityForm = forms.EntityForm( request.POST, instance = entity )
        form_valid: bool = entity_form.is_valid()
        
        if form_valid:
            # Delegate transition handling to specialized handler
            transition_handler = EntityTypeTransitionHandler()
            
            transition_response: Optional[HttpResponse] = transition_handler.handle_entity_form_save(
                request, entity, entity_form, None, original_entity_type_str
            )
            
            # Now that transaction is committed, handle any transition response
            if transition_response is not None:
                return transition_response
            
            status_code: int = 200
        else:
            status_code: int = 400

        context: Dict[str, Any] = {
            'entity': entity,
            'entity_form': entity_form,
        }
        template = get_template( 'entity/edit/panes/entity_properties_edit.html' )
        content: str = template.render( context, request = request )
        return antinode.response(
            insert_map = {
                DIVID['ENTITY_PROPERTIES_PANE']: content,
            },
            status = status_code,
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
                    'form_errors': entity_attribute_upload_form.errors
                }
            )
            
            return antinode.response(
                insert_map={
                    DIVID['ATTR_V2_STATUS_MSG']: error_html
                },
                status=400
            )

    
class EntityAttributeHistoryView(BaseAttributeHistoryView):
    """View for displaying EntityAttribute history in a modal."""
    
    def get_attribute_model_class(self):
        return EntityAttribute
    
    def get_history_url_name(self):
        return 'entity_attribute_history'
    
    def get_restore_url_name(self):
        return 'entity_attribute_restore'


class EntityAttributeRestoreView(BaseAttributeRestoreView):
    """View for restoring EntityAttribute values from history."""
    
    def get_attribute_model_class(self):
        return EntityAttribute


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
        
        # Use Django render shortcut
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
