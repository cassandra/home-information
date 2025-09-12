import json
import logging
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Tuple

from django.db import transaction

from hi.apps.entity.models import Entity, EntityPosition, EntityPath, EntityView
from hi.apps.entity.enums import EntityType
from hi.apps.location.models import Location, LocationView
from hi.apps.location.enums import LocationViewType, SvgStyleName
from hi.apps.collection.models import Collection, CollectionEntity, CollectionPosition, CollectionPath, CollectionView
from hi.apps.collection.enums import CollectionType, CollectionViewType

from .enums import ProfileType

logger = logging.getLogger(__name__)


class ProfileManager:
    """
    Manager for loading home profiles from JSON specifications.
    
    Handles atomic creation of locations, entities, collections and their
    relationships from predefined profile templates. Requires empty database.
    """

    def load_profile(self, profile_type: ProfileType) -> Tuple[bool, str]:
        """
        Load a complete profile from predefined JSON specification.
        
        Requires database to be empty (no entities or locations).
        All operations performed in a single atomic transaction.
        """
        try:
            # Validate database is empty before starting
            validation_result = self._validate_empty_database()
            if not validation_result[0]:
                return validation_result
            
            json_file_path = self._get_profile_json_path(profile_type)
            
            with transaction.atomic():
                profile_data = self._load_json_file(json_file_path)
                
                # Create in dependency order
                locations = self._create_locations(profile_data.get('locations', []))
                location_lookup = {loc.name: loc for loc in locations}
                
                entities = self._create_entities(profile_data.get('entities', []))
                entity_lookup = {ent.name: ent for ent in entities}
                
                self._create_entity_positions_and_paths(
                    profile_data.get('entities', []), 
                    entity_lookup, 
                    location_lookup
                )
                
                self._create_location_views(
                    profile_data.get('locations', []), 
                    location_lookup
                )
                
                self._create_entity_views(
                    profile_data.get('entities', []),
                    entity_lookup,
                    location_lookup
                )
                
                collections = self._create_collections(
                    profile_data.get('collections', [])
                )
                collection_lookup = {coll.name: coll for coll in collections}
                
                self._create_collection_entities(
                    profile_data.get('collections', []),
                    collection_lookup,
                    entity_lookup
                )
                
                self._create_collection_positions_and_paths(
                    profile_data.get('collections', []),
                    collection_lookup,
                    location_lookup
                )
                
                self._create_collection_views(
                    profile_data.get('collections', []),
                    collection_lookup,
                    location_lookup
                )
                
                entity_count = len(entities)
                location_count = len(locations)
                collection_count = len(collections)
                
                return True, f"Successfully loaded {profile_type.label} profile: {location_count} locations, {entity_count} entities, {collection_count} collections"
                
        except Exception as e:
            logger.exception(f"Error loading profile {profile_type}")
            return False, f"Failed to load profile: {str(e)}"

    def _validate_empty_database(self) -> Tuple[bool, str]:
        """Validate that database is empty before loading profile"""
        entity_count = Entity.objects.count()
        location_count = Location.objects.count()
        
        if entity_count > 0:
            return False, f"Database must be empty to load profile. Found {entity_count} existing entities."
        
        if location_count > 0:
            return False, f"Database must be empty to load profile. Found {location_count} existing locations."
        
        return True, "Database validation passed"

    def _get_profile_json_path(self, profile_type: ProfileType) -> str:
        """Get the file path for a profile's JSON specification"""
        base_dir = Path(__file__).parent / 'data'
        json_filename = profile_type.json_filename()
        return str(base_dir / json_filename)

    def _load_json_file(self, json_file_path: str) -> dict:
        """Load and validate JSON profile file"""
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                profile_data = json.load(f)
            
            if not isinstance(profile_data, dict):
                raise ValueError("Profile JSON must be a dictionary")
                
            return profile_data
            
        except FileNotFoundError:
            logger.error(f"Profile file not found: {json_file_path}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in profile file {json_file_path}: {e}")
            raise
        except Exception as e:
            logger.exception(f"Unexpected error loading profile file {json_file_path}")
            raise

    def _create_locations(self, location_data_list: List[dict]) -> List[Location]:
        """Create Location instances from profile data"""
        locations = []
        
        for location_data in location_data_list:
            location = Location.objects.create(
                name=location_data['name'],
                svg_fragment_filename=location_data['svg_fragment_filename'],
                svg_view_box_str=location_data['svg_view_box_str'],
                order_id=location_data.get('order_id', 0),
            )
            locations.append(location)
            continue
            
        logger.debug(f"Created {len(locations)} locations")
        return locations

    def _create_location_views(self,
                              location_data_list  : List[dict],
                              location_lookup     : Dict[str, Location]):
        """Create LocationView instances for each location"""
        view_count = 0
        
        for location_data in location_data_list:
            location = location_lookup[location_data['name']]
            
            for view_data in location_data.get('views', []):
                # Validate and convert location_view_type_str through enum
                try:
                    location_view_type = LocationViewType.from_name(view_data['location_view_type_str'])
                    location_view_type_str = str(location_view_type)
                except (KeyError, ValueError) as e:
                    logger.error(f"Invalid location_view_type_str '{view_data.get('location_view_type_str')}' for view '{view_data['name']}': {e}")
                    raise ValueError(f"Invalid location_view_type_str '{view_data.get('location_view_type_str')}' for view '{view_data['name']}'")
                
                # Validate and convert svg_style_name_str through enum
                try:
                    svg_style_name = SvgStyleName.from_name(view_data['svg_style_name_str'])
                    svg_style_name_str = str(svg_style_name)
                except (KeyError, ValueError) as e:
                    logger.error(f"Invalid svg_style_name_str '{view_data.get('svg_style_name_str')}' for view '{view_data['name']}': {e}")
                    raise ValueError(f"Invalid svg_style_name_str '{view_data.get('svg_style_name_str')}' for view '{view_data['name']}'")
                
                LocationView.objects.create(
                    location=location,
                    name=view_data['name'],
                    location_view_type_str=location_view_type_str,
                    svg_view_box_str=view_data['svg_view_box_str'],
                    svg_style_name_str=svg_style_name_str,
                    svg_rotate=Decimal(str(view_data.get('svg_rotate', 0.0))),
                    order_id=view_data.get('order_id', 0),
                )
                view_count += 1
                continue
            continue
            
        logger.debug(f"Created {view_count} location views")
        return

    def _create_entities(self, entity_data_list: List[dict]) -> List[Entity]:
        """Create Entity instances from profile data"""
        entities = []
        
        for entity_data in entity_data_list:
            # Skip comment-only entries
            if 'name' not in entity_data:
                continue
            
            # Validate and convert entity_type_str through enum
            try:
                entity_type = EntityType.from_name(entity_data['entity_type_str'])
                entity_type_str = str(entity_type)
            except (KeyError, ValueError) as e:
                logger.error(f"Invalid entity_type_str '{entity_data.get('entity_type_str')}' for entity '{entity_data['name']}': {e}")
                raise ValueError(f"Invalid entity_type_str '{entity_data.get('entity_type_str')}' for entity '{entity_data['name']}'")
                
            entity = Entity.objects.create(
                name=entity_data['name'],
                entity_type_str=entity_type_str,
            )
            entities.append(entity)
            continue
            
        logger.debug(f"Created {len(entities)} entities")
        return entities

    def _create_entity_positions_and_paths(self,
                                          entity_data_list  : List[dict],
                                          entity_lookup     : Dict[str, Entity],
                                          location_lookup   : Dict[str, Location]):
        """Create EntityPosition and EntityPath instances"""
        position_count = 0
        path_count = 0
        
        for entity_data in entity_data_list:
            if 'name' not in entity_data:
                continue
                
            entity = entity_lookup[entity_data['name']]
            
            # Create EntityPosition instances
            for position_data in entity_data.get('positions', []):
                location = location_lookup[position_data['location_name']]
                
                EntityPosition.objects.create(
                    entity=entity,
                    location=location,
                    svg_x=Decimal(str(position_data['svg_x'])),
                    svg_y=Decimal(str(position_data['svg_y'])),
                    svg_scale=Decimal(str(position_data.get('svg_scale', 1.0))),
                    svg_rotate=Decimal(str(position_data.get('svg_rotate', 0.0))),
                )
                position_count += 1
                continue
            
            # Create EntityPath instances
            for path_data in entity_data.get('paths', []):
                location = location_lookup[path_data['location_name']]
                
                EntityPath.objects.create(
                    entity=entity,
                    location=location,
                    svg_path=path_data['svg_path'],
                )
                path_count += 1
                continue
            continue
            
        logger.debug(f"Created {position_count} entity positions, {path_count} entity paths")
        return

    def _create_entity_views(self,
                            entity_data_list  : List[dict],
                            entity_lookup     : Dict[str, Entity],
                            location_lookup   : Dict[str, Location]):
        """Create EntityView instances to control entity visibility in views"""
        view_count = 0
        
        for entity_data in entity_data_list:
            if 'name' not in entity_data:
                continue
                
            entity = entity_lookup[entity_data['name']]
            
            for view_name in entity_data.get('visible_in_views', []):
                # Find the LocationView by name across all locations
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
                    EntityView.objects.create(
                        entity=entity,
                        location_view=location_view,
                    )
                    view_count += 1
                else:
                    logger.warning(f"Could not find LocationView '{view_name}' for entity '{entity.name}'")
                continue
            continue
            
        logger.debug(f"Created {view_count} entity views")
        return

    def _create_collections(self, collection_data_list: List[dict]) -> List[Collection]:
        """Create Collection instances from profile data"""
        collections = []
        
        for collection_data in collection_data_list:
            # Skip comment-only entries
            if 'name' not in collection_data:
                continue
            
            # Validate and convert collection_type_str through enum
            try:
                collection_type = CollectionType.from_name(collection_data['collection_type_str'])
                collection_type_str = str(collection_type)
            except (KeyError, ValueError) as e:
                logger.error(f"Invalid collection_type_str '{collection_data.get('collection_type_str')}' for collection '{collection_data['name']}': {e}")
                raise ValueError(f"Invalid collection_type_str '{collection_data.get('collection_type_str')}' for collection '{collection_data['name']}'")
            
            # Validate and convert collection_view_type_str through enum
            try:
                collection_view_type = CollectionViewType.from_name(collection_data['collection_view_type_str'])
                collection_view_type_str = str(collection_view_type)
            except (KeyError, ValueError) as e:
                logger.error(f"Invalid collection_view_type_str '{collection_data.get('collection_view_type_str')}' for collection '{collection_data['name']}': {e}")
                raise ValueError(f"Invalid collection_view_type_str '{collection_data.get('collection_view_type_str')}' for collection '{collection_data['name']}'")
                
            collection = Collection.objects.create(
                name=collection_data['name'],
                collection_type_str=collection_type_str,
                collection_view_type_str=collection_view_type_str,
                order_id=collection_data.get('order_id', 0),
            )
            collections.append(collection)
            continue
            
        logger.debug(f"Created {len(collections)} collections")
        return collections

    def _create_collection_entities(self,
                                   collection_data_list  : List[dict],
                                   collection_lookup     : Dict[str, Collection],
                                   entity_lookup         : Dict[str, Entity]):
        """Create CollectionEntity relationships"""
        relationship_count = 0
        
        for collection_data in collection_data_list:
            if 'name' not in collection_data:
                continue
                
            collection = collection_lookup[collection_data['name']]
            
            for order_id, entity_name in enumerate(collection_data.get('entities', [])):
                if entity_name in entity_lookup:
                    entity = entity_lookup[entity_name]
                    
                    CollectionEntity.objects.create(
                        collection=collection,
                        entity=entity,
                        order_id=order_id,
                    )
                    relationship_count += 1
                else:
                    logger.warning(f"Could not find entity '{entity_name}' for collection '{collection.name}'")
                continue
            continue
            
        logger.debug(f"Created {relationship_count} collection-entity relationships")
        return

    def _create_collection_positions_and_paths(self,
                                              collection_data_list  : List[dict],
                                              collection_lookup     : Dict[str, Collection],
                                              location_lookup       : Dict[str, Location]):
        """Create CollectionPosition and CollectionPath instances"""
        position_count = 0
        path_count = 0
        
        for collection_data in collection_data_list:
            if 'name' not in collection_data:
                continue
                
            collection = collection_lookup[collection_data['name']]
            
            # Create CollectionPosition instances
            for position_data in collection_data.get('positions', []):
                location = location_lookup[position_data['location_name']]
                
                CollectionPosition.objects.create(
                    collection=collection,
                    location=location,
                    svg_x=Decimal(str(position_data['svg_x'])),
                    svg_y=Decimal(str(position_data['svg_y'])),
                    svg_scale=Decimal(str(position_data.get('svg_scale', 1.0))),
                    svg_rotate=Decimal(str(position_data.get('svg_rotate', 0.0))),
                )
                position_count += 1
                continue
            
            # Create CollectionPath instances
            for path_data in collection_data.get('paths', []):
                location = location_lookup[path_data['location_name']]
                
                CollectionPath.objects.create(
                    collection=collection,
                    location=location,
                    svg_path=path_data['svg_path'],
                )
                path_count += 1
                continue
            continue
            
        logger.debug(f"Created {position_count} collection positions, {path_count} collection paths")
        return

    def _create_collection_views(self,
                               collection_data_list  : List[dict],
                               collection_lookup     : Dict[str, Collection],
                               location_lookup       : Dict[str, Location]):
        """Create CollectionView instances to control collection visibility in views"""
        view_count = 0
        
        for collection_data in collection_data_list:
            if 'name' not in collection_data:
                continue
                
            collection = collection_lookup[collection_data['name']]
            
            for view_name in collection_data.get('visible_in_views', []):
                # Find the LocationView by name across all locations
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
                    logger.warning(f"Could not find LocationView '{view_name}' for collection '{collection.name}'")
                continue
            continue
            
        logger.debug(f"Created {view_count} collection views")
        return