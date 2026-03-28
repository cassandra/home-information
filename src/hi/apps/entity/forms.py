from django import forms

from hi.apps.attribute.forms import AttributeForm, AttributeUploadForm, RegularAttributeBaseFormSet
from hi.apps.entity.enums import EntityType
from hi.apps.entity.models import Entity, EntityAttribute


class EntityForm( forms.ModelForm ):

    class Meta:
        model = Entity
        fields = (
            'name',
            'entity_type_str',
        )
        
    entity_type_str = forms.ChoiceField(
        label = 'Type',
        choices = EntityType.choices,
        initial = EntityType.default_value(),
        required = True,
        widget = forms.Select( attrs = { 'class' : 'custom-select' } ),
    )

    
class EntityAttributeForm( AttributeForm ):
    class Meta( AttributeForm.Meta ):
        model = EntityAttribute


class EntityAttributeRegularFormSet(RegularAttributeBaseFormSet):

    def clean(self):
        super().clean()

        if not self.instance or self.instance.can_add_custom_attributes:
            return

        for form in self.forms:
            if not hasattr(form, 'cleaned_data'):
                continue

            cleaned_data = form.cleaned_data
            if not cleaned_data:
                continue

            if cleaned_data.get('DELETE', False):
                continue

            if form.instance and form.instance.pk:
                continue

            has_new_data = bool(
                cleaned_data.get('name')
                or cleaned_data.get('value')
                or cleaned_data.get('secret')
            )
            if has_new_data:
                raise forms.ValidationError(
                    'New attributes cannot be added for this entity because attributes are managed externally.'
                )


EntityAttributeRegularFormSet = forms.inlineformset_factory(
    Entity,
    EntityAttribute,
    form = EntityAttributeForm,
    formset = EntityAttributeRegularFormSet,
    extra = 1,
    max_num = 100,
    absolute_max = 100,
    can_delete = True,
)


class EntityAttributeUploadForm( AttributeUploadForm ):
    class Meta( AttributeUploadForm.Meta ):
        model = EntityAttribute
