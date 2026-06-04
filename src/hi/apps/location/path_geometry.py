from typing import Optional, Tuple

from hi.apps.common.svg_models import SvgRadius, SvgViewBox
from hi.apps.entity.enums import EntityType
from hi.apps.collection.enums import CollectionType


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
    def get_collection_radius(cls, collection_type: CollectionType) -> SvgRadius:
        """Get collection-specific radius configuration for path generation.
        
        This preserves the existing collection-specific sizing configurations
        from hi_styles.py CollectionTypePathInitialRadius for future extensibility.
        """
        collection_radius_configs = {
            # Currently empty but preserved for future collection types
            # Example: CollectionType.SOME_TYPE: SvgRadius(x=40, y=20),
        }
        
        return collection_radius_configs.get(collection_type, SvgRadius(x=None, y=None))
    
    @classmethod
    def create_default_path_string(cls,
                                   view_box: SvgViewBox,
                                   is_path_closed: bool,
                                   center_x: Optional[float] = None,
                                   center_y: Optional[float] = None,
                                   entity_type: Optional[EntityType] = None,
                                   collection_type: Optional[CollectionType] = None,
                                   radius_multiplier: float = 1.0) -> str:
        """Create a default SVG path string with configurable positioning and sizing.

        Args:
            view_box: SvgViewBox for calculating dimensions
            is_path_closed: Whether to create closed (rectangle) or open (line) path
            center_x: X position for path center (defaults to view center)
            center_y: Y position for path center (defaults to view center)
            entity_type: EntityType for entity-specific radius (optional)
            collection_type: CollectionType for collection-specific radius (optional)
            radius_multiplier: Multiplier for radius size (e.g., 2.0 for double size)

        Returns:
            SVG path string
        """
        # Default to view center if no center provided
        if center_x is None:
            center_x = view_box.x + (view_box.width / 2.0)
        if center_y is None:
            center_y = view_box.y + (view_box.height / 2.0)

        # Get type-specific radius if provided, otherwise use default calculation
        radius_x = None
        radius_y = None

        if entity_type:
            entity_radius = cls.get_entity_radius(entity_type)
            radius_x = entity_radius.x
            radius_y = entity_radius.y
        elif collection_type:
            collection_radius = cls.get_collection_radius(collection_type)
            radius_x = collection_radius.x
            radius_y = collection_radius.y

        # Apply default calculation for None values
        if radius_x is None:
            radius_x = view_box.width * (cls.DEFAULT_RADIUS_PERCENT / 50.0)
        if radius_y is None:
            radius_y = view_box.height * (cls.DEFAULT_RADIUS_PERCENT / 50.0)
            
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

    @classmethod
    def create_coverage_triangle_path_string(
            cls,
            view_box      : SvgViewBox,
            apex_x        : float,
            apex_y        : float,
            direction     : Tuple[float, float],
    ) -> str:
        """Closed-path SVG triangle representing a directional coverage
        area. Apex at ``(apex_x, apex_y)``; base extends along the
        ``direction`` unit vector. Sized to roughly match the default
        rectangle path so the visual scale is consistent with other
        auto-placed Area delegates.
        """
        dx, dy = direction
        # Both dimensions scaled from viewbox so the triangle reads at
        # the same magnitude as the default rectangle path
        # (DEFAULT_RADIUS_PERCENT controls both).
        size_fraction = cls.DEFAULT_RADIUS_PERCENT / 50.0
        height = view_box.width * size_fraction * 2.0
        base_half_width = view_box.height * size_fraction

        # Perpendicular to direction (rotate 90° counter-clockwise in
        # SVG coordinates).
        perp_dx, perp_dy = -dy, dx

        # Base center
        base_cx = apex_x + ( dx * height )
        base_cy = apex_y + ( dy * height )

        # Base corners
        c1x = base_cx + ( perp_dx * base_half_width )
        c1y = base_cy + ( perp_dy * base_half_width )
        c2x = base_cx - ( perp_dx * base_half_width )
        c2y = base_cy - ( perp_dy * base_half_width )

        return f'M {apex_x},{apex_y} L {c1x},{c1y} L {c2x},{c2y} Z'
