from dataclasses import dataclass

from hi.apps.location.forms import (
    LocationAttributeFormSet,
    LocationAttributeUploadForm,
)
from hi.apps.location.edit.forms import (
    LocationEditForm,
    LocationViewEditForm,
)

from .models import Location, LocationView


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
            'history_url_name': 'location_attribute_history_inline',
            'restore_url_name': 'location_attribute_restore_inline',
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
