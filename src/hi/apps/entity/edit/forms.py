from django import forms

from hi.apps.attribute.forms import GeneralAttributeForm
from hi.apps.entity.enums import EntityType
from hi.apps.entity.models import Entity, EntityAttribute, EntityPosition
from hi.apps.location.edit.forms import LocationItemPositionForm


class EntityForm( forms.ModelForm ):

    class Meta:
        model = Entity
        fields = (
            'name',
            'entity_type_str',
        )
        
    entity_type_str = forms.ChoiceField(
        label = 'Entity Type',
        choices = EntityType.choices,
        initial = EntityType.default_value(),
        required = True,
        widget = forms.Select( attrs = { 'class' : 'custom-select' } ),
    )

    
class EntityAttributeForm( GeneralAttributeForm ):
    class Meta( GeneralAttributeForm.Meta ):
        model = EntityAttribute

        
EntityAttributeFormSet = forms.inlineformset_factory(
    Entity,
    EntityAttribute,
    form = EntityAttributeForm,
    extra = 1,
    max_num = 100,
    absolute_max = 100,
    can_delete = True,
)


class EntityPositionForm( LocationItemPositionForm ):
    class Meta( LocationItemPositionForm.Meta ):
        model = EntityPosition
