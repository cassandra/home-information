from django import forms

from hi.apps.collection.enums import CollectionType, CollectionViewType
from hi.apps.collection.models import Collection, CollectionPosition
from hi.apps.location.edit.forms import LocationItemPositionForm


class CollectionBaseForm( forms.ModelForm ):

    class Meta:
        model = Collection
        fields = (
            'name',
            'collection_type_str',
            'collection_view_type_str',
        )
        
    collection_type_str = forms.ChoiceField(
        label = 'Category',
        choices = CollectionType.choices,
        initial = CollectionType.default_value(),
        required = True,
        widget = forms.Select( attrs = { 'class' : 'custom-select' } ),
    )
        
    collection_view_type_str = forms.ChoiceField(
        label = 'Display',
        choices = CollectionViewType.choices,
        initial = CollectionViewType.default_value(),
        required = True,
        widget = forms.Select( attrs = { 'class' : 'custom-select' } ),
    )


class CollectionEditForm( CollectionBaseForm ):

    class Meta(CollectionBaseForm.Meta):
        fields = CollectionBaseForm.Meta.fields + ('order_id',)

        widgets = {
            'order_id': forms.NumberInput( attrs={'class': 'form-control'} ),
        }
        
    
class CollectionAddForm( CollectionBaseForm ):

    include_in_location_view = forms.BooleanField(
        label = 'Include in Current Location View?',
        required = False,
        initial = False,
    )

    def __init__(self, *args, **kwargs):
        include_in_location_view = kwargs.pop( 'include_in_location_view', False )
        super().__init__(*args, **kwargs)
        self.fields['include_in_location_view'].initial = include_in_location_view
        return

    
class CollectionPositionForm( LocationItemPositionForm ):
    class Meta( LocationItemPositionForm.Meta ):
        model = CollectionPosition
