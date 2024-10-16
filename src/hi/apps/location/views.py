import logging

from django.core.exceptions import BadRequest
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views.generic import View

from hi.apps.common.utils import is_ajax

from hi.enums import ViewType
from hi.exceptions import ForceRedirectException
from hi.hi_grid_view import HiGridView

from .location_manager import LocationManager
from .models import Location, LocationView
from .view_mixin import LocationViewMixin

logger = logging.getLogger(__name__)


class LocationViewDefaultView( View ):

    def get(self, request, *args, **kwargs):

        try:
            location_view = self._get_default_location_view( request )
            redirect_url = reverse(
                'location_view',
                kwargs = { 'location_view_id': location_view.id }
            )
        except Location.DoesNotExist:
            redirect_url = reverse( 'start' )
            
        return HttpResponseRedirect( redirect_url )

    def _get_default_location_view( self, request ):
        try:
            location_view = LocationManager().get_default_location_view( request = request )
        except LocationView.DoesNotExist:
            raise BadRequest( 'No views and no locations defined.' )

        request.view_parameters.view_type = ViewType.LOCATION_VIEW
        request.view_parameters.update_location_view( location_view )
        request.view_parameters.to_session( request )
        return location_view

    
class LocationViewView( HiGridView, LocationViewMixin ):

    def get_main_template_name( self ) -> str:
        return 'location/location_view.html'

    def get_template_context( self, request, *args, **kwargs ):
        location_view = self.get_location_view( request, *args, **kwargs )

        # Remember last location view chosen
        view_type_changed = bool( request.view_parameters.view_type != ViewType.LOCATION_VIEW )
        view_id_changed = bool( request.view_parameters.location_view_id != location_view.id )

        request.view_parameters.view_type = ViewType.LOCATION_VIEW
        request.view_parameters.update_location_view( location_view )
        request.view_parameters.to_session( request )

        # When in edit mode, a location view change needs a full
        # synchronous page load to ensure any front-end editing state and
        # views are invalidated. Else, the editing state and edit side
        # panel will be invalid for the new view.
        #
        if ( request.is_editing
             and is_ajax( request )
             and ( view_type_changed or view_id_changed )):
            redirect_url = reverse( 'location_view', kwargs = kwargs )
            raise ForceRedirectException( url = redirect_url )
        
        location_view_data = LocationManager().get_location_view_data(
            location_view = location_view,
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
            kwargs = { 'location_id': location_view.id }
        )
        return HttpResponseRedirect( redirect_url )
