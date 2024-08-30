from hi.apps.location.location_view_data import LocationViewData

from . import api_models


class ApiTranslator:

    @classmethod
    def toSvgOverlayData( cls, location_view_data : LocationViewData ) -> api_models.SvgOverlayData:

        icon_items = list()
        path_items = list()
        
        for entity_position in location_view_data.entity_positions:
            icon_item = api_models.SvgIconItem(
                html_id = entity_position.entity.html_id,
                icon_filename = entity_position.entity.entity_type.svg_icon_template_name,
                svg_x = float( entity_position.svg_x ),
                svg_y = float( entity_position.svg_y ),
                scale = float( entity_position.svg_scale ),
                rotation = float( entity_position.svg_rotation ),
            )
            icon_items.append( icon_item )
            continue

        for entity_path in location_view_data.entity_paths:
            path_item = api_models.SvgPathItem(
                html_id = entity_path.entity.html_id,
                svg_path = entity_path.svg_path,
                svg_path_style = entity_path.entity.entity_type.svg_path_style,
            )
            icon_items.append( path_item )
            continue

        for collection_position in location_view_data.collection_positions:
            icon_item = api_models.SvgIconItem(
                html_id = collection_position.collection.html_id,
                icon_filename = collection_position.collection.collection_type.svg_icon_template_name,
                svg_x = float( collection_position.svg_x ),
                svg_y = float( collection_position.svg_y ),
                scale = float( collection_position.svg_scale ),
                rotation = float( collection_position.svg_rotation ),
            )
            continue
        
        return api_models.SvgOverlayData(
            base_html_id = location_view_data.location_view.html_id,
            icon_items = icon_items,
            path_items = path_items,
        )
    
