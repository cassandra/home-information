from hi.apps.common.singleton import Singleton
from hi.apps.common.svg_models import SvgIconItem, SvgPathItem, SvgViewBox
from hi.apps.location.models import (
    LocationItemModelMixin,
    LocationItemPositionModel,
    LocationItemPathModel,
)


class SvgItemFactory( Singleton ):

    def __init_singleton__(self):
        return

    def create_svg_icon_item( self,
                              item     : LocationItemModelMixin,
                              position : LocationItemPositionModel ) -> SvgIconItem:
        return SvgIconItem(
            html_id = item.html_id,
            position_x = float( position.svg_x ),
            position_y = float( position.svg_y ),
            rotate = float( position.svg_rotate ),
            scale = float( position.svg_scale ),
            template_name = 'entity/svg/type.other.svg',
            bounding_box = SvgViewBox( x = 0, y = 0, width = 32, height = 32 ),
        )

    def create_svg_path_item( self,
                              item  : LocationItemModelMixin,
                              path  : LocationItemPathModel ) -> SvgPathItem:
        return SvgPathItem(
            html_id = item.html_id,
            svg_path = path.svg_path,
            stroke_color = '#40f040',
            stroke_width = 5.0,
            fill_color = 'none',
        )
