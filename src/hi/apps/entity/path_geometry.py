from decimal import Decimal
from typing import Optional, Tuple

from hi.apps.common.svg_models import SvgRadius, SvgViewBox
from hi.apps.entity.enums import EntityType
from hi.apps.location.models import LocationView


class PathGeometry:
    """Pure geometric utility for creating default SVG path strings.
    
    This utility is independent of SVG items and visual concerns - it only
    handles the mathematical calculations for generating path geometry.
    """
    
    DEFAULT_RADIUS_PERCENT = 5.0  # Match SvgItemFactory.NEW_PATH_RADIUS_PERCENT
    
    @classmethod
    def get_entity_radius(cls, entity_type: EntityType) -> SvgRadius:
        """Get entity-specific radius configuration for path generation.
        
        This preserves the existing entity-specific sizing configurations
        that were previously in hi_styles.py EntityTypePathInitialRadius.
        """
        entity_radius_configs = {
            EntityType.APPLIANCE: SvgRadius(x=32, y=32),
            EntityType.DOOR: SvgRadius(x=None, y=16),
            EntityType.FURNITURE: SvgRadius(x=64, y=32),
            EntityType.WALL: SvgRadius(x=16, y=None),
            EntityType.WINDOW: SvgRadius(x=None, y=16.0),
        }
        
        return entity_radius_configs.get(entity_type, SvgRadius(x=None, y=None))
    
    @classmethod
    def create_default_path_string(cls,
                                   location_view: LocationView,
                                   is_path_closed: bool,
                                   center_x: Optional[float] = None,
                                   center_y: Optional[float] = None,
                                   entity_type: Optional[EntityType] = None,
                                   radius_multiplier: float = 1.0) -> str:
        """Create a default SVG path string with configurable positioning and sizing.
        
        Args:
            location_view: LocationView for calculating dimensions
            is_path_closed: Whether to create closed (rectangle) or open (line) path
            center_x: X position for path center (defaults to view center)
            center_y: Y position for path center (defaults to view center)  
            entity_type: EntityType for entity-specific radius (optional)
            radius_multiplier: Multiplier for radius size (e.g., 2.0 for double size)
            
        Returns:
            SVG path string
        """
        # Default to view center if no center provided
        if center_x is None:
            center_x = location_view.svg_view_box.x + (location_view.svg_view_box.width / 2.0)
        if center_y is None:
            center_y = location_view.svg_view_box.y + (location_view.svg_view_box.height / 2.0)
        
        # Get entity-specific radius if provided, otherwise use default calculation
        if entity_type:
            entity_radius = cls.get_entity_radius(entity_type)
            radius_x = entity_radius.x
            radius_y = entity_radius.y
        else:
            radius_x = None
            radius_y = None
        
        # Apply default calculation for None values
        if radius_x is None:
            radius_x = location_view.svg_view_box.width * (cls.DEFAULT_RADIUS_PERCENT / 50.0)
        if radius_y is None:
            radius_y = location_view.svg_view_box.height * (cls.DEFAULT_RADIUS_PERCENT / 50.0)
            
        # Apply radius multiplier
        radius_x *= radius_multiplier
        radius_y *= radius_multiplier
        
        if is_path_closed:
            # Rectangle for closed paths
            top_left_x = center_x - radius_x
            top_left_y = center_y - radius_y
            top_right_x = center_x + radius_x
            top_right_y = center_y - radius_y
            bottom_right_x = center_x + radius_x
            bottom_right_y = center_y + radius_y
            bottom_left_x = center_x - radius_x
            bottom_left_y = center_y + radius_y
            return f'M {top_left_x},{top_left_y} L {top_right_x},{top_right_y} L {bottom_right_x},{bottom_right_y} L {bottom_left_x},{bottom_left_y} Z'
        else:
            # Line for open paths
            start_x = center_x - radius_x
            start_y = center_y
            end_x = center_x + radius_x
            end_y = center_y
            return f'M {start_x},{start_y} L {end_x},{end_y}'