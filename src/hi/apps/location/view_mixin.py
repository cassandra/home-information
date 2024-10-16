from django.core.exceptions import BadRequest
from django.http import Http404

from hi.apps.location.location_manager import LocationManager
from hi.apps.location.models import Location, LocationView


class LocationViewMixin:

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
           
