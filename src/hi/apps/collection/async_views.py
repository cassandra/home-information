import logging

from django.core.exceptions import BadRequest
from django.http import Http404

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
        collection_id = kwargs.get( 'collection_id' )
        if not collection_id:
            raise BadRequest( 'Missing collection id in request.' )
        try:
            collection = Collection.objects.get( id = collection_id )
        except Collection.DoesNotExist:
            raise Http404()

        current_location_view = None
        if request.view_parameters.view_type.is_location_view:
            current_location_view = request.view_parameters.location_view

        collection_detail_data = CollectionManager().get_collection_detail_data(
            collection = collection,
            current_location_view = current_location_view,
            is_editing = request.is_editing,
        )
        
        return {
            'collection_detail_data': collection_detail_data,
        }

    
    
