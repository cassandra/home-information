import urllib.parse

from django.core.exceptions import BadRequest
from django.http import Http404, HttpResponse
from django.urls import reverse

import hi.apps.common.antinode as antinode
from hi.apps.entity.models import Entity
from hi.apps.location.location_manager import LocationManager
from hi.apps.location.models import Location, LocationView
from hi.apps.monitor.display_data import EntityStateDisplayData
from hi.apps.monitor.status_display_manager import StatusDisplayManager
from hi.hi_async_view import HiSideView


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

    def redirect_to_location_edit_side_view( self, location : Location ) -> HttpResponse:
        """ Redirect to home with the location edit sidebar loaded alongside. """
        side_url = reverse( 'location_edit_mode', kwargs={ 'location_id': location.id } )
        redirect_url = (
            reverse( 'home' )
            + '?' + urllib.parse.urlencode({ HiSideView.SIDE_URL_PARAM_NAME: side_url })
        )
        return antinode.redirect_response( redirect_url )

    def get_entity_svg_update_response( self, entity : Entity ) -> HttpResponse:
        """ For updating a single entity in the location view via antinode response """

        entity_status_data = StatusDisplayManager().get_entity_status_data(
            entity = entity,
        )
        set_attributes_map = dict()
        for entity_state_status_data in entity_status_data.entity_state_status_data_list:
            status_display_data = EntityStateDisplayData(
                entity_state_status_data = entity_state_status_data,
            )
            attribute_dict = status_display_data.attribute_dict
            if not attribute_dict:
                continue
            state_id = status_display_data.entity_state.id
            # Mirror the polling-refresh dispatch contract documented
            # in ``entity_state_status.js``: elements opt into the
            # ``data-status`` hint (icon wrappers; see
            # ``location/panes/svg_icon_item.html``) for status-only
            # updates, or ``data-svg-style`` (path elements; see
            # ``location/panes/svg_path_item_*.html``) for the full
            # presentation attribute set. Icon wrappers get only the
            # ``status`` attribute so the parent <g>'s ``fill`` /
            # ``fill-opacity`` / ``stroke`` don't cascade into child
            # paths that depend on browser-default ``fill: black`` or
            # on full opacity. Path elements live on the element
            # being styled, so the full attribute set is the right
            # payload there.
            icon_selector = f'[data-state-id="{state_id}"][data-status]'
            path_selector = f'[data-state-id="{state_id}"][data-svg-style]'
            if 'status' in attribute_dict:
                set_attributes_map[ icon_selector ] = {
                    'status': attribute_dict[ 'status' ],
                }
            set_attributes_map[ path_selector ] = attribute_dict
            continue
        return antinode.response(
            set_attributes_map = set_attributes_map,
        )
        
