from hi.apps.common.singleton import Singleton
from hi.apps.entity.models import Entity

from .collection_data import CollectionData
from .models import Collection, CollectionEntity


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

    def create_collection_entity( self,
                                  entity      : Entity,
                                  collection  : Collection ) -> CollectionEntity:
        
        last_item = CollectionEntity.objects.order_by( '-order_id' ).first()
        return CollectionEntity.objects.create(
            entity = entity,
            collection = collection,
            order_id = last_item.order_id + 1,
        )

    def remove_collection_entity( self,
                                  entity      : Entity,
                                  collection  : Collection ) -> bool:
        try:
            collection_entity = CollectionEntity.objects.get( entity = entity, collection = collection )
            collection_entity.delete()
            return True
        except CollectionEntity.DoesNotExist:
            return False
