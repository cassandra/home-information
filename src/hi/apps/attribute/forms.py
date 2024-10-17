from django.core.exceptions import ValidationError
from django import forms

from hi.apps.common.utils import is_blank

from .enums import AttributeType, AttributeValueType


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
        
        if not self.instance.is_editable:
            raise ValidationError( 'This attribute is not editable.' )
        
        value_type = AttributeValueType.from_name( cleaned_data.get('value_type_str') )
        name = cleaned_data.get('name')
        value = cleaned_data.get('value')
        file_value = cleaned_data.get('file_value')

        if is_blank( name ):
            self.add_error( 'name', 'A name is required' )
            
        if value_type == AttributeValueType.FILE:
            if not file_value:
                self.add_error( 'file_value', 'A file is required.')

        elif value_type in { AttributeValueType.TEXT, AttributeValueType.SECRET }:
            if self.instance.is_required and is_blank( value ):
                self.add_error( 'value', 'A value is required' )

        return cleaned_data

    def save( self, commit = True ):
        instance = super().save( commit = False )
        
        if not instance.pk:
            instance.attribute_type_str = AttributeType.CUSTOM
            instance.is_editable = True
            instance.iis_required = False
        
        if commit:
            instance.save()
        return instance

    
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
