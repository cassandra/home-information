from hi.apps.common.singleton import Singleton
from hi.apps.common.svg_models import SvgIconItem, SvgPathItem, SvgStatusStyle, SvgViewBox
from hi.apps.collection.models import Collection
from hi.apps.entity.models import Entity

from hi.hi_styles import CollectionStyle, EntityStyle, ItemStyle

from .enums import SvgItemType
from .models import (
    LocationItemModelMixin,
    LocationItemPositionModel,
    LocationItemPathModel,
    LocationView,
)


class SvgItemFactory( Singleton ):

    NEW_PATH_RADIUS_PERCENT = 5.0  # Preferrable if this matches Javascript new path sizing.

    def __init_singleton__(self):
        return

    def create_svg_icon_item( self,
                              item              : LocationItemModelMixin,
                              position          : LocationItemPositionModel,
                              css_class         : str,
                              svg_status_style  : SvgStatusStyle              = None ) -> SvgIconItem:
        if not svg_status_style:
            svg_status_style = ItemStyle.get_default_svg_icon_status_style()

        if isinstance( item, Entity ):
            template_name = EntityStyle.get_svg_icon_template_name( entity_type = item.entity_type )
            viewbox = EntityStyle.get_svg_icon_viewbox( entity_type = item.entity_type )
        else:
            template_name = ItemStyle.get_default_svg_icon_template_name()
            viewbox = ItemStyle.ItemStyle.get_default_svg_icon_viewbox()

        return SvgIconItem(
            html_id = item.html_id,
            css_class = css_class,
            status_value = svg_status_style.status_value,
            position_x = float( position.svg_x ),
            position_y = float( position.svg_y ),
            rotate = float( position.svg_rotate ),
            scale = float( position.svg_scale ),
            template_name = template_name,
            bounding_box = SvgViewBox( x = 0,
                                       y = 0,
                                       width = viewbox.width,
                                       height = viewbox.height ),
        )

    def create_svg_path_item( self,
                              item              : LocationItemModelMixin,
                              path              : LocationItemPathModel,
                              css_class         : str,
                              svg_status_style  : SvgStatusStyle              = None  ) -> SvgPathItem:
        if not svg_status_style:
            if isinstance( item, Entity ):
                svg_status_style = EntityStyle.get_svg_path_status_style( item.entity_type )
            elif isinstance( item, Collection ):
                svg_status_style = CollectionStyle.get_svg_path_status_style( item.collection_type )
            if not svg_status_style:
                svg_status_style = ItemStyle.get_default_svg_path_status_style()

        return SvgPathItem(
            html_id = item.html_id,
            css_class = css_class,
            svg_path = path.svg_path,
            stroke_color = svg_status_style.stroke_color,
            stroke_width = svg_status_style.stroke_width,
            stroke_dasharray = svg_status_style.stroke_dasharray,
            fill_color = svg_status_style.fill_color,
            fill_opacity = svg_status_style.fill_opacity,
        )

    def get_svg_item_type( self, obj ) -> SvgItemType:
        if isinstance( obj, Entity ):
            entity_type = obj.entity_type

            if entity_type in EntityStyle.EntityTypeOpenPaths:
                return SvgItemType.OPEN_PATH

            if entity_type in EntityStyle.EntityTypeClosedPaths:
                return SvgItemType.CLOSED_PATH
                
            return SvgItemType.ICON
        
        elif isinstance( obj, Collection ):
            # Future colection types could leverage other SVG item types
            return SvgItemType.CLOSED_PATH
            
        else:
            return SvgItemType.ICON
        
    def get_default_svg_path_str( self,
                                  location_view   : LocationView,
                                  is_path_closed  : bool           ) -> str:

        # Note that this server-side creation of a new path is just one
        # place new paths can be created. During client-side path editing,
        # the Javascript code also uses logic to add new path segments.
        # These do not have to behave identical, but it is preferrable for
        # there to be some consistency.
        
        # Default display a line or rectangle in middle of current view with radius X% of viewbox
        center_x = location_view.svg_view_box.x + ( location_view.svg_view_box.width / 2.0 )
        center_y = location_view.svg_view_box.y + ( location_view.svg_view_box.height / 2.0 )
        radius_x = location_view.svg_view_box.width * ( self.NEW_PATH_RADIUS_PERCENT / 100.0 )
        radius_y = location_view.svg_view_box.height * ( self.NEW_PATH_RADIUS_PERCENT / 100.0 )

        if is_path_closed:
            top_left_x = center_x - radius_x
            top_left_y = center_y - radius_y
            top_right_x = center_x + radius_x
            top_right_y = center_y - radius_y
            bottom_right_x = center_x + radius_x
            bottom_right_y = center_y + radius_y
            bottom_left_x = center_x - radius_x
            bottom_left_y = center_y + radius_y
            svg_path = f'M {top_left_x},{top_left_y} L {top_right_x},{top_right_y} L {bottom_right_x},{bottom_right_y} L {bottom_left_x},{bottom_left_y} Z'
        else:
            start_x = center_x - radius_x
            start_y = center_y
            end_x = start_x + radius_x
            end_y = start_y
            svg_path = f'M {start_x},{start_y} L {end_x},{end_y}'

        return svg_path
    
