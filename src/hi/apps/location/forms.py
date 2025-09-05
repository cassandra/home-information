from django import forms

from hi.apps.attribute.forms import AttributeForm, AttributeUploadForm, RegularAttributeBaseFormSet

from hi.apps.location.models import Location, LocationAttribute


class LocationAttributeForm( AttributeForm ):
    class Meta( AttributeForm.Meta ):
        model = LocationAttribute
        
        
LocationAttributeRegularFormSet = forms.inlineformset_factory(
    Location,
    LocationAttribute,
    form = LocationAttributeForm,
    formset = RegularAttributeBaseFormSet,
    extra = 1,
    max_num = 100,
    absolute_max = 100,
    can_delete = True,
)


class LocationForm( forms.ModelForm ):
    """
    Location edit form for modal - only includes name field.
    Geometry fields (svg_view_box_str, order_id) are edited separately.
    """
    
    class Meta:
        model = Location
        fields = ('name',)
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'})
        }

        
class LocationAttributeUploadForm( AttributeUploadForm ):
    class Meta( AttributeUploadForm.Meta ):
        model = LocationAttribute


