import logging

from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views.generic import View

import hi.apps.common.antinode as antinode
from hi.apps.common.utils import is_ajax
from hi.enums import ViewType
from hi.hi_grid_view import HiGridView
from hi.views import bad_request_response

from .location_view_manager import LocationViewManager
from .models import Location, LocationView

logger = logging.getLogger(__name__)


class LocationViewDefaultView( View ):

    def get(self, request, *args, **kwargs):

        location_view = self._get_default_location_view( request )
        redirect_url = reverse(
            'location_view',
            kwargs = { 'id': location_view.id }
        )
        return HttpResponseRedirect( redirect_url )

    def _get_default_location_view( self, request ):
        if request.view_parameters.location_view:
            return request.view_parameters.location_view

        location = Location.objects.order_by( 'order_id' ).first()
        if not location:
            return bad_request_response( request, message = 'No locations defined.' )
        
        location_view = location.views.order_by( 'order_id' ).first()
        if not location_view:
            return bad_request_response( request, message = 'No views defined for this location.' )

        request.view_parameters.view_type = ViewType.LOCATION_VIEW
        request.view_parameters.location_view_id = location_view.id
        request.view_parameters.to_session( request )
        return location_view

    
class LocationViewView( HiGridView ):

    def get(self, request, *args, **kwargs):

        location_view_id = kwargs.get('id')
        try:
            location_view = LocationView.objects.select_related(
                'location' ).get( id = location_view_id )
        except LocationView.DoesNotExist:
            message = f'Location view "{location_view_id}" does not exist.'
            logger.warning( message )
            return bad_request_response( request, message = message )

        # Remember last location view chosen
        request.view_parameters.view_type = ViewType.LOCATION_VIEW
        request.view_parameters.location_view_id = location_view.id
        request.view_parameters.to_session( request )

        # When in edit mode, a location view change needs a full
        # synchronous page load to ensure any front-end editing state and
        # views are invalidated. Else, the editing state and edit side
        # panel will be invalid for the new view.
        #
        if is_ajax( request ) and request.view_parameters.view_mode.should_reload_on_view_change:
            sync_url = reverse( 'location_view', kwargs = kwargs )
            return antinode.redirect_response( url = sync_url )
        
        location_view_data = LocationViewManager().get_location_view_data(
            location_view = location_view,
        )
        context = {
            'is_async_request': is_ajax( request ),
            'location_view_data': location_view_data,
        }
        return self.hi_grid_response( 
            request = request,
            context = context,
            main_template_name = 'location/location_view.html',
            push_url_name = 'location_view',
            push_url_kwargs = kwargs,
        )
