from django.core.exceptions import BadRequest
from django.http import Http404, HttpResponse

import hi.apps.common.antinode as antinode
from hi.apps.entity.models import Entity
from hi.apps.location.location_manager import LocationManager
from hi.apps.location.models import Location, LocationView
from hi.apps.monitor.status_display_data import StatusDisplayData
from hi.apps.monitor.status_display_manager import StatusDisplayManager


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

    def get_entity_svg_update_reponse( self, entity : Entity ) -> HttpResponse:
        """ For updating a single entity in the location view vis antinode reponse """

        entity_status_data = StatusDisplayManager().get_entity_status_data(
            entity = entity,
        )
        set_attributes_map = dict()
        for entity_state_status_data in entity_status_data.entity_state_status_data_list:
            status_display_data = StatusDisplayData(
                entity_state_status_data = entity_state_status_data,
            )
            selector = f'.{status_display_data.css_class}'
            set_attributes_map.update({
                selector: status_display_data.attribute_dict
            })
            continue
        return antinode.response(
            set_attributes_map = set_attributes_map,
        )
        
