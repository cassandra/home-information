from decimal import Decimal

from django.db import transaction
from django.http import HttpRequest

from hi.apps.common.singleton import Singleton
from hi.apps.entity.models import Entity
from hi.apps.location.models import Location, LocationView

from .collection_data import CollectionData
from .enums import CollectionType
from .models import (
    Collection,
    CollectionEntity,
    CollectionPath,
    CollectionPosition,
    CollectionView,
)


class CollectionManager(Singleton):

    PATH_EDIT_NEW_PATH_RADIUS_PERCENT = 5.0  # Preferrable if this matches Javascript new path sizing.
        
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
        
        return Collection.objects.create(
            name = name,
            collection_type_str = str(collection_type),
            order_id = last_collection.order_id + 1,
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
            if collection.collection_type.is_path:
                self.add_collection_path_if_needed(
                    collection = collection,
                    location_view = location_view,
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
        assert not collection.collection_type.is_path

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
                                       collection : Collection,
                                       location_view : LocationView ) -> CollectionPath:
        assert collection.collection_type.is_path

        try:
            _ = CollectionPath.objects.get(
                location = location_view.location,
                collection = collection,
            )
            return
        except CollectionPath.DoesNotExist:
            pass

        # Note that this server-side creation of a new path is just one
        # place new paths can be created. During client-side path editing,
        # the Javascript code also uses logic to add new path segments.
        # These do not have to behave identical, but it is preferrable for
        # there to be some consistency.
        
        # Default display a line or rectangle in middle of current view with radius X% of viewbox
        center_x = location_view.svg_view_box.x + ( location_view.svg_view_box.width / 2.0 )
        center_y = location_view.svg_view_box.y + ( location_view.svg_view_box.height / 2.0 )
        radius_x = location_view.svg_view_box.width * ( self.PATH_EDIT_NEW_PATH_RADIUS_PERCENT / 100.0 )
        radius_y = location_view.svg_view_box.height * ( self.PATH_EDIT_NEW_PATH_RADIUS_PERCENT / 100.0 )

        if collection.collection_type.is_path_closed:
            top_left_x = center_x - radius_x
            top_left_y = center_y - radius_y
            top_right_x = center_x + radius_x
            top_right_y = center_y - radius_y
            bottom_right_x = center_x + radius_x
            bottom_right_y = center_y + radius_y
            bottom_left_x = center_x - radius_x
            bottom_left_y = center_y + radius_y
            svg_path = f'M {top_left_x},{top_left_y} L {top_right_x},{top_right_y} L {bottom_right_x},{bottom_right_y} L {bottom_left_x},{bottom_left_y} Z'
        else:
            start_x = center_x - radius_x
            start_y = center_y
            end_x = start_x + radius_x
            end_y = start_y
            svg_path = f'M {start_x},{start_y} L {end_x},{end_y}'
        
        collection_path = CollectionPath.objects.create(
            collection = collection,
            location = location_view.location,
            svg_path = svg_path,
        )
        return collection_path
        
    
