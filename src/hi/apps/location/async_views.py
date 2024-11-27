import logging

from django.core.exceptions import BadRequest
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views.generic import View

from hi.enums import ItemType
from hi.hi_async_view import HiSideView

from .transient_models import LocationEditData, LocationViewEditData
from .view_mixin import LocationViewMixin

logger = logging.getLogger(__name__)


class LocationViewDetailsView( HiSideView, LocationViewMixin ):

    def get_template_name( self ) -> str:
        return 'location/panes/location_details.html'

    def should_push_url( self ):
        return True
    
    def get_template_context( self, request, *args, **kwargs ):
        location_view = self.get_location_view( request, *args, **kwargs )

        location_edit_data = LocationEditData(
            location = location_view.location,
        )
        location_view_edit_data = LocationViewEditData(
            location_view = location_view,
        )
        context = location_edit_data.to_template_context()
        context.update( location_view_edit_data.to_template_context() )
        return context


class LocationItemInfoView( View ):

    def get(self, request, *args, **kwargs):
        try:
            ( item_type, item_id ) = ItemType.parse_from_dict( kwargs )
        except ValueError:
            raise BadRequest( request, message = 'Bad item id.' )
        
        if item_type == ItemType.ENTITY:
            redirect_url = reverse( 'entity_info', kwargs = { 'entity_id': item_id } )
            return HttpResponseRedirect( redirect_url )
    
        if item_type == ItemType.COLLECTION:
            redirect_url = reverse( 'collection_view', kwargs = { 'collection_id': item_id } )
            return HttpResponseRedirect( redirect_url )

        raise BadRequest( 'Unknown item type "{item_type}".' )


class LocationItemDetailsView( View ):

    def get(self, request, *args, **kwargs):
        try:
            ( item_type, item_id ) = ItemType.parse_from_dict( kwargs )
        except ValueError:
            raise BadRequest( request, message = 'Bad item id.' )
        
        if item_type == ItemType.ENTITY:
            redirect_url = reverse( 'entity_details', kwargs = { 'entity_id': item_id } )
            return HttpResponseRedirect( redirect_url )
    
        if item_type == ItemType.COLLECTION:
            redirect_url = reverse( 'collection_details', kwargs = { 'collection_id': item_id } )
            return HttpResponseRedirect( redirect_url )

        raise BadRequest( 'Unknown item type "{item_type}".' )
