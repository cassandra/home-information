from django.core.exceptions import BadRequest
from django.http import Http404, HttpRequest
from django.template.loader import get_template

import hi.apps.common.antinode as antinode
from hi.apps.location.location_manager import LocationManager
from hi.apps.location.models import Location, LocationView
from hi.apps.location.transient_models import LocationEditData, LocationViewEditData

from hi.constants import DIVID


class LocationViewMixin:

    LOCATION_VIEW_TEMPLATE_NAME = 'location/panes/location_view.html'
    
    def get_location( self, request, *args, **kwargs ) -> Location:
        """ Assumes there is a required location_id in kwargs """
        try:
            location_id = int( kwargs.get( 'location_id' ))
        except (TypeError, ValueError):
            raise BadRequest( 'Invalid location id.' )
        try:
            return LocationManager().get_location(
                request = request,
                location_id = location_id,
            )
        except Location.DoesNotExist:
            raise Http404( request )
 
    def get_location_view( self, request, *args, **kwargs ) -> LocationView:
        """ Assumes there is a required location_view_id in kwargs """
        try:
            location_view_id = int( kwargs.get( 'location_view_id' ))
        except (TypeError, ValueError):
            raise BadRequest( 'Invalid location_view id.' )
        try:
            return LocationManager().get_location_view(
                request = request,
                location_view_id = location_view_id,
            )
        except LocationView.DoesNotExist:
            raise Http404( request )
           
    def location_edit_response(
            self,
            request                         : HttpRequest,
            location_edit_data              : LocationEditData,
            status_code                     : int                                = 200 ):

        context = location_edit_data.to_template_context()
        template = get_template( 'location/edit/panes/location_edit.html' )
        content = template.render( context, request = request )
        return antinode.response(
            insert_map = {
                DIVID['LOCATION_EDIT_PANE']: content,
            },
            status = status_code,
        )
    
    def location_view_edit_response(
            self,
            request                  : HttpRequest,
            location_view_edit_data  : LocationViewEditData,
            status_code              : int                         = 200 ):

        context = location_view_edit_data.to_template_context()
        template = get_template( 'location/edit/panes/location_view_edit.html' )
        content = template.render( context, request = request )
        return antinode.response(
            insert_map = {
                DIVID['LOCATION_VIEW_EDIT_PANE']: content,
            },
            status = status_code,
        )
        
