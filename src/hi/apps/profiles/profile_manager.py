import json
import logging
import os
import shutil
from decimal import Decimal
from pathlib import Path
from typing import Dict, List
from dataclasses import dataclass

from django.conf import settings
from django.core.files.storage import default_storage, FileSystemStorage
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


@dataclass
class ProfileLoadingStats:
    """Track success/failure counts during profile loading."""
    locations_attempted: int = 0
    locations_succeeded: int = 0
    locations_failed: int = 0
    
    entities_attempted: int = 0
    entities_succeeded: int = 0
    entities_failed: int = 0
    
    collections_attempted: int = 0
    collections_succeeded: int = 0
    collections_failed: int = 0
    
    location_views_attempted: int = 0
    location_views_succeeded: int = 0
    location_views_failed: int = 0
    
    entity_positions_attempted: int = 0
    entity_positions_succeeded: int = 0
    entity_positions_failed: int = 0
    
    entity_paths_attempted: int = 0
    entity_paths_succeeded: int = 0
    entity_paths_failed: int = 0
    
    entity_views_attempted: int = 0
    entity_views_succeeded: int = 0
    entity_views_failed: int = 0
    
    collection_entities_attempted: int = 0
    collection_entities_succeeded: int = 0
    collection_entities_failed: int = 0
    
    collection_positions_attempted: int = 0
    collection_positions_succeeded: int = 0
    collection_positions_failed: int = 0
    
    collection_paths_attempted: int = 0
    collection_paths_succeeded: int = 0
    collection_paths_failed: int = 0
    
    collection_views_attempted: int = 0
    collection_views_succeeded: int = 0
    collection_views_failed: int = 0
    
    def log_summary(self, profile_label: str):
        """Log a comprehensive summary of loading results."""
        logger.info(f'Profile loading summary for {profile_label}:')
        logger.info(f'  Locations: {self.locations_succeeded}/{self.locations_attempted} succeeded')
        logger.info(f'  Entities: {self.entities_succeeded}/{self.entities_attempted} succeeded')
        logger.info(f'  Collections: {self.collections_succeeded}/{self.collections_attempted} succeeded')
        logger.info(f'  Location Views: {self.location_views_succeeded}/{self.location_views_attempted} succeeded')
        logger.info(f'  Entity Positions: {self.entity_positions_succeeded}/{self.entity_positions_attempted} succeeded')
        logger.info(f'  Entity Paths: {self.entity_paths_succeeded}/{self.entity_paths_attempted} succeeded')
        logger.info(f'  Entity Views: {self.entity_views_succeeded}/{self.entity_views_attempted} succeeded')
        logger.info(f'  Collection Entities: {self.collection_entities_succeeded}/{self.collection_entities_attempted} succeeded')
        logger.info(f'  Collection Positions: {self.collection_positions_succeeded}/{self.collection_positions_attempted} succeeded')
        logger.info(f'  Collection Paths: {self.collection_paths_succeeded}/{self.collection_paths_attempted} succeeded')
        logger.info(f'  Collection Views: {self.collection_views_succeeded}/{self.collection_views_attempted} succeeded')
        
        total_failed = (self.locations_failed + self.entities_failed + self.collections_failed
                        + self.location_views_failed + self.entity_positions_failed + self.entity_paths_failed
                        + self.entity_views_failed + self.collection_entities_failed + self.collection_positions_failed
                        + self.collection_paths_failed + self.collection_views_failed)
        
        if total_failed > 0:
            logger.warning(f'Total failures during profile loading: {total_failed}')
    
    def meets_minimum_requirements(self) -> bool:
        """Check if minimum viable profile was loaded (at least 1 Location and 1 Entity)."""
        return self.locations_succeeded >= 1 and self.entities_succeeded >= 1


