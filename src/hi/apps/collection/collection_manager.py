from decimal import Decimal

from django.db import transaction
from django.http import HttpRequest

from hi.apps.common.singleton import Singleton
from hi.apps.entity.models import Entity
from hi.apps.location.forms import LocationItemPositionForm
from hi.apps.location.models import Location, LocationView
from hi.apps.location.svg_item_factory import SvgItemFactory

from .collection_data import CollectionData
from .collection_detail_data import CollectionDetailData
from .enums import CollectionType
from .models import (
    Collection,
    CollectionEntity,
    CollectionPath,
    CollectionPosition,
    CollectionView,
)


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

    def create_collection( self,
                           request          : HttpRequest,
                           collection_type  : CollectionType,
                           name             : str          ) -> Collection:
        last_collection = Collection.objects.all().order_by( '-order_id' ).first()
        if last_collection:
            order_id = last_collection.order_id + 1
        else:
            order_id = 0
            
        return Collection.objects.create(
            name = name,
            collection_type_str = str(collection_type),
            order_id = order_id,
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

    def remove_collection_view( self, collection : Collection, location_view : LocationView ):

        with transaction.atomic():
            collection_view = CollectionView.objects.get(
                collection = collection,
                location_view = location_view,
            )
            collection_view.delete()
            
        return

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
    
    def set_collection_path( self,
                             collection_id     : int,
                             location      : Location,
                             svg_path_str  : str        ) -> CollectionPath:

        try:
            collection_path = CollectionPath.objects.get(
                location = location,
                collection_id = collection_id,
            )
            collection_path.svg_path = svg_path_str
            collection_path.save()
            return collection_path
        
        except CollectionPath.DoesNotExist:
            pass

        collection = Collection.objects.get( id = collection_id )
        return CollectionPath.objects.create(
            collection = collection,
            location = location,
            svg_path = svg_path_str,
        )
            
    def get_collection_position( self,
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

        svg_path = SvgItemFactory().get_default_svg_path_str(
            location_view = location_view,
            is_path_closed = is_path_closed,
        )
        collection_path = CollectionPath.objects.create(
            collection = collection,
            location = location_view.location,
            svg_path = svg_path,
        )
        return collection_path
        
    def get_collection_detail_data( self,
                                    collection             : Collection,
                                    current_location_view  : LocationView,
                                    is_editing             : bool ) -> CollectionDetailData:
        
        location_item_position_form = None
        if is_editing and current_location_view:
            collection_position = CollectionPosition.objects.filter(
                collection = collection,
                location = current_location_view.location,
            ).first()
            if collection_position:
                location_item_position_form = LocationItemPositionForm.from_models(
                    location_item = collection_position.collection,
                    location_item_position = collection_position,
                )
        
        # TODO: Add attributes and other data
        return CollectionDetailData(
            collection = collection,
            location_item_position_form = location_item_position_form,
        )

