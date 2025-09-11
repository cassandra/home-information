import logging
from typing import Any

from django.core.exceptions import BadRequest
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import reverse
from django.views.generic import View

from hi.apps.common.utils import is_ajax
import hi.apps.common.antinode as antinode

from hi.apps.attribute.view_mixins import AttributeEditViewMixin
from hi.apps.control.one_click_control_service import (
    OneClickControlService,
    OneClickControlNotSupportedException,
)
from hi.apps.entity.models import Entity
from hi.apps.entity.view_mixins import EntityViewMixin
from hi.apps.monitor.status_display_manager import StatusDisplayManager
from hi.enums import ItemType, ViewType
from hi.exceptions import ForceSynchronousException
from hi.hi_async_view import HiModalView
from hi.hi_grid_view import HiGridView
from hi.views import page_not_found_response

from .enums import LocationViewType
from .location_attribute_edit_context import LocationAttributeItemEditContext
from .location_manager import LocationManager
from .models import LocationView, LocationAttribute
from .view_mixins import LocationViewMixin

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


class LocationItemStatusView( View, EntityViewMixin ):

    def get(self, request, *args, **kwargs):
        try:
            ( item_type, item_id ) = ItemType.parse_from_dict( kwargs )
        except ValueError:
            raise BadRequest( 'Bad item id.' )
        
        if item_type == ItemType.ENTITY:
            entity = self.get_entity( request, entity_id = item_id )
            return self._handle_entity( request = request, entity = entity )
    
        elif item_type == ItemType.COLLECTION:
            url = reverse( 'collection_view', kwargs = { 'collection_id': item_id } )
            return HttpResponseRedirect( url )

        raise BadRequest( f'Unknown item type "{item_type}".' )
        
    def _handle_entity(self, request : HttpRequest, entity : Entity ):
        
        location_view_id = request.view_parameters.location_view_id
        location_view = LocationView.objects.get( id = location_view_id )

        if location_view.location_view_type == LocationViewType.AUTOMATION:
            try:
                logger.debug( f'Trying one-click: {entity}' )
                controller_outcome = OneClickControlService().execute_one_click_control(
                    entity = entity,
                    location_view_type = location_view.location_view_type,
                )
                if controller_outcome.has_errors:
                    logger.info( f'Problem handling click for : {entity}' )
                    return antinode.response()
                
                override_sensor_value = controller_outcome.new_value
                StatusDisplayManager().add_entity_state_value_override(
                    entity_state = controller_outcome.controller.entity_state,
                    override_value = override_sensor_value,
                )




                
                return antinode.response()
            
            except OneClickControlNotSupportedException as e:
                # Fall back to status modal when one-click control is not supported
                logger.debug( f'One-click failed: {e}' )
                pass
            
        url = reverse( 'entity_status', kwargs = { 'entity_id': entity.id } )
        return HttpResponseRedirect( url )

        
class LocationEditView( HiModalView, LocationViewMixin, AttributeEditViewMixin ):
    """
    This view uses a dual response pattern:
    - get(): Returns full modal using standard modal_response()
    - post(): Returns antinode fragments for async DOM updates
    
    Business logic is delegated to specialized handler classes following
    the "keep views simple" design philosophy.
    """
    
    def get_template_name(self) -> str:
        return 'location/modals/location_edit.html'
    
    def get( self, request,*args, **kwargs ):
        location = self.get_location(request, *args, **kwargs)
        attr_item_context = LocationAttributeItemEditContext( location = location )
        template_context = self.create_initial_template_context(
            attr_item_context= attr_item_context,
        )
        return self.modal_response( request, template_context )
    
    def post( self, request,*args, **kwargs ):
        location = self.get_location(request, *args, **kwargs)
        attr_item_context = LocationAttributeItemEditContext( location = location )
        return self.post_attribute_form(
            request = request,
            attr_item_context = attr_item_context,
        )

    
class LocationAttributeUploadView( View, LocationViewMixin, AttributeEditViewMixin ):

    def post( self, request,*args, **kwargs ):
        location = self.get_location( request, *args, **kwargs )
        attr_item_context = LocationAttributeItemEditContext( location = location )
        return self.post_upload(
            request = request,
            attr_item_context = attr_item_context,
        )


class LocationAttributeHistoryInlineView( View, AttributeEditViewMixin ):
    """View for displaying LocationAttribute history inline within the edit modal."""

    def get( self,
             request       : HttpRequest,
             location_id   : int,
             attribute_id  : int,
             *args         : Any,
             **kwargs      : Any          ) -> HttpResponse:
        # Validate that the attribute belongs to this location for security
        try:
            attribute = LocationAttribute.objects.select_related('location').get(
                pk = attribute_id, location_id = location_id
            )
        except LocationAttribute.DoesNotExist:
            return page_not_found_response(request, "Attribute not found.")

        attr_item_context = LocationAttributeItemEditContext( location = attribute.location )

        return self.get_history(
            request = request,
            attribute = attribute,
            attr_item_context = attr_item_context,
        )

    
class LocationAttributeRestoreInlineView( View, AttributeEditViewMixin ):
    """View for restoring LocationAttribute values from history within the edit modal."""
    
    def get( self,
             request       : HttpRequest,
             location_id   : int,
             attribute_id  : int,
             history_id    : int,
             *args         : Any,
             **kwargs      : Any          ) -> HttpResponse:
        """ Need to do restore in a GET since nested in main form and cannot have a form in a form """
        try:
            attribute = LocationAttribute.objects.select_related('location').get(
                pk = attribute_id, location_id = location_id
            )
        except LocationAttribute.DoesNotExist:
            return page_not_found_response(request, "Attribute not found.")

        attr_item_context = LocationAttributeItemEditContext( location = attribute.location )

        return self.post_restore(
            request = request,
            attribute = attribute,
            history_id = history_id,
            attr_item_context = attr_item_context,
        )
