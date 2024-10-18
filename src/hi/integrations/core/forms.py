from django import forms

from hi.apps.attribute.forms import AttributeForm

from .models import Integration, IntegrationAttribute


class IntegrationAttributeForm( AttributeForm ):
    class Meta( AttributeForm.Meta ):
        model = IntegrationAttribute
        

IntegrationAttributeFormSet = forms.inlineformset_factory(
    Integration,
    IntegrationAttribute,
    form = IntegrationAttributeForm,
    extra = 0,
    max_num = 100,
    absolute_max = 100,
    can_delete = False,
)
