import logging
from typing import Any, Dict

from django.http import HttpRequest, HttpResponse
from django.views.generic import View

from hi.apps.attribute.view_mixins import AttributeEditViewMixin
from hi.apps.control.controller_history_manager import ControllerHistoryManager
from hi.apps.monitor.status_display_manager import StatusDisplayManager
from hi.apps.sense.sensor_history_manager import SensorHistoryMixin

from hi.views import page_not_found_response
from hi.hi_async_view import HiModalView

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
        entity = self.get_entity( request, *args, **kwargs )

        entity_status_data = StatusDisplayManager().get_entity_status_data( entity = entity )
        if not entity_status_data.entity_state_status_data_list:
            return EntityEditView().get( request, *args, **kwargs )
        
        context = entity_status_data.to_template_context()
        return self.modal_response( request, context )


class EntityStateHistoryView( HiModalView, EntityViewMixin, SensorHistoryMixin ):

    ENTITY_STATE_HISTORY_ITEM_MAX = 5
    
    def get_template_name( self ) -> str:
        return 'entity/modals/entity_state_history.html'

    def get( self, request,*args, **kwargs ):
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


class EntityEditView( HiModalView, EntityViewMixin, AttributeEditViewMixin ):
    """
    This view uses a dual response pattern:
      - get(): Returns full modal using standard modal_response()
      - post(): Returns custom JSON response with HTML fragments for async DOM updates
    """
    
    def get_template_name(self) -> str:
        return 'entity/modals/entity_edit.html'
    
    def get( self, request,*args, **kwargs ):
        entity = self.get_entity(request, *args, **kwargs)
        attr_item_context = EntityAttributeItemEditContext( entity = entity )
        template_context = self.create_initial_template_context(
            attr_item_context= attr_item_context,
        )
        return self.modal_response( request, template_context )
    
    def post( self, request,*args, **kwargs ):
        entity = self.get_entity(request, *args, **kwargs)
        attr_item_context = EntityAttributeItemEditContext( entity = entity )
        return self.post_attribute_form(
            request = request,
            attr_item_context = attr_item_context,
        )


class EntityAttributeUploadView( View, EntityViewMixin, AttributeEditViewMixin ):

    def post( self, request,*args, **kwargs ):
        entity = self.get_entity( request, *args, **kwargs )
        attr_item_context = EntityAttributeItemEditContext(entity)
        return self.post_upload(
            request = request,
            attr_item_context = attr_item_context,
        )


class EntityAttributeHistoryInlineView( View, AttributeEditViewMixin ):
    """View for displaying EntityAttribute history inline within the edit modal."""

    def get( self,
             request      : HttpRequest,
             entity_id    : int,
             attribute_id : int,
             *args        : Any,
             **kwargs     : Any          ) -> HttpResponse:
        # Validate that the attribute belongs to this entity for security
        try:
            attribute = EntityAttribute.objects.select_related('entity').get(
                pk = attribute_id, entity_id = entity_id )
        except EntityAttribute.DoesNotExist:
            return page_not_found_response(request, "Attribute not found.")

        attr_item_context = EntityAttributeItemEditContext( entity = attribute.entity )
        return self.get_history(
            request = request,
            attribute = attribute,
            attr_item_context = attr_item_context,
        )


class EntityAttributeRestoreInlineView( View, AttributeEditViewMixin ):
    """View for restoring EntityAttribute values from history within the edit modal."""
    
    def get( self,
             request      : HttpRequest,
             entity_id    : int,
             attribute_id : int,
             history_id   : int,
             *args        : Any,
             **kwargs     : Any          ) -> HttpResponse:
        """ Need to do restore in a GET since nested in main form and cannot have a form in a form """

        try:
            attribute = EntityAttribute.objects.select_related('entity').get(
                pk = attribute_id, entity_id = entity_id )
        except EntityAttribute.DoesNotExist:
            return page_not_found_response(request, "Attribute not found.")

        attr_item_context = EntityAttributeItemEditContext( entity = attribute.entity )
        return self.post_restore(
            request = request,
            attribute = attribute,
            history_id = history_id,
            attr_item_context = attr_item_context,
        )
