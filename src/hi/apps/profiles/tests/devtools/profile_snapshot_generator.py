import json
import logging
import os
import shutil
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Any, Optional

from django.conf import settings
from django.core.files.storage import default_storage

from hi.apps.entity.models import Entity
from hi.apps.location.models import Location
from hi.apps.collection.models import Collection

from hi.apps.profiles.enums import ProfileType
import hi.apps.profiles.constants as PC

logger = logging.getLogger(__name__)


class ProfileSnapshotGenerator:
    """
    Generates JSON profile specifications from current database state.
    
    Creates profile data files in the same format used by ProfileManager for
    loading, allowing developers to capture UI-configured layouts as templates.
    """
    
    def generate_snapshot(self, profile_type: ProfileType, output_to_tmp: bool = True) -> Path:
        """
        Generate a JSON snapshot of the current database state.
        
        Args:
            profile_type: The ProfileType enum to use for naming
            output_to_tmp: If True, writes to /tmp; if False, overwrites existing profile data file
            
        Returns:
            Path to the generated JSON file
            
        Raises:
            ValueError: If database is empty (no locations)
        """
        if not Location.objects.exists():
            raise ValueError("Cannot generate snapshot from empty database")
        
        profile_data = self._build_profile_data(profile_type)
        
        if output_to_tmp:
            output_path = Path('/tmp') / profile_type.json_filename()
        else:
            output_path = self._get_profile_json_path(profile_type)
        
        with open(output_path, 'w') as f:
            json.dump(profile_data, f, indent=2, default=str)
        
        # Copy SVG fragments to assets if writing to real profile location
        if not output_to_tmp:
            self._copy_svg_fragments_to_assets(profile_data)
        
        logger.info(f"Generated profile snapshot to {output_path}")
        return output_path
    
    def _get_assets_base_directory(self) -> Path:
        """
        Get the base directory for profile assets.
        
        This is separated into its own method to allow easy overriding in tests.
        
        Returns:
            Path: The base directory containing profile assets
        """
        return Path(__file__).parent.parent.parent / 'assets'
    
    def _copy_svg_fragments_to_assets(self, profile_data: Dict[str, Any]) -> None:
        """
        Copy SVG fragment files from MEDIA_ROOT to profile assets directory.
        
        This copies the SVG fragments referenced in the profile data to the assets
        directory so they can be packaged with the application for distribution.
        
        Args:
            profile_data: The profile data containing location SVG references
            
        Raises:
            FileNotFoundError: If referenced SVG fragment files don't exist in MEDIA_ROOT
            Exception: For other file system errors during copying
        """
        locations_data = profile_data.get(PC.PROFILE_FIELD_LOCATIONS, [])
        assets_base_dir = self._get_assets_base_directory()
        
        for location_data in locations_data:
            svg_fragment_filename = location_data.get(PC.LOCATION_FIELD_SVG_FRAGMENT_FILENAME)
            if not svg_fragment_filename:
                continue
                
            # Source: MEDIA_ROOT
            source_path = os.path.join(settings.MEDIA_ROOT, svg_fragment_filename)
            
            # Destination: profile assets directory
            destination_path = assets_base_dir / svg_fragment_filename
            
            try:
                if not os.path.exists(source_path):
                    raise FileNotFoundError(f'SVG fragment file not found in MEDIA_ROOT: {source_path}')
                
                # Ensure destination directory exists
                destination_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Copy the file
                shutil.copy2(source_path, str(destination_path))
                logger.debug(f'Copied SVG fragment to assets: {source_path} -> {destination_path}')
                
            except Exception as e:
                logger.error(f'Failed to copy SVG fragment {svg_fragment_filename} to assets: {e}')
                raise
                
        logger.debug('SVG fragment files copied to assets successfully')
    
    def _get_profile_json_path(self, profile_type: ProfileType) -> Path:
        """Get the path to the profile JSON file in the data directory."""
        import hi.apps.profiles
        
        module_dir = Path(hi.apps.profiles.__file__).parent
        return module_dir / 'data' / profile_type.json_filename()
    
    def _build_profile_data(self, profile_type: ProfileType) -> Dict[str, Any]:
        """Build the complete profile data structure from database."""
        return {
            PC.PROFILE_FIELD_NAME: profile_type.label,
            PC.PROFILE_FIELD_DESCRIPTION: "Generated snapshot from current database state",
            PC.PROFILE_FIELD_LOCATIONS: self._extract_locations(),
            PC.PROFILE_FIELD_COLLECTIONS: self._extract_collections(),
            PC.PROFILE_FIELD_ENTITIES: self._extract_entities(),
        }
    
    def _extract_locations(self) -> List[Dict[str, Any]]:
        """Extract location data with their views."""
        locations_data = []
        
        for location in Location.objects.order_by('order_id'):
            location_dict = {
                PC.LOCATION_FIELD_NAME: location.name,
                PC.LOCATION_FIELD_SVG_FRAGMENT_FILENAME: location.svg_fragment_filename,
                PC.LOCATION_FIELD_SVG_VIEW_BOX_STR: location.svg_view_box_str,
                PC.LOCATION_FIELD_ORDER_ID: location.order_id,
                PC.LOCATION_FIELD_VIEWS: []
            }
            
            # Add location views
            for view in location.views.order_by('order_id'):
                view_dict = {
                    PC.LOCATION_VIEW_FIELD_NAME: view.name,
                    PC.LOCATION_VIEW_FIELD_TYPE_STR: str(view.location_view_type),
                    PC.LOCATION_VIEW_FIELD_SVG_VIEW_BOX_STR: view.svg_view_box_str,
                    PC.LOCATION_VIEW_FIELD_SVG_STYLE_NAME_STR: str(view.svg_style_name),
                    PC.LOCATION_VIEW_FIELD_ORDER_ID: view.order_id
                }
                location_dict[PC.LOCATION_FIELD_VIEWS].append(view_dict)
            
            locations_data.append(location_dict)
        
        return locations_data
    
    def _extract_collections(self) -> List[Dict[str, Any]]:
        """Extract collection data with their entities and positions."""
        collections_data = []
        
        # Track which structural patterns we've documented
        seen_collection_patterns = set()
        
        for collection in Collection.objects.order_by('order_id'):
            collection_dict = {
                PC.COLLECTION_FIELD_NAME: collection.name,
                PC.COLLECTION_FIELD_TYPE_STR: str(collection.collection_type),
                PC.COLLECTION_FIELD_VIEW_TYPE_STR: str(collection.collection_view_type),
                PC.COLLECTION_FIELD_ORDER_ID: collection.order_id,
                PC.COLLECTION_FIELD_ENTITIES: []
            }
            
            # Add comment for first example of each structural pattern
            comment = self._get_collection_pattern_comment(collection, seen_collection_patterns)
            if comment:
                collection_dict[PC.COMMON_FIELD_COMMENT] = comment
            
            # Add collection entities
            for collection_entity in collection.entities.select_related('entity').order_by('order_id'):
                collection_dict[PC.COLLECTION_FIELD_ENTITIES].append(collection_entity.entity.name)
            
            # Add collection positions
            positions = []
            for position in collection.positions.select_related('location'):
                position_dict = {
                    PC.COMMON_FIELD_LOCATION_NAME: position.location.name,
                    PC.COMMON_FIELD_SVG_X: float(position.svg_x),
                    PC.COMMON_FIELD_SVG_Y: float(position.svg_y),
                }
                if position.svg_scale != Decimal('1.0'):
                    position_dict[PC.COMMON_FIELD_SVG_SCALE] = float(position.svg_scale)
                if position.svg_rotate != Decimal('0.0'):
                    position_dict[PC.COMMON_FIELD_SVG_ROTATE] = float(position.svg_rotate)
                positions.append(position_dict)
            
            if positions:
                collection_dict[PC.COLLECTION_FIELD_POSITIONS] = positions
            
            # Add collection paths
            paths = []
            for path in collection.paths.select_related('location'):
                path_dict = {
                    PC.COMMON_FIELD_LOCATION_NAME: path.location.name,
                    PC.COMMON_FIELD_SVG_PATH: path.svg_path,
                }
                paths.append(path_dict)
            
            if paths:
                collection_dict[PC.COLLECTION_FIELD_PATHS] = paths
            
            # Add visible_in_views
            visible_views = []
            for view in collection.collection_views.select_related('location_view'):
                visible_views.append(view.location_view.name)
            
            if visible_views:
                collection_dict[PC.COLLECTION_FIELD_VISIBLE_IN_VIEWS] = visible_views
            
            collections_data.append(collection_dict)
        
        return collections_data
    
    def _extract_entities(self) -> List[Dict[str, Any]]:
        """Extract entity data with their positions and visibility."""
        entities_data = []
        
        # Track which structural patterns we've documented
        seen_entity_patterns = set()
        
        # Get all entities not in collections first, then those in collections
        all_entities = Entity.objects.order_by('name')
        
        for entity in all_entities:
            entity_dict = {
                PC.ENTITY_FIELD_NAME: entity.name,
                PC.ENTITY_FIELD_TYPE_STR: str(entity.entity_type),
            }
            
            # Add comment for first example of each structural pattern
            comment = self._get_entity_pattern_comment(entity, seen_entity_patterns)
            if comment:
                entity_dict[PC.COMMON_FIELD_COMMENT] = comment
            
            # Add entity positions
            positions = []
            for position in entity.positions.select_related('location'):
                position_dict = {
                    PC.COMMON_FIELD_LOCATION_NAME: position.location.name,
                    PC.COMMON_FIELD_SVG_X: float(position.svg_x),
                    PC.COMMON_FIELD_SVG_Y: float(position.svg_y),
                }
                if position.svg_scale != Decimal('1.0'):
                    position_dict[PC.COMMON_FIELD_SVG_SCALE] = float(position.svg_scale)
                if position.svg_rotate != Decimal('0.0'):
                    position_dict[PC.COMMON_FIELD_SVG_ROTATE] = float(position.svg_rotate)
                positions.append(position_dict)
            
            if positions:
                entity_dict[PC.ENTITY_FIELD_POSITIONS] = positions
            
            # Add entity paths
            paths = []
            for path in entity.paths.select_related('location'):
                path_dict = {
                    PC.COMMON_FIELD_LOCATION_NAME: path.location.name,
                    PC.COMMON_FIELD_SVG_PATH: path.svg_path,
                }
                paths.append(path_dict)
            
            if paths:
                entity_dict[PC.ENTITY_FIELD_PATHS] = paths
            
            # Add visible_in_views
            visible_views = []
            for view in entity.entity_views.select_related('location_view'):
                visible_views.append(view.location_view.name)
            
            if visible_views:
                entity_dict[PC.ENTITY_FIELD_VISIBLE_IN_VIEWS] = visible_views
            
            entities_data.append(entity_dict)
        
        return entities_data
    
    def _get_entity_pattern_comment(self, entity, seen_patterns: set) -> Optional[str]:
        """Get comment for entity if it's the first example of a structural pattern."""
        # Check if entity is part of any collections
        if entity.collections.exists() and 'collection_member' not in seen_patterns:
            seen_patterns.add('collection_member')
            return PC.ENTITY_COMMENT_COLLECTION_MEMBER
        
        # Check if entity has paths (EntityPath)
        if entity.paths.exists() and 'path_entity' not in seen_patterns:
            seen_patterns.add('path_entity')
            return PC.ENTITY_COMMENT_PATH_ENTITY
        
        # Check if entity has positions (EntityPosition) - most common case
        if entity.positions.exists() and 'icon_positioned' not in seen_patterns:
            seen_patterns.add('icon_positioned')
            return PC.ENTITY_COMMENT_ICON_POSITIONED
        
        return None
    
    def _get_collection_pattern_comment(self, collection, seen_patterns: set) -> Optional[str]:
        """Get comment for collection if it's the first example of a structural pattern."""
        # Check if collection has paths
        if collection.paths.exists() and 'path_based' not in seen_patterns:
            seen_patterns.add('path_based')
            return PC.COLLECTION_COMMENT_PATH_BASED
        
        # Check if collection has positions
        if collection.positions.exists() and 'with_positioning' not in seen_patterns:
            seen_patterns.add('with_positioning')
            return PC.COLLECTION_COMMENT_WITH_POSITIONING
        
        return None
    
