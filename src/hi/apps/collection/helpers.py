from hi.apps.location.models import Location

from .models import Collection, CollectionPosition


class CollectionHelpers:

    @classmethod
    def get_collection_position( cls,
                                 collection_id  : int,
                                 location       : Location ) -> CollectionPosition:
        try:
            collection = Collection.objects.get( id = collection_id )
        except Collection.DoesNotExist:
            return None
        
        collection_position = CollectionPosition.objects.filter(
            collection = collection,
            location = location,
        ).first()
        if collection_position:
            return collection_position
        
        return CollectionPosition(
            collection = collection,
            location = location,
        )
    
