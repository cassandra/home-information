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
  viewbox's smaller dimension, clamped to the canonical scale bounds.
* ``path_center`` — geometric center of an existing SVG path
  string. Lives here because the *output* is a position even
  though the input is a path string.

Performs no DB writes and has no opinions about Entity vs Collection,
and no coupling to any model: callers pass in a bare ``SvgViewBox``
and receive geometry. Constants for the placement heuristic live here
as the canonical home (scale clamps live on ``SvgItemPositionBounds``).
"""

from decimal import Decimal
import math
import re
from typing import Optional, Tuple

from hi.apps.common.svg_models import SvgItemPositionBounds, SvgViewBox
from hi.hi_styles import EntityStyle


class PositionGeometry:

    DEFAULT_ICON_SIZE_PERCENT_OF_VIEWBOX = 7.5
    # Default center-to-center distance between bulk-placement grid
    # slots, as a fraction of viewbox dimension. Used as a target for
    # modest counts; large grids tighten below this to fit the
    # viewbox without clamping.
    DEFAULT_GRID_SPACING_FRACTION = 0.12
    DEFAULT_VIEWBOX_MARGIN_FRACTION = 0.05

    @classmethod
    def view_center( cls, view_box : SvgViewBox ) -> Tuple[float, float]:
        return (
            view_box.x + ( view_box.width / 2.0 ),
            view_box.y + ( view_box.height / 2.0 ),
        )

    @classmethod
    def grid_slot( cls,
                   view_box       : SvgViewBox,
                   grid_index     : int,
                   grid_total     : int ) -> Tuple[float, float]:
        center_x, center_y = cls.view_center( view_box )

        if grid_total <= 1:
            return center_x, center_y

        # Column count adapts to ``grid_total`` and viewbox aspect:
        # wider views get more columns, taller views get more rows.
        # Cap at ``grid_total`` so a small batch in a wide view does
        # not produce trailing empty cells that skew item centering.
        aspect_ratio = (
            view_box.width / view_box.height if view_box.height > 0 else 1.0
        )
        columns = min(
            grid_total,
            max( 2, math.ceil( math.sqrt( grid_total * aspect_ratio ) ) ),
        )
        rows = ( grid_total + columns - 1 ) // columns

        column_index = grid_index % columns
        row_index = grid_index // columns

        column_offset = column_index - ( ( columns - 1 ) / 2.0 )
        row_offset = row_index - ( ( rows - 1 ) / 2.0 )

        # Default spacing for modest counts; for grids large enough
        # that the default would overflow the viewbox (minus margin),
        # tighten so the full grid fits without clamping. Items may
        # still overlap each other at very large counts — that is
        # the natural consequence of "user added many items at once,"
        # not a layout failure.
        default_spacing_x = view_box.width * cls.DEFAULT_GRID_SPACING_FRACTION
        default_spacing_y = view_box.height * cls.DEFAULT_GRID_SPACING_FRACTION
        margin = cls.DEFAULT_VIEWBOX_MARGIN_FRACTION
        usable_width = view_box.width * ( 1.0 - ( 2.0 * margin ) )
        usable_height = view_box.height * ( 1.0 - ( 2.0 * margin ) )

        spacing_x = (
            min( default_spacing_x, usable_width / ( columns - 1 ) )
            if columns > 1 else 0.0
        )
        spacing_y = (
            min( default_spacing_y, usable_height / ( rows - 1 ) )
            if rows > 1 else 0.0
        )

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
                            view_box : SvgViewBox ) -> Decimal:
        """Default scale for an icon entity: ~10% of the viewbox's
        smaller dimension, multiplied by the entity type's opt-in
        size factor (defaults to 1.0; only entity types with
        meaningfully different intended layout sizes — e.g.
        Automobile — override it), clamped to the canonical
        SvgItemPositionBounds.DEFAULT_MIN_SCALE / DEFAULT_MAX_SCALE."""
        icon_view_box = EntityStyle.get_svg_icon_viewbox( entity.entity_type )

        icon_max_dimension = max( icon_view_box.width, icon_view_box.height )
        if icon_max_dimension <= 0:
            return Decimal( str( SvgItemPositionBounds.DEFAULT_MIN_SCALE ) )

        viewbox_min_dimension = min( view_box.width, view_box.height )
        size_fraction = cls.DEFAULT_ICON_SIZE_PERCENT_OF_VIEWBOX / 100.0
        size_factor = EntityStyle.get_icon_size_factor( entity.entity_type )
        target_icon_size = viewbox_min_dimension * size_fraction * size_factor
        scale = target_icon_size / icon_max_dimension

        scale = max( SvgItemPositionBounds.DEFAULT_MIN_SCALE,
                     min( scale, SvgItemPositionBounds.DEFAULT_MAX_SCALE ) )

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
