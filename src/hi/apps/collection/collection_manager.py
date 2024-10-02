from hi.apps.common.singleton import Singleton

from .collection_data import CollectionData
from .models import Collection


class CollectionManager(Singleton):

    def __init_singleton__(self):
        return

    def get_collection_data( self, collection : Collection ):

        entity_list = list()
        for collection_entity in collection.entities.all().order_by('order_id'):
            entity_list.append( collection_entity.entity )
            continue

        return CollectionData(
            collection = collection,
            entity_list = entity_list,
        )
