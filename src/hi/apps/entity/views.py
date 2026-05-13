import logging
from datetime import datetime
from typing import Any, Dict, Optional

from django.http import HttpRequest, HttpResponse
from django.views.generic import View

from hi.apps.common import datetimeproxy

from hi.apps.attribute.view_mixins import AttributeEditViewMixin
from hi.apps.attribute.edit_response_renderer import AttributeEditResponseRenderer
from hi.apps.control.controller_history_manager import ControllerHistoryManager
from hi.apps.control.transient_models import ControllerHistoryResponse
from hi.apps.monitor.status_display_manager import StatusDisplayManager
from hi.apps.sense.sensor_history_manager import SensorHistoryMixin
from hi.apps.sense.transient_models import SensorResponse

from hi.views import page_not_found_response
from hi.hi_async_view import HiModalView
from hi.apps.entity.edit.entity_type_transition_handler import EntityTypeTransitionHandler

from .entity_state_history import get_entity_state_history_page
from .models import Entity, EntityAttribute
from .transient_models import EntityStateHistoryData
from .view_mixins import EntityStateViewMixin, EntityViewMixin
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
        sensor_response_list_map = {
            sensor: [ SensorResponse.from_sensor_history( h ) for h in history_list ]
            for sensor, history_list in sensor_history_list_map.items()
        }
        controller_response_list_map = {
            controller: [ ControllerHistoryResponse.from_controller_history( h ) for h in history_list ]
            for controller, history_list in controller_history_list_map.items()
        }
        entity_state_history_data = EntityStateHistoryData(
            entity = entity,
            sensor_response_list_map = sensor_response_list_map,
            controller_response_list_map = controller_response_list_map,
        )
        context: Dict[str, Any] = entity_state_history_data.to_template_context()
        return self.modal_response( request, context )


class EntityStateMergedHistoryView( HiModalView, EntityStateViewMixin ):
    """Paginated per-EntityState merged history. The "History" anchor
    in the EntityStatus modal (both sensor and controller rows) and
    elsewhere lands here. Pagination is next/prev only, anchored on
    sensor observation timestamps with controller intents fetched in
    the same time range."""

    PAGE_SIZE = 25

    def get_template_name( self ) -> str:
        return 'entity/modals/entity_state_merged_history.html'

    def get( self, request, *args, **kwargs ):
        entity_state = self.get_entity_state( request, *args, **kwargs )

        before = _parse_iso_cursor( request.GET.get( 'before' ) )

        rows = get_entity_state_history_page(
            entity_state = entity_state,
            page_size = self.PAGE_SIZE,
            before = before,
        )

        # Multi-instrument source annotation surfaces only when the
        # state has more than one sensor or more than one controller,
        # i.e., when the row's instrument identity is ambiguous.
        multi_sensor = entity_state.sensors.count() > 1
        multi_controller = entity_state.controllers.count() > 1
        annotate_sources = multi_sensor or multi_controller

        # The oldest row's timestamp drives the "older" navigation
        # link; the cursor we paged from drives the "newer" link
        # back toward the most-recent page.
        older_cursor : Optional[ str ] = (
            datetimeproxy.datetime_to_iso_str( rows[ -1 ].timestamp )
            if rows else None
        )
        newer_cursor : Optional[ str ] = (
            datetimeproxy.datetime_to_iso_str( before )
            if before is not None else None
        )

        context = {
            'entity_state'      : entity_state,
            'history_rows'      : rows,
            'annotate_sources'  : annotate_sources,
            'older_cursor'      : older_cursor,
            'newer_cursor'      : newer_cursor,
        }
        return self.modal_response( request, context )


def _parse_iso_cursor( raw : Optional[ str ] ) -> Optional[ datetime ]:
    if not raw:
        return None
    try:
        return datetimeproxy.iso_str_to_datetime( raw )
    except ValueError:
        return None


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
        original_entity_type = entity.entity_type
        attr_item_context = EntityAttributeItemEditContext( entity = entity )
        response = self.post_attribute_form(
            request = request,
            attr_item_context = attr_item_context,
        )

        if response.status_code != 200:
            return response

        entity.refresh_from_db()
        entity_type_changed = bool( original_entity_type != entity.entity_type )
        if not entity_type_changed:
            return response

        transition_response = EntityTypeTransitionHandler().handle_entity_type_change(
            request = request,
            entity = entity,
        )
        if transition_response is None:
            return response

        return transition_response


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


class EntityAttributeRestoreDeletedInlineView( View ):
    """View for restoring soft-deleted EntityAttributes."""

    def get( self,
             request      : HttpRequest,
             entity_id    : int,
             attribute_id : int,
             *args        : Any,
             **kwargs     : Any          ) -> HttpResponse:
        try:
            attribute = EntityAttribute.deleted_objects.select_related('entity').get(
                pk = attribute_id,
                entity_id = entity_id,
            )
        except EntityAttribute.DoesNotExist:
            return page_not_found_response(request, "Deleted attribute not found.")

        attribute.restore_from_deleted()
        attr_item_context = EntityAttributeItemEditContext( entity = attribute.entity )
        renderer = AttributeEditResponseRenderer()
        return renderer.render_form_success_response(
            attr_item_context = attr_item_context,
            request = request,
            message = 'Attribute restored',
        )
