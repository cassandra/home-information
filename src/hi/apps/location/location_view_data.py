from dataclasses import dataclass
from typing import Dict, Generator, List, Set

from hi.apps.collection.models import Collection, CollectionPath, CollectionPosition
from hi.apps.common.svg_models import SvgIconItem, SvgPathItem
from hi.apps.entity.models import Entity, EntityPosition, EntityPath
from hi.apps.location.svg_item_factory import SvgItemFactory
from hi.apps.monitor.status_display_data import StatusDisplayData
from hi.apps.monitor.transient_models import EntityStateStatusData

from .models import LocationView


@dataclass
class LocationViewData:
    """
    Encapsulates all the data needed to render overlaying a Location's SVG
    for a given LocationView.
    """
    location_view                            : LocationView
    entity_positions                         : List[ EntityPosition ]
    entity_paths                             : List[ EntityPath ]
    collection_positions                     : List[ CollectionPosition ]
    collection_paths                         : List[ CollectionPath ]
    unpositioned_collections                 : List[ Collection ]
    orphan_entities                          : Set[ Entity ]
    entity_to_entity_state_status_data_list  : Dict[ Entity, List[ EntityStateStatusData ]]
    
    def __post_init__(self):
        self._svg_item_factory = SvgItemFactory()
        self._css_class_map = self._get_css_class_map()
        self._latest_entity_state_status_data_map = self._get_latest_entity_state_status_data_map()
        return
    
    def svg_icon_items(self) -> Generator[ SvgIconItem, None, None ]:

        for entity_position in self.entity_positions:

            css_class = self._css_class_map.get( entity_position.entity, '' )
            latest_entity_state_status_data = self._latest_entity_state_status_data_map.get(
                entity_position.entity,
            )
            if latest_entity_state_status_data:
                status_display_data = StatusDisplayData(
                    entity_state_status_data = latest_entity_state_status_data,
                )
                svg_status_style = status_display_data.svg_status_style
            else:
                svg_status_style = None
            
            svg_icon_item = self._svg_item_factory.create_svg_icon_item(
                item = entity_position.entity,
                position = entity_position,
                css_class = css_class,
                svg_status_style = svg_status_style,
            )
            yield svg_icon_item
            continue
        
        for collection_position in self.collection_positions:
            svg_icon_item = self._svg_item_factory.create_svg_icon_item(
                item = collection_position.collection,
                position = collection_position,
                css_class = '',
            )
            yield svg_icon_item
            continue
        return

    def svg_path_items(self) -> Generator[ SvgPathItem, None, None ]:

        for entity_path in self.entity_paths:

            css_class = self._css_class_map.get( entity_path.entity, '' )
            latest_entity_state_status_data = self._latest_entity_state_status_data_map.get(
                entity_path.entity,
            )
            if latest_entity_state_status_data:
                status_display_data = StatusDisplayData(
                    entity_state_status_data = latest_entity_state_status_data,
                )
                svg_status_style = status_display_data.svg_status_style
            else:
                svg_status_style = None
                
            svg_path_item = self._svg_item_factory.create_svg_path_item(
                item = entity_path.entity,
                path = entity_path,
                css_class = css_class,
                svg_status_style = svg_status_style,
            )
            yield svg_path_item
            continue
        
        for collection_path in self.collection_paths:
            svg_path_item = self._svg_item_factory.create_svg_path_item(
                item = collection_path.collection,
                path = collection_path,
                css_class = '',
            )
            yield svg_path_item
            continue
        return

    def _get_css_class_map(self):
        css_class_map = dict()
        for entity, entity_state_status_data_list in self.entity_to_entity_state_status_data_list.items():
            if not entity_state_status_data_list:
                continue
            entity_states = [ x.entity_state for x in entity_state_status_data_list ]
            css_class_map[entity] = ' '.join([ x.css_class for x in entity_states ])
            continue
        return css_class_map

    def _get_latest_entity_state_status_data_map(self):
        latest_entity_state_status_data_map = dict()
        for entity, entity_state_status_data_list in self.entity_to_entity_state_status_data_list.items():
            if not entity_state_status_data_list:
                continue
            with_responses_list = [ x for x in entity_state_status_data_list if x.latest_sensor_response ]
            if not with_responses_list:
                continue
            with_responses_list.sort( key = lambda item : item.latest_sensor_response.timestamp,
                                      reverse = True )
            latest_entity_state_status_data_map[entity] = with_responses_list[0]
            continue
        return latest_entity_state_status_data_map
