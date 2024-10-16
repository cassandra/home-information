import logging

from django.core.exceptions import BadRequest
from django.http import Http404

from hi.apps.location.location_manager import LocationManager

from hi.hi_async_view import HiSideView

from .collection_manager import CollectionManager
from .models import Collection

logger = logging.getLogger(__name__)


class CollectionDetailsView( HiSideView ):

    def get_template_name( self ) -> str:
        return 'collection/panes/collection_details.html'
    
    def should_push_url( self ):
        return True
    
    def get_template_context( self, request, *args, **kwargs ):
        try:
            collection_id = int( kwargs.get( 'collection_id' ))
        except (TypeError, ValueError):
            raise BadRequest( 'Invalid location view id.' )
        try:
            collection = CollectionManager().get_collection(
                request = request,
                collection_id = collection_id,
            )
        except Collection.DoesNotExist:
            raise Http404( request )
        
        current_location_view = LocationManager().get_default_location_view( request =request )
        collection_detail_data = CollectionManager().get_collection_detail_data(
            collection = collection,
            current_location_view = current_location_view,
            is_editing = request.is_editing,
        )
        
        return {
            'collection_detail_data': collection_detail_data,
        }

    
    
