import logging
from typing import Any

from django.core.exceptions import BadRequest
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import reverse
from django.views.generic import View

from hi.apps.common.utils import is_ajax

from hi.apps.attribute.view_mixins import AttributeEditViewMixin
from hi.apps.control.controller_manager import ControllerManager
from hi.apps.entity.models import Entity
from hi.apps.entity.enums import EntityStateValue
from hi.apps.monitor.status_display_manager import StatusDisplayManager
from hi.enums import ItemType, ViewType
from hi.exceptions import ForceSynchronousException
from hi.hi_async_view import HiModalView
from hi.hi_grid_view import HiGridView
from hi.views import page_not_found_response

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


class LocationItemStatusView( View ):

    # Mapping for determining toggle values for binary entity states
    TOGGLE_VALUE_MAP = {
        EntityStateValue.OFF: EntityStateValue.ON,
        EntityStateValue.ON: EntityStateValue.OFF,
        EntityStateValue.CLOSED: EntityStateValue.OPEN,
        EntityStateValue.OPEN: EntityStateValue.CLOSED,
        EntityStateValue.LOW: EntityStateValue.HIGH,
        EntityStateValue.HIGH: EntityStateValue.LOW,
        EntityStateValue.IDLE: EntityStateValue.ACTIVE,
        EntityStateValue.ACTIVE: EntityStateValue.IDLE,
        EntityStateValue.DISCONNECTED: EntityStateValue.CONNECTED,
        EntityStateValue.CONNECTED: EntityStateValue.DISCONNECTED,
    }

    def get(self, request, *args, **kwargs):
        try:
            ( item_type, item_id ) = ItemType.parse_from_dict( kwargs )
        except ValueError:
            raise BadRequest( 'Bad item id.' )
        
        if item_type == ItemType.ENTITY:
            return self._handle_entity_item( request, item_id )
    
        if item_type == ItemType.COLLECTION:
            redirect_url = reverse( 'collection_view', kwargs = { 'collection_id': item_id } )
            return HttpResponseRedirect( redirect_url )

        raise BadRequest( f'Unknown item type "{item_type}".' )

    def _handle_entity_item( self, request, entity_id ):
        """Handle entity item click with one-click control logic."""
        try:
            entity = Entity.objects.get( id = entity_id )
        except Entity.DoesNotExist:
            raise BadRequest( f'Entity {entity_id} not found.' )

        # Check if we have LocationView context for one-click behavior
        location_view = self._get_current_location_view( request )
        if location_view:
            controller_result = self._attempt_one_click_control( entity, location_view )
            if controller_result is not None:
                return controller_result

        # Fallback to existing entity status modal behavior
        redirect_url = reverse( 'entity_status', kwargs = { 'entity_id': entity_id } )
        return HttpResponseRedirect( redirect_url )

    def _get_current_location_view( self, request ):
        """Get the current LocationView from request context."""
        location_view_id = None
        
        # Try to get from view_parameters first
        try:
            if hasattr( request, 'view_parameters' ) and request.view_parameters.view_type == ViewType.LOCATION_VIEW:
                location_view_id = getattr( request.view_parameters, 'location_view_id', None )
        except AttributeError:
            pass
        
        # Fallback to session
        if not location_view_id:
            try:
                session_view_type = request.session.get( 'view_type' )
                if session_view_type == str( ViewType.LOCATION_VIEW ):
                    location_view_id = request.session.get( 'location_view_id' )
            except AttributeError:
                pass
        
        # Get LocationView object if we have an ID
        if location_view_id:
            try:
                return LocationView.objects.get( id = location_view_id )
            except LocationView.DoesNotExist:
                pass
                
        return None

    def _attempt_one_click_control( self, entity, location_view ):
        """Attempt to execute one-click control based on LocationViewType priorities."""
        location_view_type = location_view.location_view_type
        if not location_view_type or not location_view_type.entity_state_type_priority_list:
            return None

        # Find the highest priority controllable EntityState
        controllable_state = self._find_controllable_entity_state( entity, location_view_type )
        if not controllable_state:
            return None

        # Get the first controller for this state (can be enhanced later for multiple controllers)
        controller = controllable_state.controllers.first()
        if not controller:
            return None

        # Determine the control value to use
        control_value = self._determine_control_value( controllable_state, controller )

        try:
            # Execute the control action
            control_result = ControllerManager().do_control(
                controller = controller,
                control_value = control_value,
            )

            if not control_result.has_errors:
                # Update status display manager with immediate feedback
                StatusDisplayManager().add_entity_state_value_override(
                    entity_state = controllable_state,
                    override_value = control_value,
                )

            # Return success response - could be enhanced to return JSON for AJAX requests
            # For now, redirect to entity status to show the result
            redirect_url = reverse( 'entity_status', kwargs = { 'entity_id': entity.id } )
            return HttpResponseRedirect( redirect_url )

        except Exception as e:
            logger.error( f'One-click control failed for entity {entity.id}: {e}' )
            # Fall back to status modal on error
            return None

    def _find_controllable_entity_state( self, entity, location_view_type ):
        """Find the highest priority EntityState that has controllers."""
        priority_list = location_view_type.entity_state_type_priority_list
        
        for state_type in priority_list:
            for entity_state in entity.entity_states.all():
                if entity_state.entity_state_type == state_type:
                    if entity_state.controllers.exists():
                        return entity_state
        return None

    def _determine_control_value( self, entity_state, controller ):
        """Determine what control value to send based on current state."""
        # Get current sensor response to determine current state
        try:
            sensor_response = StatusDisplayManager().get_latest_sensor_response( entity_state )
            if sensor_response:
                current_value_str = sensor_response.value_str
                try:
                    current_value = EntityStateValue.from_name_safe( current_value_str )
                    # Try to toggle to opposite value
                    if current_value in self.TOGGLE_VALUE_MAP:
                        return str( self.TOGGLE_VALUE_MAP[current_value] )
                except ( ValueError, AttributeError ):
                    pass
        except Exception:
            pass

        # Fallback: Use controller's entity state type to determine a reasonable default
        entity_state_type = entity_state.entity_state_type
        
        # Use common defaults for known controllable types
        if entity_state_type.name == 'ON_OFF':
            return str( EntityStateValue.ON )
        elif entity_state_type.name == 'OPEN_CLOSE':
            return str( EntityStateValue.OPEN )
        elif entity_state_type.name == 'HIGH_LOW':
            return str( EntityStateValue.HIGH )
        
        # For other types, try to get first choice from controller
        choices = controller.choices
        if choices:
            return choices[0][0]  # Return first choice key
            
        return 'unknown'


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
