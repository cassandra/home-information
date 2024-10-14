import logging
import os

from django import forms
from django.conf import settings

from hi.apps.attribute.forms import AttributeForm
from hi.apps.common.svg_file_form import SvgFileForm

from hi.apps.location.models import Location, LocationAttribute, LocationView

logger = logging.getLogger(__name__)


class LocationSvgFileForm( SvgFileForm ):

    def get_default_source_directory(self):
        return os.path.join(
            settings.BASE_DIR,
            'static',
            'img',
        )

    def get_default_basename(self):
        return 'location-default.svg'
    
    def get_media_destination_directory(self):
        return 'location/svg'

    
class LocationAddForm( LocationSvgFileForm ):

    # N.B. When adding a Location, we use limited field options to
    # keep it simpler.
        
    name = forms.CharField(
        label = 'Location Name',
        required = True,
    )

    def get_default_source_directory(self):
        return os.path.join(
            settings.BASE_DIR,
            'static',
            'img',
        )

    def get_default_basename(self):
        return 'location-default.svg'
    
    def get_media_destination_directory(self):
        return 'location/svg'

    
class LocationEditForm( forms.ModelForm ):

    # N.B. The svg file fields are managed separately with SvgFileForm due
    # to special handling needed.
    
    class Meta:
        model = Location
        fields = (
            'name',
            'order_id',
        )
    

class LocationAttributeForm( AttributeForm ):

    class Meta:
        model = LocationAttribute
        fields = (
            'name',
            'value',
            'value_type_str',
        )

        
LocationAttributeFormset = forms.inlineformset_factory(
    Location,
    LocationAttribute,
    form = LocationAttributeForm,
    extra = 1,
    max_num = 100,
    absolute_max = 100,
    can_delete = True,
)


class LocationViewAddForm(forms.Form):

    # N.B. When adding a LocationView, we use limited field options to keep
    # it simpler.
    
    name = forms.CharField()

    
class LocationViewEditForm( forms.ModelForm ):

    class Meta:
        model = LocationView
        fields = (
            'name',
            'order_id',
            'svg_view_box_str',
            'svg_rotate',
            'location_view_type_str',
        )
    