class ProfileManager:
    """
    Manager for loading home profiles from JSON specifications.
    
    Handles atomic creation of locations, entities, collections and their
    relationships from predefined profile templates. Requires empty database.
    """

    def load_profile(self, profile_type: ProfileType) -> ProfileLoadingStats:
        """
        Load a complete profile from predefined JSON specification with robust error handling.
        
        Continues loading even if individual items fail, but ensures minimum viable profile.
        Requires database to be empty (no entities or locations).
        All operations performed in a single atomic transaction.
        
        Returns:
            ProfileLoadingStats: Detailed statistics about what succeeded and failed during loading
        
        Raises:
            ValueError: If database is not empty, fundamental validation fails, 
                       or minimum requirements not met (at least 1 Location and 1 Entity)
            FileNotFoundError: If profile JSON file is missing
            json.JSONDecodeError: If profile JSON is invalid
            Exception: For other fundamental errors during profile loading
        """
        # Validate database is empty before starting
        self._validate_empty_database()
        
        json_file_path = self._get_profile_json_path(profile_type)
        profile_data = self._load_json_file( json_file_path )
        
        # Validate fundamental requirements before starting
        self._validate_fundamental_requirements(profile_data)
        
        # Copy SVG fragment files from assets to MEDIA_ROOT before validation
        self._copy_svg_fragment_files(profile_data)
        
        # Initialize tracking
        stats = ProfileLoadingStats()
        
        with transaction.atomic():
            # Create core models with error tracking
            locations, location_lookup = self._create_locations_robust(
                profile_data.get(PC.PROFILE_FIELD_LOCATIONS, []), stats)
            
            entities, entity_lookup = self._create_entities_robust(
                profile_data.get(PC.PROFILE_FIELD_ENTITIES, []), stats)
            
            collections, collection_lookup = self._create_collections_robust(
                profile_data.get(PC.PROFILE_FIELD_COLLECTIONS, []), stats)
            
            # Create relationships with error tracking
            self._create_entity_positions_and_paths_robust(
                profile_data.get(PC.PROFILE_FIELD_ENTITIES, []), 
                entity_lookup, location_lookup, stats)
            
            self._create_location_views_robust(
                profile_data.get(PC.PROFILE_FIELD_LOCATIONS, []), 
                location_lookup, stats)
            
            self._create_entity_views_robust(
                profile_data.get(PC.PROFILE_FIELD_ENTITIES, []),
                entity_lookup, location_lookup, stats)
            
            self._create_collection_entities_robust(
                profile_data.get( PC.PROFILE_FIELD_COLLECTIONS, [] ),
                collection_lookup, entity_lookup, stats)
            
            self._create_collection_positions_and_paths_robust(
                profile_data.get(PC.PROFILE_FIELD_COLLECTIONS, []),
                collection_lookup, location_lookup, stats)
            
            self._create_collection_views_robust(
                profile_data.get(PC.PROFILE_FIELD_COLLECTIONS, []),
                collection_lookup, location_lookup, stats)
            
            # Validate minimum requirements were met
            if not stats.meets_minimum_requirements():
                raise ValueError(
                    f'Profile loading failed: Minimum requirements not met. '
                    f'Successfully loaded {stats.locations_succeeded} locations '
                    f'and {stats.entities_succeeded} entities. '
                    f'At least 1 location and 1 entity are required.')
            
            # Log comprehensive results
            stats.log_summary(profile_type.label)
            return stats
    
    def _validate_fundamental_requirements(self, profile_data: dict) -> None:
        """
        Validate fundamental requirements before starting profile loading.
        
        Raises:
            ValueError: If fundamental requirements are not met
        """
        # Ensure there are locations defined
        locations_data = profile_data.get(PC.PROFILE_FIELD_LOCATIONS, [])
        if not locations_data:
            raise ValueError('Profile must contain at least one location definition')
        
        # Ensure there are entities defined
        entities_data = profile_data.get(PC.PROFILE_FIELD_ENTITIES, [])
        if not entities_data:
            raise ValueError('Profile must contain at least one entity definition')
        
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
        base_dir = Path(__file__).parent
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

    def _get_assets_base_directory(self) -> Path:
        """
        Get the base directory for profile assets.
        
        This is separated into its own method to allow easy overriding in tests.
        
        Returns:
            Path: The base directory containing profile assets
        """
        return Path(__file__).parent / 'assets'
    
    def _copy_svg_fragment_files(self, profile_data: dict) -> None:
        """
        Copy predefined SVG fragment files from profile assets to MEDIA_ROOT.
        
        This must be called before location creation/validation to ensure
        referenced SVG files exist in MEDIA_ROOT.
        
        Args:
            profile_data: The loaded profile JSON data
            
        Raises:
            FileNotFoundError: If required SVG fragment files are missing from assets
            Exception: For other file system errors during copying
        """
        locations_data = profile_data.get(PC.PROFILE_FIELD_LOCATIONS, [])
        assets_base_dir = self._get_assets_base_directory()
        
        for location_data in locations_data:
            svg_fragment_filename = location_data.get(PC.LOCATION_FIELD_SVG_FRAGMENT_FILENAME)
            if not svg_fragment_filename:
                continue
                
            # Source: profile assets directory
            source_path = assets_base_dir / svg_fragment_filename
            
            # Destination: MEDIA_ROOT
            destination_path = os.path.join(settings.MEDIA_ROOT, svg_fragment_filename)
            
            try:
                if not source_path.exists():
                    raise FileNotFoundError(f'SVG fragment file not found in assets: {source_path}')
                
                # Ensure destination directory exists
                self._ensure_directory_exists(svg_fragment_filename)
                
                # Copy the file
                shutil.copy2(str(source_path), destination_path)
                logger.debug(f'Copied SVG fragment: {source_path} -> {destination_path}')
                
            except Exception as e:
                logger.error(f'Failed to copy SVG fragment {svg_fragment_filename}: {e}')
                raise
                
        logger.debug('SVG fragment files copied successfully')
        
    def _ensure_directory_exists(self, filepath: str) -> None:
        """
        Ensure the directory for the given filepath exists in MEDIA_ROOT.
        
        This follows the same pattern as LocationManager._ensure_directory_exists
        """
        if isinstance(default_storage, FileSystemStorage):
            directory = os.path.dirname(default_storage.path(filepath))
            if not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)

    def _create_locations(self, location_data_list: List[dict]) -> List[Location]:
        locations = []

        for location_data in location_data_list:
            svg_fragment_filename = location_data[PC.LOCATION_FIELD_SVG_FRAGMENT_FILENAME]
            
            # Validate SVG file exists in MEDIA_ROOT (same as include_media_template)
            full_filesystem_path = os.path.join(settings.MEDIA_ROOT, svg_fragment_filename)
            if not os.path.exists(full_filesystem_path):
                raise ValueError(f'SVG file not found: {full_filesystem_path}')
            
            location = Location.objects.create(
                name = location_data[PC.LOCATION_FIELD_NAME],
                svg_fragment_filename = svg_fragment_filename,
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

    # Robust error handling versions of creation methods
    
    def _create_locations_robust(self, location_data_list: List[dict], stats: ProfileLoadingStats) -> tuple[List[Location], Dict[str, Location]]:
        """Create locations with error tracking and graceful failure handling."""
        locations = []
        
        for location_data in location_data_list:
            stats.locations_attempted += 1
            try:
                svg_fragment_filename = location_data[PC.LOCATION_FIELD_SVG_FRAGMENT_FILENAME]
                
                # Validate SVG file exists in MEDIA_ROOT (same as include_media_template)
                full_filesystem_path = os.path.join(settings.MEDIA_ROOT, svg_fragment_filename)
                if not os.path.exists(full_filesystem_path):
                    raise ValueError(f'SVG file not found: {full_filesystem_path}')
                
                location = Location.objects.create(
                    name = location_data[PC.LOCATION_FIELD_NAME],
                    svg_fragment_filename = svg_fragment_filename,
                    svg_view_box_str = location_data[PC.LOCATION_FIELD_SVG_VIEW_BOX_STR],
                    order_id = location_data.get(PC.LOCATION_FIELD_ORDER_ID, 0),
                )
                locations.append(location)
                stats.locations_succeeded += 1
                
            except Exception as e:
                stats.locations_failed += 1
                location_name = location_data.get(PC.LOCATION_FIELD_NAME, 'unknown')
                logger.error(f'Failed to create location "{location_name}": {e}')
                continue
                
        location_lookup = { location.name: location for location in locations }
        logger.debug(f'Created {len(locations)} locations ({stats.locations_succeeded} succeeded, {stats.locations_failed} failed)')
        return locations, location_lookup

    def _create_entities_robust(self, entity_data_list: List[dict], stats: ProfileLoadingStats) -> tuple[List[Entity], Dict[str, Entity]]:
        """Create entities with error tracking and graceful failure handling."""
        entities = []
        
        for entity_data in entity_data_list:
            # Skip comment-only entries
            if PC.ENTITY_FIELD_NAME not in entity_data:
                continue
                
            stats.entities_attempted += 1
            try:
                input_str = entity_data[PC.ENTITY_FIELD_TYPE_STR]
                entity_type = EntityType.from_name( input_str )
                    
                entity = Entity.objects.create(
                    name = entity_data[PC.ENTITY_FIELD_NAME],
                    entity_type_str = str(entity_type),
                )
                entities.append(entity)
                stats.entities_succeeded += 1
                
            except Exception as e:
                stats.entities_failed += 1
                entity_name = entity_data.get(PC.ENTITY_FIELD_NAME, 'unknown')
                logger.error(f'Failed to create entity "{entity_name}": {e}')
                continue
                
        entity_lookup = { entity.name: entity for entity in entities }
        logger.debug(f'Created {len(entities)} entities ({stats.entities_succeeded} succeeded, {stats.entities_failed} failed)')
        return entities, entity_lookup

    def _create_collections_robust(self, collection_data_list: List[dict], stats: ProfileLoadingStats) -> tuple[List[Collection], Dict[str, Collection]]:
        """Create collections with error tracking and graceful failure handling."""
        collections = []
        
        for collection_data in collection_data_list:
            # Skip comment-only entries
            if PC.COLLECTION_FIELD_NAME not in collection_data:
                continue
                
            stats.collections_attempted += 1
            try:
                input_str = collection_data[PC.COLLECTION_FIELD_TYPE_STR]
                collection_type = CollectionType.from_name( input_str )
                
                input_str = collection_data[PC.COLLECTION_FIELD_VIEW_TYPE_STR]
                collection_view_type = CollectionViewType.from_name( input_str )
                    
                collection = Collection.objects.create(
                    name = collection_data[PC.COLLECTION_FIELD_NAME],
                    collection_type_str = str(collection_type),
                    collection_view_type_str = str(collection_view_type),
                    order_id = collection_data.get(PC.COLLECTION_FIELD_ORDER_ID, 0),
                )
                collections.append(collection)
                stats.collections_succeeded += 1
                
            except Exception as e:
                stats.collections_failed += 1
                collection_name = collection_data.get(PC.COLLECTION_FIELD_NAME, 'unknown')
                logger.error(f'Failed to create collection "{collection_name}": {e}')
                continue
                
        collection_lookup = { collection.name: collection for collection in collections }
        logger.debug(f'Created {len(collections)} collections ({stats.collections_succeeded} succeeded, {stats.collections_failed} failed)')
        return collections, collection_lookup

    def _create_entity_positions_and_paths_robust(self, entity_data_list: List[dict],
                                                  entity_lookup: Dict[str, Entity],
                                                  location_lookup: Dict[str, Location],
                                                  stats: ProfileLoadingStats):
        """Create entity positions and paths with error tracking and graceful failure handling."""
        for entity_data in entity_data_list:
            if PC.ENTITY_FIELD_NAME not in entity_data:
                continue
            
            entity_name = entity_data[PC.ENTITY_FIELD_NAME]
            if entity_name not in entity_lookup:
                continue  # Skip if entity creation failed
                
            entity = entity_lookup[entity_name]
            
            # Handle positions
            for position_data in entity_data.get(PC.ENTITY_FIELD_POSITIONS, []):
                stats.entity_positions_attempted += 1
                try:
                    location_name = position_data[PC.COMMON_FIELD_LOCATION_NAME]
                    if location_name not in location_lookup:
                        raise ValueError(f'Location "{location_name}" not found')
                    
                    location = location_lookup[location_name]
                    
                    EntityPosition.objects.create(
                        entity = entity,
                        location = location,
                        svg_x = Decimal(str(position_data[PC.COMMON_FIELD_SVG_X])),
                        svg_y = Decimal(str(position_data[PC.COMMON_FIELD_SVG_Y])),
                        svg_scale = Decimal(str(position_data.get(PC.COMMON_FIELD_SVG_SCALE, 1.0))),
                        svg_rotate = Decimal(str(position_data.get(PC.COMMON_FIELD_SVG_ROTATE, 0.0))),
                    )
                    stats.entity_positions_succeeded += 1
                    
                except Exception as e:
                    stats.entity_positions_failed += 1
                    logger.error(f'Failed to create position for entity "{entity_name}": {e}')
                    continue
            
            # Handle paths
            for path_data in entity_data.get(PC.ENTITY_FIELD_PATHS, []):
                stats.entity_paths_attempted += 1
                try:
                    location_name = path_data[PC.COMMON_FIELD_LOCATION_NAME]
                    if location_name not in location_lookup:
                        raise ValueError(f'Location "{location_name}" not found')
                    
                    location = location_lookup[location_name]
                    
                    EntityPath.objects.create(
                        entity = entity,
                        location = location,
                        svg_path = path_data[PC.COMMON_FIELD_SVG_PATH],
                    )
                    stats.entity_paths_succeeded += 1
                    
                except Exception as e:
                    stats.entity_paths_failed += 1
                    logger.error(f'Failed to create path for entity "{entity_name}": {e}')
                    continue
        
        logger.debug(f'Created entity positioning: {stats.entity_positions_succeeded} positions, {stats.entity_paths_succeeded} paths')
        return

    def _create_location_views_robust(self, location_data_list: List[dict], 
                                      location_lookup: Dict[str, Location],
                                      stats: ProfileLoadingStats):
        """Create location views with error tracking and graceful failure handling."""
        for location_data in location_data_list:
            location_name = location_data[PC.LOCATION_FIELD_NAME]
            if location_name not in location_lookup:
                continue  # Skip if location creation failed
                
            location = location_lookup[location_name]
            
            for view_data in location_data.get(PC.LOCATION_FIELD_VIEWS, []):
                stats.location_views_attempted += 1
                try:
                    location_view_name = view_data[PC.LOCATION_VIEW_FIELD_NAME]
                    
                    input_str = view_data[PC.LOCATION_VIEW_FIELD_TYPE_STR]
                    location_view_type = LocationViewType.from_name( input_str )
                    
                    input_str = view_data[PC.LOCATION_VIEW_FIELD_SVG_STYLE_NAME_STR]
                    svg_style_name = SvgStyleName.from_name( input_str )
                    
                    LocationView.objects.create(
                        location = location,
                        name = location_view_name,
                        location_view_type_str= str( location_view_type ),
                        svg_view_box_str = view_data[PC.LOCATION_VIEW_FIELD_SVG_VIEW_BOX_STR],
                        svg_style_name_str = str(svg_style_name),
                        svg_rotate = Decimal( str(view_data.get(PC.COMMON_FIELD_SVG_ROTATE, 0.0)) ),
                        order_id = view_data.get(PC.LOCATION_VIEW_FIELD_ORDER_ID, 0),
                    )
                    stats.location_views_succeeded += 1
                    
                except Exception as e:
                    stats.location_views_failed += 1
                    view_name = view_data.get(PC.LOCATION_VIEW_FIELD_NAME, 'unknown')
                    logger.error(f'Failed to create location view "{view_name}" for location "{location_name}": {e}')
                    continue
        
        logger.debug(f'Created {stats.location_views_succeeded} location views')
        return

    def _create_entity_views_robust(self, entity_data_list: List[dict], 
                                    entity_lookup: Dict[str, Entity],
                                    location_lookup: Dict[str, Location],
                                    stats: ProfileLoadingStats):
        """Create entity views with error tracking and graceful failure handling."""
        for entity_data in entity_data_list:
            if PC.ENTITY_FIELD_NAME not in entity_data:
                continue
                
            entity_name = entity_data[PC.ENTITY_FIELD_NAME]
            if entity_name not in entity_lookup:
                continue  # Skip if entity creation failed
                
            entity = entity_lookup[entity_name]
            
            for view_name in entity_data.get(PC.ENTITY_FIELD_VISIBLE_IN_VIEWS, []):
                stats.entity_views_attempted += 1
                try:
                    # Find the LocationView by searching all locations
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
                        stats.entity_views_succeeded += 1
                    else:
                        raise ValueError(f'LocationView "{view_name}" not found')
                        
                except Exception as e:
                    stats.entity_views_failed += 1
                    logger.error(f'Failed to create entity view for "{entity_name}" in view "{view_name}": {e}')
                    continue
        
        logger.debug(f'Created {stats.entity_views_succeeded} entity views')
        return

    def _create_collection_entities_robust(self, collection_data_list: List[dict], 
                                           collection_lookup: Dict[str, Collection],
                                           entity_lookup: Dict[str, Entity],
                                           stats: ProfileLoadingStats):
        """Create collection-entity relationships with error tracking and graceful failure handling."""
        for collection_data in collection_data_list:
            if PC.COLLECTION_FIELD_NAME not in collection_data:
                continue
                
            collection_name = collection_data[PC.COLLECTION_FIELD_NAME]
            if collection_name not in collection_lookup:
                continue  # Skip if collection creation failed
                
            collection = collection_lookup[collection_name]
            
            for order_id, entity_name in enumerate(collection_data.get(PC.COLLECTION_FIELD_ENTITIES, [])):
                stats.collection_entities_attempted += 1
                try:
                    if entity_name not in entity_lookup:
                        raise ValueError(f'Entity "{entity_name}" not found')
                    
                    entity = entity_lookup[entity_name]
                    
                    CollectionEntity.objects.create(
                        collection = collection,
                        entity = entity,
                        order_id = order_id,
                    )
                    stats.collection_entities_succeeded += 1
                    
                except Exception as e:
                    stats.collection_entities_failed += 1
                    logger.error(f'Failed to add entity "{entity_name}" to collection "{collection_name}": {e}')
                    continue
        
        logger.debug(f'Created {stats.collection_entities_succeeded} collection-entity relationships')
        return

    def _create_collection_positions_and_paths_robust(self, collection_data_list: List[dict], 
                                                      collection_lookup: Dict[str, Collection],
                                                      location_lookup: Dict[str, Location],
                                                      stats: ProfileLoadingStats):
        """Create collection positions and paths with error tracking and graceful failure handling."""
        for collection_data in collection_data_list:
            if PC.COLLECTION_FIELD_NAME not in collection_data:
                continue
                
            collection_name = collection_data[PC.COLLECTION_FIELD_NAME]
            if collection_name not in collection_lookup:
                continue  # Skip if collection creation failed
                
            collection = collection_lookup[collection_name]
            
            # Handle positions
            for position_data in collection_data.get(PC.COLLECTION_FIELD_POSITIONS, []):
                stats.collection_positions_attempted += 1
                try:
                    location_name = position_data[PC.COMMON_FIELD_LOCATION_NAME]
                    if location_name not in location_lookup:
                        raise ValueError(f'Location "{location_name}" not found')
                    
                    location = location_lookup[location_name]
                    
                    CollectionPosition.objects.create(
                        collection = collection,
                        location = location,
                        svg_x = Decimal(str(position_data[PC.COMMON_FIELD_SVG_X])),
                        svg_y = Decimal(str(position_data[PC.COMMON_FIELD_SVG_Y])),
                        svg_scale = Decimal(str(position_data.get(PC.COMMON_FIELD_SVG_SCALE, 1.0))),
                        svg_rotate = Decimal(str(position_data.get(PC.COMMON_FIELD_SVG_ROTATE, 0.0))),
                    )
                    stats.collection_positions_succeeded += 1
                    
                except Exception as e:
                    stats.collection_positions_failed += 1
                    logger.error(f'Failed to create position for collection "{collection_name}": {e}')
                    continue
            
            # Handle paths
            for path_data in collection_data.get(PC.COLLECTION_FIELD_PATHS, []):
                stats.collection_paths_attempted += 1
                try:
                    location_name = path_data[PC.COMMON_FIELD_LOCATION_NAME]
                    if location_name not in location_lookup:
                        raise ValueError(f'Location "{location_name}" not found')
                    
                    location = location_lookup[location_name]
                    
                    CollectionPath.objects.create(
                        collection=collection,
                        location=location,
                        svg_path=path_data[PC.COMMON_FIELD_SVG_PATH],
                    )
                    stats.collection_paths_succeeded += 1
                    
                except Exception as e:
                    stats.collection_paths_failed += 1
                    logger.error(f'Failed to create path for collection "{collection_name}": {e}')
                    continue
        
        logger.debug(f'Created collection positioning: {stats.collection_positions_succeeded} positions, {stats.collection_paths_succeeded} paths')
        return

    def _create_collection_views_robust(self, collection_data_list: List[dict], 
                                        collection_lookup: Dict[str, Collection],
                                        location_lookup: Dict[str, Location],
                                        stats: ProfileLoadingStats):
        """Create collection views with error tracking and graceful failure handling."""
        for collection_data in collection_data_list:
            if PC.COLLECTION_FIELD_NAME not in collection_data:
                continue
                
            collection_name = collection_data[PC.COLLECTION_FIELD_NAME]
            if collection_name not in collection_lookup:
                continue  # Skip if collection creation failed
                
            collection = collection_lookup[collection_name]
            
            for view_name in collection_data.get(PC.COLLECTION_FIELD_VISIBLE_IN_VIEWS, []):
                stats.collection_views_attempted += 1
                try:
                    # Find the LocationView by searching all locations
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
                        stats.collection_views_succeeded += 1
                    else:
                        raise ValueError(f'LocationView "{view_name}" not found')
                        
                except Exception as e:
                    stats.collection_views_failed += 1
                    logger.error(f'Failed to create collection view for "{collection_name}" in view "{view_name}": {e}')
                    continue
        
        logger.debug(f'Created {stats.collection_views_succeeded} collection views')
        return
