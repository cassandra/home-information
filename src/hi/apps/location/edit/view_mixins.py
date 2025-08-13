from django.http import HttpRequest
from django.template.loader import get_template

import hi.apps.common.antinode as antinode
from hi.apps.location.transient_models import LocationEditData, LocationViewEditData

from hi.constants import DIVID


class LocationEditViewMixin:

    def location_edit_response(
            self,
            request                         : HttpRequest,
            location_edit_data              : LocationEditData,
            status_code                     : int                                = 200 ):

        context = location_edit_data.to_template_context()
        if request.view_parameters.is_editing:
            template = get_template( 'location/edit/panes/location_edit.html' )
            content = template.render( context, request = request )
            return antinode.response(
                insert_map = {
                    DIVID['LOCATION_EDIT_PANE']: content,
                },
                status = status_code,
            )
        return antinode.modal_from_template(
            request = request,
            template_name = 'location/modals/location_edit.html',
            context = context,
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
        
