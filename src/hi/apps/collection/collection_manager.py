from decimal import Decimal
from typing import List

from django.db import transaction
from django.http import HttpRequest

from hi.apps.collection.edit.forms import CollectionPositionForm
from hi.apps.common.singleton import Singleton
from hi.apps.entity.enums import EntityGroupType
from hi.apps.entity.models import Entity
from hi.apps.location.models import Location, LocationView
from hi.apps.location.svg_item_factory import SvgItemFactory
from hi.apps.monitor.status_display_manager import StatusDisplayManager

from .models import (
    Collection,
    CollectionEntity,
    CollectionPath,
    CollectionPosition,
    CollectionView,
)
from .transient_models import (
    CollectionData,
    CollectionEditModeData,
    CollectionViewGroup,
    CollectionViewItem,
    EntityCollectionGroup,
    EntityCollectionItem,
)


class CollectionManager(Singleton):

    def __init_singleton__(self):
        return

    def get_collection( self, request : HttpRequest, collection_id : int ) -> Collection:
        """
        This should always be used to fetch from the database and never using
        the "objects" query interface. The view_parameters loads the
        current default Collection, so any out-of-band loading risks the
        cached view_parameters version to be different from the one
        loaded. Since so much of the app features revolve around the
        current collection, not having the default update can result in hard
        to detect issues.
        """
        current_collection = request.view_parameters.collection
        if current_collection and ( current_collection.id == int(collection_id) ):
            return current_collection
        return Collection.objects.get( id = collection_id )

    def get_default_collection( self, request : HttpRequest ) -> Collection:
        current_collection = request.view_parameters.collection
        if current_collection:
            return current_collection
        collection = Collection.objects.order_by( 'order_id' ).first()
        if collection:
            return collection
        raise Collection.DoesNotExist()
    
    def get_collection_data( self,
                             collection     : Collection,
                             is_editing     : bool ):

        collection_entity_list = list( collection.entities.all().order_by('order_id') )
        entity_list = [ x.entity for x in collection_entity_list ]
        entity_status_data_list = StatusDisplayManager().get_entity_status_data_list(
            entities = entity_list,
        )

        svg_item_factory = SvgItemFactory()
        for entity_status_data in entity_status_data_list:
            svg_icon_item = svg_item_factory.get_display_only_svg_icon_item(
                entity = entity_status_data.entity,
            )
            entity_status_data.display_only_svg_icon_item = svg_icon_item
            continue
        
        return CollectionData(
            collection = collection,
            entity_status_data_list = entity_status_data_list,
        )

    def create_collection_entity( self,
                                  entity      : Entity,
                                  collection  : Collection ) -> CollectionEntity:
        
        last_item = CollectionEntity.objects.order_by( '-order_id' ).first()
        if last_item:
            order_id = last_item.order_id + 1
        else:
            order_id = 0
        
        return CollectionEntity.objects.create(
            entity = entity,
            collection = collection,
            order_id = order_id,
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

    def create_collection_view( self, collection : Collection, location_view : LocationView ):

        with transaction.atomic():

            # Need to make sure it has some visible representation in the view if none exists.
            svg_item_type = SvgItemFactory().get_svg_item_type( collection )
            if svg_item_type.is_path:
                self.add_collection_path_if_needed(
                    collection = collection,
                    location_view = location_view,
                    is_path_closed = svg_item_type.is_path_closed,
                )
            else:
                self.add_collection_position_if_needed(
                    collection = collection,
                    location_view = location_view,
                )

            try:
                collection_view = CollectionView.objects.get(
                    collection = collection,
                    location_view = location_view,
                )
            except CollectionView.DoesNotExist:
                collection_view = CollectionView.objects.create(
                    collection = collection,
                    location_view = location_view,
                )
            
        return collection_view
    
    def toggle_collection_in_view( self,
                                   collection              : Collection,
                                   location_view           : LocationView ) -> bool:

        try:
            with transaction.atomic():
                self.remove_collection_view(
                    collection = collection,
                    location_view = location_view,
                )
            return False
            
        except CollectionView.DoesNotExist:
            with transaction.atomic():
                _ = self.create_collection_view(
                    collection = collection,
                    location_view = location_view,
                )
            return True
        
    def remove_collection_view( self, collection : Collection, location_view : LocationView ):

        with transaction.atomic():
            collection_view = CollectionView.objects.get(
                collection = collection,
                location_view = location_view,
            )
            collection_view.delete()
            
        return

    def set_collection_path( self,
                             collection    : Collection,
                             location      : Location,
                             svg_path_str  : str        ) -> CollectionPath:

        with transaction.atomic():
            try:
                collection_path = CollectionPath.objects.get(
                    location = location,
                    collection = collection,
                )
                collection_path.svg_path = svg_path_str
                collection_path.save()
                return collection_path

            except CollectionPath.DoesNotExist:
                pass

            return CollectionPath.objects.create(
                collection = collection,
                location = location,
                svg_path = svg_path_str,
            )
            
    def add_collection_position_if_needed( self,
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
    
    def add_collection_path_if_needed( self,
                                       collection      : Collection,
                                       location_view   : LocationView,
                                       is_path_closed  : bool         ) -> CollectionPath:
        try:
            _ = CollectionPath.objects.get(
                location = location_view.location,
                collection = collection,
            )
            return
        except CollectionPath.DoesNotExist:
            pass

        svg_path = SvgItemFactory().get_default_collection_svg_path_str(
            collection = collection,
            location_view = location_view,
            is_path_closed = is_path_closed,
        )
        collection_path = CollectionPath.objects.create(
            collection = collection,
            location = location_view.location,
            svg_path = svg_path,
        )
        return collection_path
        
    def get_collection_edit_mode_data( self,
                                       collection      : Collection,
                                       location_view  : LocationView,
                                       is_editing      : bool ) -> CollectionEditModeData:
        
        collection_position_form = None
        if is_editing and location_view:
            collection_position = CollectionPosition.objects.filter(
                collection = collection,
                location = location_view.location,
            ).first()
            if collection_position:
                collection_position_form = CollectionPositionForm(
                    location_view.location.svg_position_bounds,
                    instance = collection_position,
                )
        
        return CollectionEditModeData(
            collection = collection,
            collection_position_form = collection_position_form,
        )

    def create_entity_collection_group_list( self,
                                             collection : Collection,
                                             unused_entity_ids : set = None ) -> List[EntityCollectionGroup]:

        entity_queryset = Entity.objects.all()

        if unused_entity_ids is None:
            unused_entity_ids = set()

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
                is_unused = entity.id in unused_entity_ids,
            )

            entity_group_type = EntityGroupType.from_entity_type( entity.entity_type )
 
            if entity_group_type not in entity_collection_group_dict:
                entity_collection_group = EntityCollectionGroup(
                    collection = collection,
                    entity_group_type = entity_group_type,
                )
                entity_collection_group_dict[entity_group_type] = entity_collection_group
            entity_collection_group_dict[entity_group_type].item_list.append( entity_collection_item )
            continue

        entity_collection_group_list = list( entity_collection_group_dict.values() )
        entity_collection_group_list.sort( key = lambda item : item.entity_group_type.label )
        return entity_collection_group_list

    def toggle_entity_in_collection( self, entity : Entity, collection : Collection ) -> bool:

        if CollectionEntity.objects.filter( entity = entity, collection = collection ).exists():
            self.remove_entity_from_collection( entity = entity, collection = collection )
            return False
        else:
            self.add_entity_to_collection( entity = entity, collection = collection )
            return True

    def add_entity_to_collection( self, entity : Entity, collection : Collection ) -> bool:

        with transaction.atomic():
            self.create_collection_entity( 
                entity = entity,
                collection = collection,
            )
        return
            
    def remove_entity_from_collection( self, entity : Entity, collection : Collection ) -> bool:

        with transaction.atomic():
            self.remove_collection_entity( 
                entity = entity,
                collection = collection,
            )
        return
        
    def set_collection_entity_order( self,
                                     collection      : Collection,
                                     entity_id_list  : List[int] ):
        item_id_to_idx = {
            item_id: order_id for order_id, item_id in enumerate( entity_id_list )
        }
        
        collection_entity_queryset = CollectionEntity.objects.filter(
            collection = collection,
            entity_id__in = entity_id_list,
        )
        with transaction.atomic():
            for collection_entity in collection_entity_queryset:
                item_idx = item_id_to_idx.get( collection_entity.entity.id )
                order_id = 2 * ( item_idx + 1)  # Leave gaps to make one-off insertions easier
                collection_entity.order_id = order_id
                collection_entity.save()
                continue
        return

    def set_collection_order( self, collection_id_list  : List[int] ):
        item_id_to_idx = {
            item_id: order_id for order_id, item_id in enumerate( collection_id_list )
        }
        
        collection_queryset = Collection.objects.filter( id__in = collection_id_list )
        with transaction.atomic():
            for collection in collection_queryset:
                item_idx = item_id_to_idx.get( collection.id )
                order_id = 2 * ( item_idx + 1)  # Leave gaps to make one-off insertions easier
                collection.order_id = order_id
                collection.save()
                continue
        return
    

    def create_location_collection_view_group( self, location_view : LocationView ) -> CollectionViewGroup:
        existing_collections = [ x.collection
                                 for x in location_view.collection_views.select_related('collection').all() ]
        return self.create_collection_view_group( existing_collections = existing_collections )
    
    def create_collection_view_group( self,
                                      existing_collections : List[ Collection ] ) -> CollectionViewGroup:
        existing_collection_set = set( existing_collections )
        collection_queryset = Collection.objects.all()

        collection_view_group = CollectionViewGroup()
        for collection in collection_queryset:

            collection_view_item = CollectionViewItem(
                collection = collection,
                exists_in_view = bool( collection in existing_collection_set ),
            )
            collection_view_group.item_list.append( collection_view_item )
            continue

        collection_view_group.item_list.sort( key = lambda item : item.collection.name )
        return collection_view_group

