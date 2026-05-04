"""
Position geometry: "where in the SVG" math.

Pure-functional helpers that answer the question "where, in a
Location's SVG coordinate space, should something go?" — siblings
to ``PathGeometry`` (which answers "what does the path string look
like once you've decided where").

* ``view_center`` — the center of the current viewbox.
* ``grid_slot`` — one slot of a centered grid laid over the
  viewbox; used to lay out a group of entities arriving together.
* ``clamp_to_viewbox`` — keep a point inside the viewbox margin.
* ``default_icon_scale`` — entity-aware icon scale: ~10% of the
  viewbox's smaller dimension, clamped to the location's
  svg_position_bounds.
* ``path_center`` — geometric center of an existing SVG path
  string. Lives here because the *output* is a position even
  though the input is a path string.

Performs no DB writes and has no opinions about Entity vs
Collection: callers in either domain pass in a ``LocationView`` (or
view box) and receive geometry. Constants for the placement
heuristic live here as the canonical home.
"""

from decimal import Decimal
import re
from typing import Optional, Tuple

from hi.apps.location.models import LocationView
from hi.hi_styles import EntityStyle


class PositionGeometry:

    DEFAULT_ICON_SIZE_PERCENT_OF_VIEWBOX = 10.0
    DEFAULT_GRID_COLUMNS = 4
    DEFAULT_GRID_SPACING_FRACTION = 0.18
    DEFAULT_VIEWBOX_MARGIN_FRACTION = 0.05

    @classmethod
    def view_center( cls, location_view : LocationView ) -> Tuple[float, float]:
        view_box = location_view.svg_view_box
        return (
            view_box.x + ( view_box.width / 2.0 ),
            view_box.y + ( view_box.height / 2.0 ),
        )

    @classmethod
    def grid_slot( cls,
                   location_view  : LocationView,
                   grid_index     : int,
                   grid_total     : int ) -> Tuple[float, float]:
        view_box = location_view.svg_view_box
        center_x, center_y = cls.view_center( location_view )

        if grid_total <= 1:
            return center_x, center_y

        columns = min( max( 2, cls.DEFAULT_GRID_COLUMNS ), grid_total )
        rows = ( grid_total + columns - 1 ) // columns

        column_index = grid_index % columns
        row_index = grid_index // columns

        column_offset = column_index - ( ( columns - 1 ) / 2.0 )
        row_offset = row_index - ( ( rows - 1 ) / 2.0 )

        spacing_x = view_box.width * cls.DEFAULT_GRID_SPACING_FRACTION
        spacing_y = view_box.height * cls.DEFAULT_GRID_SPACING_FRACTION

        svg_x = center_x + ( column_offset * spacing_x )
        svg_y = center_y + ( row_offset * spacing_y )

        return cls.clamp_to_viewbox(
            svg_x = svg_x,
            svg_y = svg_y,
            view_box = view_box,
        )

    @classmethod
    def clamp_to_viewbox( cls,
                          svg_x    : float,
                          svg_y    : float,
                          view_box ) -> Tuple[float, float]:
        margin_x = view_box.width * cls.DEFAULT_VIEWBOX_MARGIN_FRACTION
        margin_y = view_box.height * cls.DEFAULT_VIEWBOX_MARGIN_FRACTION

        min_x = view_box.x + margin_x
        max_x = ( view_box.x + view_box.width ) - margin_x
        min_y = view_box.y + margin_y
        max_y = ( view_box.y + view_box.height ) - margin_y

        if min_x > max_x:
            min_x = max_x = view_box.x + ( view_box.width / 2.0 )
        if min_y > max_y:
            min_y = max_y = view_box.y + ( view_box.height / 2.0 )

        clamped_x = max( min_x, min( svg_x, max_x ) )
        clamped_y = max( min_y, min( svg_y, max_y ) )
        return clamped_x, clamped_y

    @classmethod
    def default_icon_scale( cls,
                            entity,
                            location_view : LocationView ) -> Decimal:
        """Default scale for an icon entity: ~10% of the viewbox's
        smaller dimension, clamped to the location's
        svg_position_bounds.min_scale / max_scale."""
        view_box = location_view.svg_view_box
        icon_view_box = EntityStyle.get_svg_icon_viewbox( entity.entity_type )

        icon_max_dimension = max( icon_view_box.width, icon_view_box.height )
        if icon_max_dimension <= 0:
            return Decimal( str( location_view.location.svg_position_bounds.min_scale ) )

        viewbox_min_dimension = min( view_box.width, view_box.height )
        size_fraction = cls.DEFAULT_ICON_SIZE_PERCENT_OF_VIEWBOX / 100.0
        target_icon_size = viewbox_min_dimension * size_fraction
        scale = target_icon_size / icon_max_dimension

        position_bounds = location_view.location.svg_position_bounds
        scale = max( position_bounds.min_scale,
                     min( scale, position_bounds.max_scale ) )

        return Decimal( str( scale ) )

    @classmethod
    def path_center( cls, svg_path : str ) -> Tuple[Optional[float], Optional[float]]:
        """Geometric center of an SVG path: average of all extracted
        coordinate pairs. Returns ``(None, None)`` for malformed or
        too-short input."""
        try:
            numbers = re.findall( r'[-+]?(?:\d*\.\d+|\d+)', svg_path )
            if len( numbers ) < 4:
                return None, None

            coords = [ float( n ) for n in numbers ]
            x_coords = [ coords[i] for i in range( 0, len( coords ), 2 ) ]
            y_coords = [ coords[i] for i in range( 1, len( coords ), 2 ) ]

            if not x_coords or not y_coords:
                return None, None

            return (
                sum( x_coords ) / len( x_coords ),
                sum( y_coords ) / len( y_coords ),
            )

        except (ValueError, IndexError, ZeroDivisionError):
            return None, None
