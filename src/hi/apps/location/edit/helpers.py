from decimal import Decimal
from typing import List

from django.db import transaction
from django.http import HttpRequest

from hi.apps.collection.collection_manager import CollectionManager
from hi.apps.collection.models import (
    Collection,
    CollectionView,
)
from hi.apps.entity.delegation_manager import DelegationManager
from hi.apps.entity.entity_manager import EntityManager
from hi.apps.entity.models import (
    Entity,
    EntityView,
)
from hi.apps.location.models import Location, LocationView

from .transient_models import (
    EntityViewGroup,
    EntityViewItem,
    CollectionViewItem,
    CollectionViewGroup,
)


class LocationEditHelpers:

    @classmethod
    def create_entity_view_group_list( cls, location_view : LocationView ) -> List[EntityViewGroup]:

        entity_queryset = Entity.objects.all()
        
        entity_view_group_dict = dict()
        for entity in entity_queryset:
        
            exists_in_view = False
            for entity_view in entity.entity_views.all():
                if entity_view.location_view == location_view:
                    exists_in_view = True
                    break
                continue

            entity_view_item = EntityViewItem(
                entity = entity,
                exists_in_view = exists_in_view,
            )
            
            if entity.entity_type not in entity_view_group_dict:
                entity_view_group = EntityViewGroup(
                    location_view = location_view,
                    entity_type = entity.entity_type,
                )
                entity_view_group_dict[entity.entity_type] = entity_view_group
            entity_view_group_dict[entity.entity_type].item_list.append( entity_view_item )
            continue

        entity_view_group_list = list( entity_view_group_dict.values() )
        entity_view_group_list.sort( key = lambda item : item.entity_type.label )
        return entity_view_group_list

    @classmethod
    def create_collection_view_group( cls, location_view : LocationView ) -> CollectionViewGroup:

        collection_queryset = Collection.objects.all()
        
        collection_view_group = CollectionViewGroup(
            location_view = location_view,
        )
        for collection in collection_queryset:
        
            exists_in_view = False
            for collection_view in collection.collection_views.all():
                if collection_view.location_view == location_view:
                    exists_in_view = True
                    break
                continue

            collection_view_item = CollectionViewItem(
                collection = collection,
                exists_in_view = exists_in_view,
            )
            collection_view_group.item_list.append( collection_view_item )
            continue

        collection_view_group.item_list.sort( key = lambda item : item.collection.name )
        return collection_view_group

    @classmethod
    def toggle_entity_in_view( cls, entity : Entity, location_view : LocationView ) -> bool:

        try:
            cls.remove_entity_from_view( entity = entity, location_view = location_view )
            return False
        except EntityView.DoesNotExist:
            cls.add_entity_to_view( entity = entity, location_view = location_view )
            return True
        
    @classmethod
    def remove_entity_from_view( cls, entity : Entity, location_view : LocationView ):

        with transaction.atomic():
            EntityManager().remove_entity_view(
                entity = entity,
                location_view = location_view,
            )

            DelegationManager().remove_delegate_entities_from_view_if_needed(
                entity = entity,
                location_view = location_view,
            )
            
        return
    
    @classmethod
    def add_entity_to_view_by_id( cls, entity : Entity, location_view_id : int ):
        location_view = LocationView.objects.get( id = location_view_id )
        cls.add_entity_to_view( entity = entity, location_view = location_view )
        return
    
    @classmethod
    def add_entity_to_view( cls, entity : Entity, location_view : LocationView ):

        with transaction.atomic():
            # Only create delegate entities the first time an entity is added to a view.
            if not entity.entity_views.all().exists():
                delegate_entity_list = DelegationManager().get_delegate_entities_with_defaults(
                    entity = entity,
                )
            else:
                delegate_entity_list = DelegationManager().get_delegate_entities(
                    entity = entity,
                )

            _ = EntityManager().create_entity_view(
                entity = entity,
                location_view = location_view,
            )
                            
            for delegate_entity in delegate_entity_list:
                _ = EntityManager().create_entity_view(
                    entity = delegate_entity,
                    location_view = location_view,
                )
                continue
            
        return 
        
    @classmethod
    def toggle_collection_in_view( cls,
                                   collection              : Collection,
                                   location_view           : LocationView ) -> bool:

        try:
            cls.remove_collection_from_view( collection = collection, location_view = location_view )
            return False
            
        except CollectionView.DoesNotExist:
            cls.add_collection_to_view( collection = collection, location_view = location_view )
            return True
        
    @classmethod
    def remove_collection_from_view( cls,
                                     collection              : Collection,
                                     location_view           : LocationView ):
        with transaction.atomic():
            CollectionManager().remove_collection_view(
                collection = collection,
                location_view = location_view,
            )
        return
        
    @classmethod
    def add_collection_to_view_by_id( cls, collection : Collection, location_view_id : int ):
        location_view = LocationView.objects.get( id = location_view_id )
        cls.add_collection_to_view( collection = collection, location_view = location_view )
        return
    
    @classmethod
    def add_collection_to_view( cls,
                                collection              : Collection,
                                location_view           : LocationView ):
        
        with transaction.atomic():
            _ = CollectionManager().create_collection_view(
                collection = collection,
                location_view = location_view,
            )
        return
        
    @classmethod
    def set_location_view_order( cls, location_view_id_list  : List[int] ):

        item_id_to_order_id = {
            item_id: order_id for order_id, item_id in enumerate( location_view_id_list )
        }

        location_view_queryset = LocationView.objects.filter( id__in = location_view_id_list )
        with transaction.atomic():
            for location_view in location_view_queryset:
                location_view.order_id = item_id_to_order_id.get( location_view.id )
                location_view.save()
                continue
        return
    
