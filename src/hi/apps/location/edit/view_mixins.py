from django.http import HttpRequest
from django.template.loader import get_template

import hi.apps.common.antinode as antinode
from hi.apps.location.transient_models import LocationEditModeData, LocationViewEditModeData

from hi.constants import DIVID


class LocationEditViewMixin:

    def location_properties_response(
            self,
            request                         : HttpRequest,
            location_edit_data              : LocationEditModeData,
            status_code                     : int                                = 200 ):
        """Return sidebar response for location properties editing only (name, order_id, svg_view_box_str)"""
        context = location_edit_data.to_template_context()
        template = get_template( 'location/edit/panes/location_properties_edit.html' )
        content = template.render( context, request = request )
        return antinode.response(
            insert_map = {
                DIVID['LOCATION_PROPERTIES_PANE']: content,
            },
            status = status_code,
        )
        
    def location_view_edit_mode_response(
            self,
            request                  : HttpRequest,
            location_view_edit_data  : LocationViewEditModeData,
            status_code              : int                         = 200 ):

        context = location_view_edit_data.to_template_context()
        template = get_template( 'location/edit/panes/location_view_properties_edit.html' )
        content = template.render( context, request = request )
        return antinode.response(
            insert_map = {
                DIVID['LOCATION_VIEW_EDIT_PANE']: content,
            },
            status = status_code,
        )
        
