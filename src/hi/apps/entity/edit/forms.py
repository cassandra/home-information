from django import forms

from hi.apps.entity.enums import EntityType
from hi.apps.entity.models import EntityPosition
from hi.apps.location.edit.forms import LocationItemPositionForm


class EntityForm(forms.Form):

    name = forms.CharField(
        label = 'Name',
        max_length = 64,
        required = False,
    )
    
    entity_type = forms.ChoiceField(
        label = 'Entity Type',
        choices = EntityType.choices,
        initial = EntityType.default_value(),
        required = True,
        widget = forms.Select( attrs = { 'class' : 'custom-select' } ),
    )
    
    def clean(self):
        cleaned_data = super().clean()

        name = cleaned_data.get( 'name', '' )
        if not name:
            entity_type_str = cleaned_data.get( 'entity_type' )
            entity_type = EntityType.from_name_safe( entity_type_str )
            cleaned_data['name'] = entity_type.label

        return cleaned_data

    
class EntityPositionForm( LocationItemPositionForm ):
    class Meta( LocationItemPositionForm.Meta ):
        model = EntityPosition
