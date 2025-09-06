from django import forms

from hi.apps.attribute.forms import AttributeForm, RegularAttributeBaseFormSet

from .models import Integration, IntegrationAttribute


class IntegrationAttributeForm( AttributeForm ):
    class Meta( AttributeForm.Meta ):
        model = IntegrationAttribute

    
IntegrationAttributeRegularFormSet = forms.inlineformset_factory(
    Integration,
    IntegrationAttribute,
    form = IntegrationAttributeForm,
    formset = RegularAttributeBaseFormSet,
    extra = 0,
    max_num = 100,
    absolute_max = 100,
    can_delete = False,
)
