from dataclasses import dataclass
from typing import Dict, Generator, List, Set

from hi.apps.collection.models import Collection, CollectionPath, CollectionPosition
from hi.apps.common.svg_models import SvgIconItem, SvgPathItem
from hi.apps.entity.models import Entity, EntityPosition, EntityPath
from hi.apps.location.svg_item_factory import SvgItemFactory

from .models import LocationView
from .transient_models import StatusDisplayData


@dataclass
class LocationViewData:
    """
    Encapsulates all the data needed to render overlaying a Location's SVG
    for a given LocationView.
    """
    location_view             : LocationView
    entity_positions          : List[ EntityPosition ]
    entity_paths              : List[ EntityPath ]
    collection_positions      : List[ CollectionPosition ]
    collection_paths          : List[ CollectionPath ]
    unpositioned_collections  : List[ Collection ]
    orphan_entities           : Set[ Entity ]
    status_display_data_map   : Dict[ Entity, StatusDisplayData ]

    def __post_init__(self):
        self._svg_item_factory = SvgItemFactory()
        return
    
    def svg_icon_items(self) -> Generator[ SvgIconItem, None, None ]:

        for entity_position in self.entity_positions:            
            status_display_data = self.status_display_data_map.get( entity_position.entity )
            svg_icon_item = self._svg_item_factory.create_svg_icon_item(
                item = entity_position.entity,
                position = entity_position,
                status_display_data = status_display_data,
            )
            yield svg_icon_item
            continue
        for collection_position in self.collection_positions:
            svg_icon_item = self._svg_item_factory.create_svg_icon_item(
                item = collection_position.collection,
                position = collection_position,
            )
            yield svg_icon_item
            continue
        return

    def svg_path_items(self) -> Generator[ SvgPathItem, None, None ]:

        for entity_path in self.entity_paths:
            status_display_data = self.status_display_data_map.get( entity_path.entity )
            svg_path_item = self._svg_item_factory.create_svg_path_item(
                item = entity_path.entity,
                path = entity_path,
                status_display_data = status_display_data,
            )
            yield svg_path_item
            continue
        for collection_path in self.collection_paths:
            svg_path_item = self._svg_item_factory.create_svg_path_item(
                item = collection_path.collection,
                path = collection_path,
            )
            yield svg_path_item
            continue
        return

    
