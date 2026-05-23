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


class EntityAddForm( EntityForm ):

    MAX_BULK_ADD_QUANTITY = 100

    quantity = forms.IntegerField(
        label = 'Quantity',
        required = True,
        min_value = 1,
        max_value = MAX_BULK_ADD_QUANTITY,
        initial = 1,
        widget = forms.NumberInput( attrs = {
            'min': 1,
            'max': MAX_BULK_ADD_QUANTITY,
            'step': 1,
        }),
    )


class EntityAttributeForm( AttributeForm ):
    class Meta( AttributeForm.Meta ):
        model = EntityAttribute


class EntityAttributeRegularFormSet(RegularAttributeBaseFormSet):
    pass


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
