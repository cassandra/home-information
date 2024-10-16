from django import forms

from hi.apps.collection.enums import CollectionType
from hi.apps.collection.models import Collection, CollectionPosition
from hi.apps.location.edit.forms import LocationItemPositionForm


class CollectionForm( forms.ModelForm ):

    class Meta:
        model = Collection
        fields = (
            'name',
            'collection_type_str',
        )
        
    collection_type_str = forms.ChoiceField(
        label = 'Collection Type',
        choices = CollectionType.choices,
        initial = CollectionType.default_value(),
        required = True,
        widget = forms.Select( attrs = { 'class' : 'custom-select' } ),
    )

        
class CollectionPositionForm( LocationItemPositionForm ):
    class Meta( LocationItemPositionForm.Meta ):
        model = CollectionPosition
