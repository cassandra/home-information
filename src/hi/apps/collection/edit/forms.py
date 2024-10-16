from django import forms

from hi.apps.collection.enums import CollectionType
from hi.apps.collection.models import CollectionPosition
from hi.apps.location.edit.forms import LocationItemPositionForm


class CollectionForm(forms.Form):

    name = forms.CharField(
        label = 'Name',
        max_length = 64,
        required = False,
    )
    
    collection_type = forms.ChoiceField(
        label = 'Collection Type',
        choices = CollectionType.choices,
        initial = CollectionType.default_value(),
        required = True,
        widget = forms.Select( attrs = { 'class' : 'custom-select' } ),
    )
    
    def clean(self):
        cleaned_data = super().clean()

        name = cleaned_data.get( 'name', '' )
        if not name:
            collection_type_str = cleaned_data.get( 'collection_type' )
            collection_type = CollectionType.from_name_safe( collection_type_str )
            cleaned_data['name'] = collection_type.label

        return cleaned_data

    
class CollectionPositionForm( LocationItemPositionForm ):
    class Meta( LocationItemPositionForm.Meta ):
        model = CollectionPosition
