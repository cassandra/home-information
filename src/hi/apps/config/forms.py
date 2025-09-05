from django import forms

from hi.apps.attribute.forms import AttributeForm, RegularAttributeBaseFormSet

from .models import Subsystem, SubsystemAttribute


class SubsystemAttributeForm( AttributeForm ):
    class Meta( AttributeForm.Meta ):
        model = SubsystemAttribute

    
SubsystemAttributeRegularFormSet = forms.inlineformset_factory(
    Subsystem,
    SubsystemAttribute,
    form = SubsystemAttributeForm,
    formset = RegularAttributeBaseFormSet,
    extra = 0,
    max_num = 100,
    absolute_max = 100,
    can_delete = False,
)
