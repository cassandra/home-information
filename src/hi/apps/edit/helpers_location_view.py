from decimal import Decimal
from typing import List

from django.db import transaction

from hi.apps.collection.models import (
    Collection,
    CollectionView,
    CollectionPosition,
)
from hi.apps.entity.models import (
    Entity,
    EntityView,
    EntityPosition,
    EntityPath,
)
from hi.apps.location.models import LocationView

from .transient_models import (
    CollectionViewItem,
    CollectionViewGroup,
    EntityViewItem,
    EntityViewGroup,
)


class LocationViewEditHelpers:

    @classmethod
    def create_entity_view_group_list( cls, location_view : LocationView ) -> List[EntityViewItem]:

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
            entity_view = EntityView.objects.get(
                entity = entity,
                location_view = location_view,
            )
            entity_view.delete()
            return False
            
        except EntityView.DoesNotExist:
            cls.add_entity_to_view( entity = entity, location_view = location_view )
            return True
        
    @classmethod
    def add_entity_to_view( cls, entity : Entity, location_view : LocationView ):
        
        with transaction.atomic():
            # Need to make sure it has some visible representation in the view if none exists.
            if entity.entity_type.is_path:
                cls.add_entity_path_if_needed(
                    entity = entity,
                    location_view = location_view,
                )
            else:
                cls.add_entity_position_if_needed(
                    entity = entity,
                    location_view = location_view,
                )

            _ = EntityView.objects.create(
                entity = entity,
                location_view = location_view,
            )
        return 
        
    @classmethod
    def add_entity_position_if_needed( cls, entity : Entity, location_view : LocationView ) -> EntityPosition:
        assert not entity.entity_type.is_path

        try:
            _ = EntityPosition.objects.get(
                location = location_view.location,
                entity = entity,
            )
            return
        except EntityPosition.DoesNotExist:
            pass

        # Default display in middle of current view
        svg_x = location_view.svg_view_box.x + ( location_view.svg_view_box.width / 2.0 )
        svg_y = location_view.svg_view_box.y + ( location_view.svg_view_box.height / 2.0 )
        
        entity_position = EntityPosition.objects.create(
            entity = entity,
            location = location_view.location,
            svg_x = Decimal( svg_x ),
            svg_y = Decimal( svg_y ),
            svg_scale = Decimal( 1.0 ),
            svg_rotate = Decimal( 0.0 ),
        )
        return entity_position
    
    @classmethod
    def add_entity_path_if_needed( cls, entity : Entity, location_view : LocationView ) -> EntityPath:
        assert entity.entity_type.is_path

        try:
            _ = EntityPath.objects.get(
                location = location_view.location,
                entity = entity,
            )
            return
        except EntityPath.DoesNotExist:
            pass

        # Default display a line in middle of current view with length 10% of viewbox width
        length = location_view.svg_view_box.width / 10.0
        center_x = location_view.svg_view_box.x + ( location_view.svg_view_box.width / 2.0 )
        center_y = location_view.svg_view_box.y + ( location_view.svg_view_box.height / 2.0 )
        start_x = center_x - ( length / 2.0 )
        start_y = center_y
        end_x = start_x + length
        end_y = start_y
        
        svg_path = f'M {start_x},{start_y} L {end_x},{end_y}'

        entity_path = EntityPath.objects.create(
            entity = entity,
            location = location_view.location,
            svg_path = svg_path,
        )
        return entity_path
        
    @classmethod
    def toggle_collection_in_view( cls,
                                   collection              : Collection,
                                   location_view           : LocationView,
                                   add_position_if_needed  : bool ) -> bool:

        try:
            collection_view = CollectionView.objects.get(
                collection = collection,
                location_view = location_view,
            )
            collection_view.delete()
            return False
            
        except CollectionView.DoesNotExist:
            cls.add_collection_to_view(
                collection = collection,
                location_view = location_view,
                add_position_if_needed = add_position_if_needed,
            )
            return True
        
    @classmethod
    def add_collection_to_view( cls,
                                collection              : Collection,
                                location_view           : LocationView,
                                add_position_if_needed  : bool ):
        
        with transaction.atomic():
            if add_position_if_needed:
                cls.add_collection_position_if_needed(
                    collection = collection,
                    location_view = location_view,
                )
            _ = CollectionView.objects.create(
                collection = collection,
                location_view = location_view,
            )
        return
        
    @classmethod
    def add_collection_position_if_needed( cls,
                                           collection : Collection,
                                           location_view : LocationView ) -> CollectionPosition:
        try:
            _ = CollectionPosition.objects.get(
                location = location_view.location,
                collection = collection,
            )
            return
        except CollectionPosition.DoesNotExist:
            pass

        # Default display in middle of current view
        svg_x = location_view.svg_view_box.x + ( location_view.svg_view_box.width / 2.0 )
        svg_y = location_view.svg_view_box.y + ( location_view.svg_view_box.height / 2.0 )
        
        collection_position = CollectionPosition.objects.create(
            collection = collection,
            location = location_view.location,
            svg_x = Decimal( svg_x ),
            svg_y = Decimal( svg_y ),
            svg_scale = Decimal( 1.0 ),
            svg_rotate = Decimal( 0.0 ),
        )
        return collection_position
    
