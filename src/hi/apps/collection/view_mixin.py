from django.core.exceptions import BadRequest
from django.http import Http404

from hi.apps.collection.collection_manager import CollectionManager
from hi.apps.collection.models import Collection


class CollectionViewMixin:

    def get_collection( self, request, *args, **kwargs ) -> Collection:
        """ Assumes there is a required collection_id in kwargs """
        try:
            collection_id = int( kwargs.get( 'collection_id' ))
        except (TypeError, ValueError):
            raise BadRequest( 'Invalid collection id.' )
        try:
            return CollectionManager().get_collection(
                request = request,
                collection_id = collection_id,
            )
        except Collection.DoesNotExist:
            raise Http404( request )
 
