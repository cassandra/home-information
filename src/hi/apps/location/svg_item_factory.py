from hi.apps.common.singleton import Singleton
from hi.apps.location.path_geometry import PathGeometry
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

    def get_display_only_svg_icon_item( self, entity : Entity ) -> SvgIconItem:
        template_name = EntityStyle.get_svg_icon_template_name( entity_type = entity.entity_type )
        svg_view_box = EntityStyle.get_svg_icon_viewbox( entity_type = entity.entity_type )
        
        return SvgIconItem(
            html_id = None,
            css_class = None,
            status_value = None,
            position_x = None,
            position_y = None,
            rotate = None,
            scale = None ,
            template_name = template_name,
            bounding_box = svg_view_box,
        )
    
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
            viewbox = ItemStyle.get_default_svg_icon_viewbox()

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

            if entity_type.requires_open_path():
                return SvgItemType.OPEN_PATH

            if entity_type.requires_closed_path():
                return SvgItemType.CLOSED_PATH
                
            return SvgItemType.ICON
        
        elif isinstance( obj, Collection ):
            # Future colection types could leverage other SVG item types
            return SvgItemType.CLOSED_PATH
            
        else:
            return SvgItemType.ICON
        
    def get_default_entity_svg_path_str( self,
                                         entity         : Entity,
                                         location_view  : LocationView,
                                         is_path_closed : bool           ) -> str:
        return PathGeometry.create_default_path_string(
            location_view=location_view,
            is_path_closed=is_path_closed,
            entity_type=entity.entity_type,
        )
    
    def get_default_collection_svg_path_str( self,
                                             collection      : Collection,
                                             location_view   : LocationView,
                                             is_path_closed  : bool           ) -> str:
        # Use unified PathGeometry approach for collections
        return PathGeometry.create_default_path_string(
            location_view=location_view,
            is_path_closed=is_path_closed,
            collection_type=collection.collection_type,
        )

    
