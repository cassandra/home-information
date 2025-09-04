from django import forms

from hi.apps.attribute.forms import AttributeForm, AttributeUploadForm

from .models import Subsystem, SubsystemAttribute


class SubsystemAttributeForm( AttributeForm ):
    class Meta( AttributeForm.Meta ):
        model = SubsystemAttribute

    
SubsystemAttributeFormSet = forms.inlineformset_factory(
    Subsystem,
    SubsystemAttribute,
    form = SubsystemAttributeForm,
    extra = 0,
    max_num = 100,
    absolute_max = 100,
    can_delete = False,
)
