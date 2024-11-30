from django import forms

from hi.apps.collection.enums import CollectionType, CollectionViewType
from hi.apps.collection.models import Collection, CollectionPosition
from hi.apps.location.edit.forms import LocationItemPositionForm


class CollectionForm( forms.ModelForm ):

    class Meta:
        model = Collection
        fields = (
            'name',
            'collection_type_str',
            'collection_view_type_str',
            'order_id',
        )
        
    collection_type_str = forms.ChoiceField(
        label = 'Collection Type',
        choices = CollectionType.choices,
        initial = CollectionType.default_value(),
        required = True,
        widget = forms.Select( attrs = { 'class' : 'custom-select' } ),
    )
        
    collection_view_type_str = forms.ChoiceField(
        label = 'View Type',
        choices = CollectionViewType.choices,
        initial = CollectionViewType.default_value(),
        required = True,
        widget = forms.Select( attrs = { 'class' : 'custom-select' } ),
    )

        
class CollectionPositionForm( LocationItemPositionForm ):
    class Meta( LocationItemPositionForm.Meta ):
        model = CollectionPosition
