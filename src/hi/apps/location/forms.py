from django import forms

from hi.apps.attribute.forms import AttributeForm, AttributeUploadForm
from hi.apps.attribute.enums import AttributeValueType

from hi.apps.location.models import Location, LocationAttribute


class LocationAttributeForm( AttributeForm ):
    class Meta( AttributeForm.Meta ):
        model = LocationAttribute
        
        
class RegularAttributeBaseFormSet(forms.BaseInlineFormSet):
    """Base formset that automatically excludes FILE attributes for regular attribute editing"""
    
    def get_queryset(self):
        """Override to automatically filter out FILE attributes"""
        queryset = super().get_queryset()
        return queryset.exclude(value_type_str=str(AttributeValueType.FILE))


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


