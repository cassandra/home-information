import logging
import os

from django import forms
from django.conf import settings

from hi.apps.attribute.forms import AttributeForm
from hi.apps.common.svg_forms import SvgDecimalFormField, SvgFileForm

from hi.apps.location.enums import LocationViewType
from hi.apps.location.models import (
    Location,
    LocationAttribute,
    LocationView,
)

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

    def allow_default_svg_file(self):
        return True

    
class LocationSvgReplaceForm( LocationSvgFileForm ):

    def allow_default_svg_file(self):
        return False

    
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
        
    svg_rotate = SvgDecimalFormField()

    location_view_type_str = forms.ChoiceField(
        label = 'View Type',
        choices = LocationViewType.choices,
        initial = LocationViewType.default_value(),
        required = True,
        widget = forms.Select( attrs = { 'class' : 'custom-select' } ),
    )
    
    
class LocationViewGeometryForm( forms.ModelForm ):
    class Meta:
        model = LocationView
        fields = (
            'svg_view_box_str',
            'svg_rotate',
        )

    svg_rotate = SvgDecimalFormField()

   
class LocationItemPositionForm( forms.ModelForm ):
    # Abstract class.  Subclasses need to add model. e.g.,
    #
    #    class MySubclassForm(LocationItemPositionForm):
    #      class Meta(LocationItemPositionForm.Meta):
    #          model = MySubclassModel

    class Meta:
        fields = (
            'svg_x',
            'svg_y',
            'svg_scale',
            'svg_rotate',
        )

    svg_x = SvgDecimalFormField()
    svg_y = SvgDecimalFormField()
    svg_scale = SvgDecimalFormField()
    svg_rotate = SvgDecimalFormField()
