import mimetypes

from django.core.exceptions import ValidationError
from django import forms

from hi.apps.common.utils import is_blank

from .enums import AttributeType, AttributeValueType


class AttributeForm( forms.ModelForm ):
    """
    Abstract mode form class the corresponds to the abstract model calss
    Attribute.  When subclassing the Attribute model, you likely also want
    a subclass of this model form.  Subclassing this fomr looks something
    like this:
    
        class MyAttributeForm( AttributeForm ):
            class Meta( AttributeForm.Meta ):
                model = MyAttribute
    """
    class Meta:
        fields = (
            'name',
            'value',
        )

    secret = forms.BooleanField(
        required = False,
        label = 'Mark as Secret',
    )

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
        name = cleaned_data.get('name')
        value = cleaned_data.get('value')

        form_is_bound = bool( self.instance.pk )
        if form_is_bound:
            if not self.instance.is_editable:
                raise ValidationError( f'The attribute "{self.instance.name}" is not editable.' )
            if ( self.instance.attribute_type == AttributeType.PREDEFINED
                 and ( name != self.instance.name )):
                raise ValidationError( 'Changing name forbidden for predefined attributes.' ) 
            value = cleaned_data.get('value')
            if self.instance.is_required and is_blank( value ):
                self.add_error( 'value', 'A value is required.')

        if self.cleaned_data.get('secret'):
            stripped_value = value.strip()
            value_lines = stripped_value.splitlines()
            if len( value_lines) > 1:
                self.add_error( 'value', 'Secret attributes are limited ot a single line.')
            
        return cleaned_data

    def save( self, commit = True ):
        instance = super().save( commit = False )
        
        if not instance.pk:
            instance.attribute_type_str = str(AttributeType.CUSTOM)
            instance.is_editable = True
            instance.is_required = False

            if self.cleaned_data.get('secret'):
                instance.value_type_str = str( AttributeValueType.SECRET )
            else:
                instance.value_type_str = str(AttributeValueType.TEXT)

        if commit:
            instance.save()
        return instance

    
class AttributeUploadForm( forms.ModelForm ):

    class Meta:
        fields = (
            'file_value',
        )
        
    def clean(self):
        cleaned_data = super().clean()

        file_value = cleaned_data.get('file_value')
        if not file_value:
            self.add_error( 'file_value', 'A file is required.')

        return cleaned_data

    def save( self, commit = True ):
        instance = super().save( commit = False )

        mime_type_tuple = mimetypes.guess_type( instance.file_value.name )
        
        instance.name = instance.file_value.name
        instance.file_mime_type = mime_type_tuple[0]
        instance.value_type_str = str( AttributeValueType.FILE )
        instance.attribute_type_str = str(AttributeType.CUSTOM)
        instance.is_editable = True
        instance.is_required = False

        if commit:
            instance.save()
        return instance
