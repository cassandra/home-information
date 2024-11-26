from hi.apps.common.singleton import Singleton
from hi.apps.common.svg_models import SvgIconItem, SvgPathItem, SvgViewBox
from hi.apps.collection.models import Collection
from hi.apps.entity.enums import EntityType
from hi.apps.entity.models import Entity

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
                              item       : LocationItemModelMixin,
                              position   : LocationItemPositionModel,
                              css_class  : str ) -> SvgIconItem:

        return SvgIconItem(
            html_id = item.html_id,
            css_class = css_class,
            position_x = float( position.svg_x ),
            position_y = float( position.svg_y ),
            rotate = float( position.svg_rotate ),
            scale = float( position.svg_scale ),
            template_name = 'entity/svg/type.other.svg',
            bounding_box = SvgViewBox( x = 0, y = 0, width = 32, height = 32 ),
        )

    def create_svg_path_item( self,
                              item       : LocationItemModelMixin,
                              path       : LocationItemPathModel,
                              css_class  : str ) -> SvgPathItem:

        return SvgPathItem(
            html_id = item.html_id,
            css_class = css_class,
            svg_path = path.svg_path,
            stroke_color = '#40f040',
            stroke_width = 5.0,
            fill_color = 'white',
            fill_opacity = 0.0,
        )

    def get_svg_item_type( self, obj ) -> SvgItemType:
        if isinstance( obj, Entity ):
            entity_type = obj.entity_type

            if entity_type in [ EntityType.CONTROL_WIRE,
                                EntityType.ELECTRIC_WIRE,
                                EntityType.SEWER_LINE,
                                EntityType.SPRINKLER_WIRE,
                                EntityType.TELECOM_WIRE,
                                EntityType.WASTE_PIPE,
                                EntityType.WATER_LINE, ]:
                return SvgItemType.OPEN_PATH

            if entity_type in [ EntityType.AREA ]:
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
    
