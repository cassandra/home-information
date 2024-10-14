from dataclasses import dataclass

from hi.apps.common.svg_file_form import SvgFileForm
from hi.apps.location.edit.forms import (
    LocationAttributeFormset,
    LocationEditForm,
    LocationSvgFileForm,
    LocationViewEditForm,
)
from .models import Location, LocationView


@dataclass
class LocationDetailData:

    location                    : Location
    location_edit_form          : LocationEditForm
    location_attribute_formset  : LocationAttributeFormset
    location_svg_file_form      : LocationSvgFileForm
    
    location_view               : LocationView
    location_view_edit_form     : LocationViewEditForm
