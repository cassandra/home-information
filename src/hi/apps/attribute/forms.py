from django.core.files.storage import default_storage
from django import forms

from .enums import AttributeValueType


class AttributeForm(forms.ModelForm):

    class Meta:
        abstract = True

    @property
    def show_as_editable(self):
        return self._show_as_editable
        
    def __init__(self, *args, **kwargs):
        self._show_as_editable = kwargs.pop( 'show_as_editable', True )
        super().__init__(*args, **kwargs)

        # Access the instance's value_type field
        instance = kwargs.get('instance')

        for field in self.fields.values():
            if self._show_as_editable or ( instance and instance.is_editable ):
                continue
            field.widget.attrs['disabled'] = 'disabled'
            continue
            
        return
            
    def clean(self):
        cleaned_data = super().clean()
        value = cleaned_data.get('value')
        value_type = self.instance.value_type

        if value_type in { AttributeValueType.TEXT }:
            if not isinstance(value, str):
                self.add_error('value', 'Value must be a string.')

        elif value_type in { AttributeValueType.FILE }:
            if not default_storage.exists( value ):
                self.add_error('value', f'{value_type} file does not exist.')

        return cleaned_data

    
class GeneralAttributeForm( AttributeForm ):

    class Meta:
        fields = (
            'name',
            'value',
            'file_value',
            'value_type_str',
        )

    value_type_str = forms.ChoiceField(
        label = 'Value Type',
        choices = AttributeValueType.choices,
        initial = AttributeValueType.default_value(),
        required = True,
        widget = forms.Select( attrs = {
            'class' : 'custom-select',
            'onchange': 'Hi.changeAttributeValueType( this );',
        } ),
    )
