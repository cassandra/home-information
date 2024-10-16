import logging

from hi.apps.location.location_manager import LocationManager

from hi.hi_async_view import HiSideView

from .collection_manager import CollectionManager
from .view_mixin import CollectionViewMixin

logger = logging.getLogger(__name__)


class CollectionDetailsView( HiSideView, CollectionViewMixin ):

    def get_template_name( self ) -> str:
        return 'collection/panes/collection_details.html'
    
    def should_push_url( self ):
        return True
    
    def get_template_context( self, request, *args, **kwargs ):
        collection = self.get_collection( request, *args, **kwargs )
        
        current_location_view = LocationManager().get_default_location_view( request =request )
        collection_detail_data = CollectionManager().get_collection_detail_data(
            collection = collection,
            current_location_view = current_location_view,
            is_editing = request.is_editing,
        )
        
        return {
            'collection_detail_data': collection_detail_data,
        }
