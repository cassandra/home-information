from hi.apps.common.singleton import Singleton

from .location_view_data import LocationViewData
from .models import LocationView


class LocationViewManager(Singleton):

    def __init_singleton__(self):
        return

    def get_location_view_data( self, location_view : LocationView ):

        location = location_view.location
        entity_positions = set()
        entity_paths = set()
        non_displayed_entities = set()
        for entity in location_view.entities.all():
            is_visible = False
            entity_position = entity.positions.filter( location = location ).first()
            if entity_position:
                is_visible = True
                entity_positions.add( entity_position )
            entity_path = entity.paths.filter( location = location ).first()
            if entity_path:
                is_visible = True
                entity_paths.add( entity_path )
            if not is_visible:
                non_displayed_entities.add( entity )
            continue

        all_collections = set()
        collection_positions = set()
        unpositioned_collections = set()
        for collection in location_view.collections.all():
            collection_position = collection.positions.filter( location = location ).first()
            if collection_position:
                collection_positions.add( collection )
            else:
                unpositioned_collections.add( collection )
            all_collections.add( collection )
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
        collection_list = list( unpositioned_collections )
        collection_list.sort( key = lambda item : item.order_id )

        return LocationViewData(
            location_view = location_view,
            entity_positions = entity_positions,
            entity_paths = entity_paths,
            collection_positions = collection_positions,
            unpositioned_collections = unpositioned_collections,
            orphan_entities = orphan_entities,
        )
