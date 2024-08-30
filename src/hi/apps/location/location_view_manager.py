from hi.apps.common.singleton import Singleton

from .location_view_data import LocationViewData
from .models import LocationView


class LocationViewManager(Singleton):

    def __init_singleton__(self):
        return

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
        unpositioned_collections = list()
        for collection_view in location_view.collection_views.all():
            collection = collection_view.collection
            collection_position = collection.positions.filter( location = location ).first()
            if collection_position:
                collection_positions.append( collection )
            else:
                unpositioned_collections.append( collection )
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
            unpositioned_collections = unpositioned_collections,
            orphan_entities = orphan_entities,
        )
