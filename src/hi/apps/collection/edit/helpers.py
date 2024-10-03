from typing import List

from django.db import transaction
from django.http import HttpRequest

from hi.apps.collection.enums import CollectionType
from hi.apps.collection.models import (
    Collection,
    CollectionEntity,
)
from hi.apps.entity.models import (
    Entity,
)

from .transient_models import (
    EntityCollectionItem,
    EntityCollectionGroup,
)


class CollectionEditHelpers:

    @classmethod
    def create_collection( cls,
                           request          : HttpRequest,
                           collection_type  : CollectionType,
                           name             : str          ) -> Collection:
        last_collection = Collection.objects.all().order_by( '-order_id' ).first()
        
        return Collection.objects.create(
            name = name,
            collection_type_str = str(collection_type),
            order_id = last_collection.order_id + 1,
        )
        
    @classmethod
    def create_entity_collection_group_list( cls, collection : Collection ) -> List[EntityCollectionGroup]:

        entity_queryset = Entity.objects.all()
        
        entity_collection_group_dict = dict()
        for entity in entity_queryset:
        
            exists_in_collection = False
            for collection_entity in entity.collections.all():
                if collection_entity.collection == collection:
                    exists_in_collection = True
                    break
                continue

            entity_collection_item = EntityCollectionItem(
                entity = entity,
                exists_in_collection = exists_in_collection,
            )
            
            if entity.entity_type not in entity_collection_group_dict:
                entity_collection_group = EntityCollectionGroup(
                    collection = collection,
                    entity_type = entity.entity_type,
                )
                entity_collection_group_dict[entity.entity_type] = entity_collection_group
            entity_collection_group_dict[entity.entity_type].item_list.append( entity_collection_item )
            continue

        entity_collection_group_list = list( entity_collection_group_dict.values() )
        entity_collection_group_list.sort( key = lambda item : item.entity_type.label )
        return entity_collection_group_list

    @classmethod
    def toggle_entity_in_collection( cls, entity : Entity, collection : Collection ) -> bool:

        try:
            collection_entity = CollectionEntity.objects.get(
                entity = entity,
                collection = collection,
            )
            collection_entity.delete()
            return False
            
        except CollectionEntity.DoesNotExist:
            last_item = CollectionEntity.objects.order_by( '-order_id' ).first()
            _ = CollectionEntity.objects.create(
                entity = entity,
                collection = collection,
                order_id = last_item.order_id + 1,
            )
            return True
        
    @classmethod
    def set_collection_entity_order( cls,
                                     collection_id   : int,
                                     entity_id_list  : List[int] ):
        item_id_to_order_id = {
            item_id: order_id for order_id, item_id in enumerate( entity_id_list )
        }
        
        collection_entity_queryset = CollectionEntity.objects.filter(
            collection_id = collection_id,
            entity_id__in = entity_id_list,
        )
        with transaction.atomic():
            for collection_entity in collection_entity_queryset:
                collection_entity.order_id = item_id_to_order_id.get( collection_entity.entity.id )
                collection_entity.save()
                continue
        return

    @classmethod
    def set_collection_order( cls, collection_id_list  : List[int] ):
        item_id_to_order_id = {
            item_id: order_id for order_id, item_id in enumerate( collection_id_list )
        }
        
        collection_queryset = Collection.objects.filter( id__in = collection_id_list )
        with transaction.atomic():
            for collection in collection_queryset:
                collection.order_id = item_id_to_order_id.get( collection.id )
                collection.save()
                continue
        return
    
