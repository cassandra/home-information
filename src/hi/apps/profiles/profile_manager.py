import json
import logging
from decimal import Decimal
from pathlib import Path
from typing import Dict, List

from django.db import transaction

from hi.apps.entity.models import Entity, EntityPosition, EntityPath, EntityView
from hi.apps.entity.enums import EntityType
from hi.apps.location.models import Location, LocationView
from hi.apps.location.enums import LocationViewType, SvgStyleName
from hi.apps.collection.models import (
    Collection,
    CollectionEntity,
    CollectionPosition,
    CollectionPath,
    CollectionView,
)
from hi.apps.collection.enums import CollectionType, CollectionViewType

from .enums import ProfileType
import hi.apps.profiles.constants as PC

logger = logging.getLogger(__name__)


class ProfileManager:
    """
    Manager for loading home profiles from JSON specifications.
    
    Handles atomic creation of locations, entities, collections and their
    relationships from predefined profile templates. Requires empty database.
    """

    def load_profile(self, profile_type: ProfileType) -> None:
        """
        Load a complete profile from predefined JSON specification.
        
        Requires database to be empty (no entities or locations).
        All operations performed in a single atomic transaction.
        
        Raises:
            ValueError: If database is not empty
            FileNotFoundError: If profile JSON file is missing
            json.JSONDecodeError: If profile JSON is invalid
            Exception: For other errors during profile loading
        """
        # Validate database is empty before starting
        self._validate_empty_database()
        
        json_file_path = self._get_profile_json_path(profile_type)
        
        with transaction.atomic():
            profile_data = self._load_json_file( json_file_path )
            
            # Create in dependency order
            locations = self._create_locations( profile_data.get(PC.PROFILE_FIELD_LOCATIONS, []) )
            location_lookup = { location.name: location for location in locations }
            
            entities = self._create_entities(profile_data.get(PC.PROFILE_FIELD_ENTITIES, []))
            entity_lookup = { entity.name: entity for entity in entities }
            
            self._create_entity_positions_and_paths(
                profile_data.get(PC.PROFILE_FIELD_ENTITIES, []), 
                entity_lookup, 
                location_lookup,
            )
            
            self._create_location_views(
                profile_data.get(PC.PROFILE_FIELD_LOCATIONS, []), 
                location_lookup,
            )
            
            self._create_entity_views(
                profile_data.get(PC.PROFILE_FIELD_ENTITIES, []),
                entity_lookup,
                location_lookup,
            )
            
            collections = self._create_collections(
                profile_data.get(PC.PROFILE_FIELD_COLLECTIONS, [])
            )
            collection_lookup = { collection.name: collection for collection in collections }
            
            self._create_collection_entities(
                profile_data.get( PC.PROFILE_FIELD_COLLECTIONS, [] ),
                collection_lookup,
                entity_lookup,
            )
            
            self._create_collection_positions_and_paths(
                profile_data.get(PC.PROFILE_FIELD_COLLECTIONS, []),
                collection_lookup,
                location_lookup,
            )
            
            self._create_collection_views(
                profile_data.get(PC.PROFILE_FIELD_COLLECTIONS, []),
                collection_lookup,
                location_lookup,
            )
            
            entity_count = len(entities)
            location_count = len(locations)
            collection_count = len(collections)
            
            logger.info( f'Successfully loaded {profile_type.label} profile:'
                         f' {location_count} locations, {entity_count} entities,'
                         f' {collection_count} collections' )
            return
        
    def _validate_empty_database(self) -> None:
        """Validate that database is empty before loading profile.
        
        Raises:
            ValueError: If database contains existing entities or locations
        """
        entity_count = Entity.objects.count()
        location_count = Location.objects.count()
        if ( entity_count > 0 ) or ( location_count > 0 ):
            raise ValueError( 'Database must be empty to load profile.' )
        return
    
    def _get_profile_json_path(self, profile_type: ProfileType) -> str:
        base_dir = Path(__file__).parent / 'data'
        json_filename = profile_type.json_filename()
        return str( base_dir / json_filename )

    def _load_json_file(self, json_file_path: str) -> dict:
        try:
            with open( json_file_path, 'r', encoding='utf-8' ) as f:
                profile_data = json.load(f)
            
            if not isinstance( profile_data, dict ):
                raise ValueError('Profile JSON must be a dictionary')
                
            return profile_data
            
        except FileNotFoundError:
            logger.error(f'Profile file not found: {json_file_path}')
            raise
        except json.JSONDecodeError as e:
            logger.error(f'Invalid JSON in profile file {json_file_path}: {e}')
            raise
        except Exception:
            logger.exception(f'Unexpected error loading profile file {json_file_path}')
            raise

    def _create_locations(self, location_data_list: List[dict]) -> List[Location]:
        locations = []

        for location_data in location_data_list:
            location = Location.objects.create(
                name = location_data[PC.LOCATION_FIELD_NAME],
                svg_fragment_filename = location_data[PC.LOCATION_FIELD_SVG_FRAGMENT_FILENAME],
                svg_view_box_str = location_data[PC.LOCATION_FIELD_SVG_VIEW_BOX_STR],
                order_id = location_data.get(PC.LOCATION_FIELD_ORDER_ID, 0),
            )
            locations.append(location)
            continue
            
        logger.debug(f'Created {len(locations)} locations')
        return locations

    def _create_location_views( self,
                                location_data_list  : List[dict],
                                location_lookup     : Dict[str, Location]):
        view_count = 0
        
        for location_data in location_data_list:
            location_name = location_data[PC.LOCATION_FIELD_NAME]
            location = location_lookup[ location_name ]
            
            for view_data in location_data.get( PC.LOCATION_FIELD_VIEWS, [] ):
                location_view_name = view_data[PC.LOCATION_VIEW_FIELD_NAME]
                try:
                    input_str = view_data[PC.LOCATION_VIEW_FIELD_TYPE_STR]
                    location_view_type = LocationViewType.from_name( input_str )
                except (KeyError, ValueError) as e:
                    logger.error( f'Invalid location_view_type_str: {input_str}: {e}' )
                    raise ValueError( f'Invalid location_view_type_str {input_str}' )
                
                try:
                    input_str = view_data[PC.LOCATION_VIEW_FIELD_SVG_STYLE_NAME_STR]
                    svg_style_name = SvgStyleName.from_name( input_str )
                except (KeyError, ValueError) as e:
                    logger.error(f'Invalid svg_style_name_str {input_str}: {e}')
                    raise ValueError(f'Invalid svg_style_name_str {input_str}')
                
                LocationView.objects.create(
                    location = location,
                    name = location_view_name,
                    location_view_type_str= str( location_view_type ),
                    svg_view_box_str = view_data[PC.LOCATION_VIEW_FIELD_SVG_VIEW_BOX_STR],
                    svg_style_name_str = str(svg_style_name),
                    svg_rotate = Decimal( str(view_data.get(PC.COMMON_FIELD_SVG_ROTATE, 0.0)) ),
                    order_id = view_data.get(PC.LOCATION_VIEW_FIELD_ORDER_ID, 0),
                )
                view_count += 1
                continue
            continue
            
        logger.debug( f'Created {view_count} location views' )
        return

    def _create_entities( self, entity_data_list: List[dict] ) -> List[Entity]:
        """Create Entity instances from profile data"""
        entities = []
        
        for entity_data in entity_data_list:
            # Skip comment-only entries
            if PC.ENTITY_FIELD_NAME not in entity_data:
                continue
            
            try:
                input_str = entity_data[PC.ENTITY_FIELD_TYPE_STR]
                entity_type = EntityType.from_name( input_str )
            except (KeyError, ValueError) as e:
                logger.error( f'Invalid entity_type_str {input_str}: {e}')
                raise ValueError( f'Invalid entity_type_str {input_str}' )
                
            entity = Entity.objects.create(
                name = entity_data[PC.ENTITY_FIELD_NAME],
                entity_type_str = str(entity_type),
            )
            entities.append(entity)
            continue
            
        logger.debug(f'Created {len(entities)} entities')
        return entities

    def _create_entity_positions_and_paths( self,
                                            entity_data_list  : List[dict],
                                            entity_lookup     : Dict[str, Entity],
                                            location_lookup   : Dict[str, Location] ):
        position_count = 0
        path_count = 0
        
        for entity_data in entity_data_list:
            if PC.ENTITY_FIELD_NAME not in entity_data:
                continue
                
            entity = entity_lookup[entity_data[PC.ENTITY_FIELD_NAME]]
            
            for position_data in entity_data.get(PC.ENTITY_FIELD_POSITIONS, []):
                location = location_lookup[position_data[PC.COMMON_FIELD_LOCATION_NAME]]
                
                EntityPosition.objects.create(
                    entity = entity,
                    location = location,
                    svg_x = Decimal(str(position_data[PC.COMMON_FIELD_SVG_X])),
                    svg_y = Decimal(str(position_data[PC.COMMON_FIELD_SVG_Y])),
                    svg_scale = Decimal(str(position_data.get(PC.COMMON_FIELD_SVG_SCALE, 1.0))),
                    svg_rotate = Decimal(str(position_data.get(PC.COMMON_FIELD_SVG_ROTATE, 0.0))),
                )
                position_count += 1
                continue
            
            for path_data in entity_data.get(PC.ENTITY_FIELD_PATHS, []):
                location = location_lookup[path_data[PC.COMMON_FIELD_LOCATION_NAME]]
                
                EntityPath.objects.create(
                    entity = entity,
                    location = location,
                    svg_path = path_data[PC.COMMON_FIELD_SVG_PATH],
                )
                path_count += 1
                continue
            continue
            
        logger.debug(f'Created {position_count} entity positions, {path_count} entity paths')
        return

    def _create_entity_views( self,
                              entity_data_list  : List[dict],
                              entity_lookup     : Dict[str, Entity],
                              location_lookup   : Dict[str, Location]):
        view_count = 0
        
        for entity_data in entity_data_list:
            if PC.ENTITY_FIELD_NAME not in entity_data:
                continue
                
            entity = entity_lookup[entity_data[PC.ENTITY_FIELD_NAME]]
            
            for view_name in entity_data.get(PC.ENTITY_FIELD_VISIBLE_IN_VIEWS, []):
                location_view = None
                for location in location_lookup.values():
                    try:
                        location_view = LocationView.objects.get(
                            location =location,
                            name =view_name
                        )
                        break
                    except LocationView.DoesNotExist:
                        continue
                
                if location_view:
                    EntityView.objects.create(
                        entity = entity,
                        location_view = location_view,
                    )
                    view_count += 1
                else:
                    logger.warning( f'Could not find LocationView: {view_name}' )
                continue
            continue
            
        logger.debug(f'Created {view_count} entity views')
        return

    def _create_collections(self, collection_data_list: List[dict]) -> List[Collection]:
        collections = []
        
        for collection_data in collection_data_list:
            # Skip comment-only entries
            if 'name' not in collection_data:
                continue
            
            try:
                input_str = collection_data[PC.COLLECTION_FIELD_TYPE_STR]
                collection_type = CollectionType.from_name( input_str )
            except (KeyError, ValueError) as e:
                logger.error( f'Invalid collection_type_str {input_str}: {e}')
                raise ValueError(f'Invalid collection_type_str {input_str}' )
            
            try:
                input_str = collection_data[PC.COLLECTION_FIELD_VIEW_TYPE_STR]
                collection_view_type = CollectionViewType.from_name( input_str )
            except (KeyError, ValueError) as e:
                logger.error( f'Invalid collection_view_type_str {input_str}: {e}' )
                raise ValueError( f'Invalid collection_view_type_str {input_str}' )
                
            collection = Collection.objects.create(
                name = collection_data[PC.COLLECTION_FIELD_NAME],
                collection_type_str = str(collection_type),
                collection_view_type_str = str(collection_view_type),
                order_id = collection_data.get(PC.COLLECTION_FIELD_ORDER_ID, 0),
            )
            collections.append(collection)
            continue
            
        logger.debug(f'Created {len(collections)} collections')
        return collections

    def _create_collection_entities( self,
                                     collection_data_list  : List[dict],
                                     collection_lookup     : Dict[str, Collection],
                                     entity_lookup         : Dict[str, Entity]):
        relationship_count = 0
        
        for collection_data in collection_data_list:
            if PC.COLLECTION_FIELD_NAME not in collection_data:
                continue
                
            collection = collection_lookup[collection_data[PC.COLLECTION_FIELD_NAME]]
            
            for order_id, entity_name in enumerate(collection_data.get(PC.COLLECTION_FIELD_ENTITIES, [])):
                if entity_name in entity_lookup:
                    entity = entity_lookup[entity_name]
                    
                    CollectionEntity.objects.create(
                        collection = collection,
                        entity = entity,
                        order_id = order_id,
                    )
                    relationship_count += 1
                else:
                    logger.warning( f'Could not find entity {entity_name}' )
                continue
            continue
            
        logger.debug(f'Created {relationship_count} collection-entity relationships')
        return

    def _create_collection_positions_and_paths( self,
                                                collection_data_list  : List[dict],
                                                collection_lookup     : Dict[str, Collection],
                                                location_lookup       : Dict[str, Location] ):
        position_count = 0
        path_count = 0
        
        for collection_data in collection_data_list:
            if PC.COLLECTION_FIELD_NAME not in collection_data:
                continue
                
            collection = collection_lookup[collection_data[PC.COLLECTION_FIELD_NAME]]
            
            for position_data in collection_data.get(PC.COLLECTION_FIELD_POSITIONS, []):
                location = location_lookup[position_data[PC.COMMON_FIELD_LOCATION_NAME]]
                
                CollectionPosition.objects.create(
                    collection = collection,
                    location = location,
                    svg_x = Decimal(str(position_data[PC.COMMON_FIELD_SVG_X])),
                    svg_y = Decimal(str(position_data[PC.COMMON_FIELD_SVG_Y])),
                    svg_scale = Decimal(str(position_data.get(PC.COMMON_FIELD_SVG_SCALE, 1.0))),
                    svg_rotate = Decimal(str(position_data.get(PC.COMMON_FIELD_SVG_ROTATE, 0.0))),
                )
                position_count += 1
                continue
            
            # Create CollectionPath instances
            for path_data in collection_data.get(PC.COLLECTION_FIELD_PATHS, []):
                location = location_lookup[path_data[PC.COMMON_FIELD_LOCATION_NAME]]
                
                CollectionPath.objects.create(
                    collection=collection,
                    location=location,
                    svg_path=path_data[PC.COMMON_FIELD_SVG_PATH],
                )
                path_count += 1
                continue
            continue
            
        logger.debug(f'Created {position_count} collection positions, {path_count} paths')
        return

    def _create_collection_views( self,
                                  collection_data_list  : List[dict],
                                  collection_lookup     : Dict[str, Collection],
                                  location_lookup       : Dict[str, Location] ):
        view_count = 0
        
        for collection_data in collection_data_list:
            if PC.COLLECTION_FIELD_NAME not in collection_data:
                continue
                
            collection = collection_lookup[collection_data[PC.COLLECTION_FIELD_NAME]]
            
            for view_name in collection_data.get(PC.COLLECTION_FIELD_VISIBLE_IN_VIEWS, []):
                location_view = None
                for location in location_lookup.values():
                    try:
                        location_view = LocationView.objects.get(
                            location=location,
                            name=view_name
                        )
                        break
                    except LocationView.DoesNotExist:
                        continue
                
                if location_view:
                    CollectionView.objects.create(
                        collection=collection,
                        location_view=location_view,
                    )
                    view_count += 1
                else:
                    logger.warning(f'Could not find LocationView {view_name}' )
                continue
            continue
            
        logger.debug(f'Created {view_count} collection views')
        return
