from decimal import Decimal

from hi.apps.common.singleton import Singleton

from .enums import LocationViewType
from .location_view_data import LocationViewData
from .models import Location, LocationView


class LocationViewManager(Singleton):

    def __init_singleton__(self):
        return

    def create_location_view( self,
                              location  : Location,
                              name      : str          ) -> LocationView:

        last_location_view = location.views.order_by( '-order_id' ).first()
        if last_location_view:
            order_id = last_location_view.order_id + 1
        else:
            order_id = 0
            
        return LocationView.objects.create(
            location = location,
            location_view_type_str = LocationViewType.default(),
            name = name,
            svg_view_box_str = str( location.svg_view_box ),
            svg_rotate = Decimal( 0.0 ),
            order_id = order_id,
        )
    
    def get_location_view_data( self, location_view : LocationView ):

        location = location_view.location
        entity_positions = list()
        entity_paths = list()
        non_displayed_entities = set()
        for entity_view in location_view.entity_views.all():
            entity = entity_view.entity
            is_visible = False
            entity_position = entity.positions.filter( location = location ).first()
            if entity_position:
                is_visible = True
                entity_positions.append( entity_position )
            entity_path = entity.paths.filter( location = location ).first()
            if entity_path:
                is_visible = True
                entity_paths.append( entity_path )
            if not is_visible:
                non_displayed_entities.add( entity )
            continue

        collection_positions = list()
        collection_paths = list()
        unpositioned_collections = list()
        for collection_view in location_view.collection_views.all():
            collection = collection_view.collection
            collection_position = collection.positions.filter( location = location ).first()
            if collection_position:
                collection_positions.append( collection_position )
            else:
                unpositioned_collections.append( collection )
            collection_path = collection.paths.filter( location = location ).first()
            if collection_path:
                collection_paths.append( collection_path )
            continue

        # These are used for reporting entities that might otherwise be
        # invisible to the user.  (not displayed on SVG and nor part of any
        # viewable collection).
        #
        orphan_entities = set()
        for entity in non_displayed_entities:
            if not entity.collections.exists():
                orphan_entities.add( entity )
            continue

        # These become bottom buttons, which can be ordered
        unpositioned_collections.sort( key = lambda item : item.order_id )

        return LocationViewData(
            location_view = location_view,
            entity_positions = entity_positions,
            entity_paths = entity_paths,
            collection_positions = collection_positions,
            collection_paths = collection_paths,
            unpositioned_collections = unpositioned_collections,
            orphan_entities = orphan_entities,
        )
