import hi.apps.common.datetimeproxy as datetimeproxy
from hi.apps.common.singleton import Singleton
from hi.apps.common.svg_models import SvgIconItem, SvgPathItem, SvgViewBox
from hi.apps.collection.models import Collection
from hi.apps.entity.enums import EntityStateType, EntityType
from hi.apps.entity.models import Entity
from hi.apps.sense.enums import SensorValue

from .enums import SvgItemType
from .models import (
    LocationItemModelMixin,
    LocationItemPositionModel,
    LocationItemPathModel,
    LocationView,
)
from .transient_models import StatusDisplayData


class SvgItemFactory( Singleton ):

    NEW_PATH_RADIUS_PERCENT = 5.0  # Preferrable if this matches Javascript new path sizing.

    def __init_singleton__(self):
        return

    def create_svg_icon_item( self,
                              item                 : LocationItemModelMixin,
                              position             : LocationItemPositionModel,
                              status_display_data  : StatusDisplayData          = None ) -> SvgIconItem:

        status_value = 'placeholder'
        
        return SvgIconItem(
            html_id = item.html_id,
            position_x = float( position.svg_x ),
            position_y = float( position.svg_y ),
            rotate = float( position.svg_rotate ),
            scale = float( position.svg_scale ),
            template_name = 'entity/svg/type.other.svg',
            bounding_box = SvgViewBox( x = 0, y = 0, width = 32, height = 32 ),
            status_value = status_value,
        )

    def create_svg_path_item( self,
                              item                 : LocationItemModelMixin,
                              path                 : LocationItemPathModel,
                              status_display_data  : StatusDisplayData      = None ) -> SvgPathItem:


        

        if status_display_data:

            print( f'\n\n{status_display_data.sensor.entity_state.entity_state_type}' )
            print( f'\n\n{status_display_data.sensor_response_list}' )
            print( f'   First = {status_display_data.sensor_response_list[0].value}' )
            if len(status_display_data.sensor_response_list) > 1:
                print( f'  Second = {status_display_data.sensor_response_list[1].value}' )
                
            if status_display_data.sensor.entity_state.entity_state_type == EntityStateType.MOVEMENT:
                if status_display_data.sensor_response_list[0].value == str(SensorValue.MOVEMENT_ACTIVE):
                    fill_color = 'red'
                    fill_opacity = 0.5
                elif (( len(status_display_data.sensor_response_list) > 1 )
                      and ( status_display_data.sensor_response_list[1].value == str(SensorValue.MOVEMENT_ACTIVE) )):
                    movement_timedelta = datetimeproxy.now() - status_display_data.sensor_response_list[1].timestamp
                    if movement_timedelta.seconds < 30:
                        fill_color = 'orange'
                        fill_opacity = 0.5
                    elif movement_timedelta.seconds < 60:
                        fill_color = 'yellow'
                        fill_opacity = 0.5
                    else:
                        fill_color = 'white'
                        fill_opacity = 0.5
                else:
                    fill_color = 'white'
                    fill_opacity = 0.0
            else:
                fill_color = 'blue'
                fill_opacity = 0.5
        else:
            fill_color = 'green'
            fill_opacity = 0.5


            

        
        
        return SvgPathItem(
            html_id = item.html_id,
            svg_path = path.svg_path,
            stroke_color = '#40f040',
            stroke_width = 5.0,
            fill_color = fill_color,
            fill_opacity = fill_opacity,
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
    
