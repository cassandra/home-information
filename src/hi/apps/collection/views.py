import logging

from django.core.exceptions import BadRequest
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views.generic import View

from hi.apps.common.utils import is_ajax
from hi.apps.location.location_manager import LocationManager

from hi.enums import ViewType
from hi.exceptions import ForceSynchronousException
from hi.hi_async_view import HiSideView
from hi.hi_grid_view import HiGridView

from .collection_manager import CollectionManager
from .models import Collection
from .view_mixin import CollectionViewMixin

logger = logging.getLogger(__name__)


class CollectionViewDefaultView( View ):

    def get(self, request, *args, **kwargs):

        collection = self._get_default_collection( request )
        redirect_url = reverse(
            'collection_view',
            kwargs = { 'collection_id': collection.id }
        )
        return HttpResponseRedirect( redirect_url )

    def _get_default_collection( self, request ):
        try:
            collection = CollectionManager().get_default_collection( request = request )
        except Collection.DoesNotExist:
            raise BadRequest( 'No collections defined.' )

        request.view_parameters.view_type = ViewType.COLLECTION
        request.view_parameters.update_collection( collection )
        request.view_parameters.to_session( request )
        return collection
    
    
class CollectionViewView( HiGridView, CollectionViewMixin ):

    def get_main_template_name( self ) -> str:
        return 'collection/panes/collection_view.html'

    def get_main_template_context( self, request, *args, **kwargs ):
        collection = self.get_collection( request, *args, **kwargs )

        if self.should_force_sync_request(
                request = request,
                next_view_type = ViewType.COLLECTION,
                next_id = collection.id ):
            raise ForceSynchronousException()

        request.view_parameters.view_type = ViewType.COLLECTION
        request.view_parameters.update_collection( collection )
        request.view_parameters.to_session( request )

        collection_data = CollectionManager().get_collection_data(
            collection = collection,
            is_editing = request.view_parameters.is_editing,
        )
        
        context = collection_data.to_template_context()
        context['is_async_request'] = is_ajax( request )
        return context
    
    
class CollectionDetailsView( HiSideView, CollectionViewMixin ):

    def get_template_name( self ) -> str:
        return 'collection/panes/collection_details.html'
    
    def should_push_url( self ):
        return True
    
    def get_template_context( self, request, *args, **kwargs ):
        collection = self.get_collection( request, *args, **kwargs )
        
        current_location_view = None
        if request.view_parameters.view_type.is_location_view:
            current_location_view = LocationManager().get_default_location_view( request = request )

        collections_detail_data = CollectionManager().get_collection_details_data(
            collection = collection,
            location_view = current_location_view,
            is_editing = request.view_parameters.is_editing,
        )
        return collections_detail_data.to_template_context()
