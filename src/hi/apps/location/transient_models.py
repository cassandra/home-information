from dataclasses import dataclass
from typing import Dict, Generator, List, Set

from hi.apps.collection.models import Collection, CollectionPath, CollectionPosition
from hi.apps.common.svg_models import SvgIconItem, SvgPathItem
from hi.apps.entity.models import Entity, EntityPosition, EntityPath
from hi.apps.location.edit.forms import (
    LocationAttributeFormSet,
    LocationAttributeUploadForm,
    LocationEditForm,
    LocationViewEditForm,
)
from hi.apps.location.svg_item_factory import SvgItemFactory
from hi.apps.sense.transient_models import SensorResponse

from .models import Location, LocationView


@dataclass
class StatusDisplayData:
    entity           : Entity
    sensor_response  : SensorResponse

    
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
    
    @property
    def svg_icon_items(self) -> Generator[ SvgIconItem, None, None ]:
        svg_item_factory = SvgItemFactory()
        for entity_position in self.entity_positions:
            svg_icon_item = svg_item_factory.create_svg_icon_item(
                item = entity_position.entity,
                position = entity_position,
            )
            yield svg_icon_item
            continue
        for collection_position in self.collection_positions:
            svg_icon_item = svg_item_factory.create_svg_icon_item(
                item = collection_position.collection,
                position = collection_position,
            )
            yield svg_icon_item
            continue
        return

    @property
    def svg_path_items(self) -> Generator[ SvgPathItem, None, None ]:
        svg_item_factory = SvgItemFactory()
        for entity_path in self.entity_paths:
            svg_path_item = svg_item_factory.create_svg_path_item(
                item = entity_path.entity,
                path = entity_path,
            )
            yield svg_path_item
            continue
        for collection_path in self.collection_paths:
            svg_path_item = svg_item_factory.create_svg_path_item(
                item = collection_path.collection,
                path = collection_path,
            )
            yield svg_path_item
            continue
        return

    
@dataclass
class LocationEditData:
    """ All the data needed to render the Location edit pane. """
    location                        : Location
    location_edit_form              : LocationEditForm             = None
    location_attribute_formset      : LocationAttributeFormSet     = None
    location_attribute_upload_form  : LocationAttributeUploadForm  = None

    def __post_init__(self):

        if not self.location_edit_form:
            self.location_edit_form = LocationEditForm(
                instance = self.location,
            )
        if not self.location_attribute_formset:
            self.location_attribute_formset = LocationAttributeFormSet(
                instance = self.location,
                prefix = f'location-{self.location.id}',
                form_kwargs = {
                    'show_as_editable': True,
                },
            )
        if not self.location_attribute_upload_form:
            self.location_attribute_upload_form = LocationAttributeUploadForm()
            
        return
    
    def to_template_context(self):
        return {
            'location': self.location,
            'location_edit_form': self.location_edit_form,
            'location_attribute_formset': self.location_attribute_formset,
            'location_attribute_upload_form': self.location_attribute_upload_form,
        }

    
@dataclass
class LocationViewEditData:
    """ All the data needed to render the LocationView edit pane. """

    location_view            : LocationView
    location_view_edit_form  : LocationViewEditForm  = None
    
    def __post_init__(self):

        if not self.location_view_edit_form:
            self.location_view_edit_form = LocationViewEditForm( instance = self.location_view )

        return
        
    def to_template_context(self):
        return {
            'location_view': self.location_view,
            'location_view_edit_form': self.location_view_edit_form,
        }
