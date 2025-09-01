from dataclasses import dataclass

from hi.apps.location.edit.forms import (
    LocationEditForm,
    LocationViewEditForm,
)

from .models import Location, LocationView


@dataclass
class LocationEditModeData:
    """ All the data needed to render the Location edit pane. """
    location                        : Location
    location_edit_form              : LocationEditForm             = None

    def __post_init__(self):

        if not self.location_edit_form:
            self.location_edit_form = LocationEditForm(
                instance = self.location,
            )
        return
    
    def to_template_context(self):
        return {
            'location': self.location,
            'location_edit_form': self.location_edit_form,
        }

    
@dataclass
class LocationViewEditModeData:
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
