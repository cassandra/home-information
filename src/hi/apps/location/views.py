import logging

from django.core.exceptions import BadRequest
from django.http import HttpResponseRedirect, HttpResponseNotAllowed
from django.urls import reverse
from django.views.generic import View

from hi.apps.common.utils import is_ajax

from hi.enums import ItemType, ViewType
from hi.exceptions import ForceSynchronousException
from hi.hi_async_view import HiSideView
from hi.hi_grid_view import HiGridView
from hi.apps.attribute.views import BaseAttributeHistoryView, BaseAttributeRestoreView

from .location_manager import LocationManager
from .models import LocationView, LocationAttribute
from .transient_models import LocationEditData, LocationViewEditData
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


class LocationDetailsView( HiSideView, LocationViewMixin ):

    def get_template_name( self ) -> str:
        return 'location/panes/location_edit_mode_panel.html'

    def should_push_url( self ):
        return True
    
    def get_template_context( self, request, *args, **kwargs ):
        location = self.get_location( request, *args, **kwargs )
        location_edit_data = LocationEditData(
            location = location,
        )
        return location_edit_data.to_template_context()
    
    def post( self, request, *args, **kwargs ):
        return HttpResponseNotAllowed(['GET'])


class LocationViewDetailsView( HiSideView, LocationViewMixin ):

    def get_template_name( self ) -> str:
        return 'location/panes/location_view_details.html'

    def should_push_url( self ):
        return True
    
    def get_template_context( self, request, *args, **kwargs ):
        location_view = self.get_location_view( request, *args, **kwargs )
        location_view_edit_data = LocationViewEditData(
            location_view = location_view,
        )
        return location_view_edit_data.to_template_context()
    
    def post( self, request, *args, **kwargs ):
        return HttpResponseNotAllowed(['GET'])


class LocationItemInfoView( View ):

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


class LocationItemDetailsView( View ):

    def get(self, request, *args, **kwargs):
        try:
            ( item_type, item_id ) = ItemType.parse_from_dict( kwargs )
        except ValueError:
            raise BadRequest( 'Bad item id.' )
        
        if item_type == ItemType.ENTITY:
            redirect_url = reverse( 'entity_details', kwargs = { 'entity_id': item_id } )
            return HttpResponseRedirect( redirect_url )
    
        if item_type == ItemType.COLLECTION:
            redirect_url = reverse( 'collection_details', kwargs = { 'collection_id': item_id } )
            return HttpResponseRedirect( redirect_url )

        raise BadRequest( f'Unknown item type "{item_type}".' )


class LocationAttributeHistoryView(BaseAttributeHistoryView):
    """View for displaying LocationAttribute history in a modal."""
    
    def get_attribute_model_class(self):
        return LocationAttribute
    
    def get_history_url_name(self):
        return 'location_attribute_history'
    
    def get_restore_url_name(self):
        return 'location_attribute_restore'


class LocationAttributeRestoreView(BaseAttributeRestoreView):
    """View for restoring LocationAttribute values from history."""
    
    def get_attribute_model_class(self):
        return LocationAttribute
