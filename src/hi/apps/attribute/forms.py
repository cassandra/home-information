import json

from django.core.validators import validate_email, URLValidator
from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django import forms
from django.utils.dateparse import parse_date, parse_datetime, parse_time

from .enums import AttributeValueType


class AttributeForm(forms.ModelForm):

    class Meta:
        abstract = True
        fields = (
            'name',
            'value',
        )
        widgets = {
            'name': forms.TextInput(
                attrs = {
                    'class': 'form-control',
                }
            ),
            'value': forms.TextInput(
                attrs = {
                    'class': 'form-control',
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        self._is_editable = kwargs.pop( 'is_editable', True )
        super().__init__(*args, **kwargs)

        # Access the instance's value_type field
        instance = kwargs.get('instance')

        # Always set the name field as a TextInput widget
        self.fields['name'].widget = forms.TextInput(attrs={'class': 'form-control'})

        # Customize the value field based on the value_type in the instance
        if instance and instance.value_type:
            value_type = instance.value_type

            if value_type == AttributeValueType.INTEGER:
                self.fields['value'].widget = forms.NumberInput(
                    attrs={'class': 'form-control'},
                )
            elif value_type == AttributeValueType.FLOAT:
                self.fields['value'].widget = forms.NumberInput(
                    attrs={'step': 'any', 'class': 'form-control'},
                )
            elif value_type == AttributeValueType.BOOLEAN:
                self.fields['value'].widget = forms.CheckboxInput()
            elif value_type == AttributeValueType.DATE:
                self.fields['value'].widget = forms.DateInput(
                    attrs={'type': 'date', 'class': 'form-control'},
                )
            elif value_type == AttributeValueType.DATETIME:
                self.fields['value'].widget = forms.DateTimeInput(
                    attrs={'type': 'datetime-local', 'class': 'form-control'},
                )
            elif value_type == AttributeValueType.TIME:
                self.fields['value'].widget = forms.TimeInput(
                    attrs={'type': 'time', 'class': 'form-control'},
                )
            elif value_type == AttributeValueType.TEXT:
                self.fields['value'].widget = forms.Textarea(
                    attrs={'class': 'form-control'},
                )
            elif value_type == AttributeValueType.EMAIL:
                self.fields['value'].widget = forms.EmailInput(
                    attrs={'class': 'form-control'},
                )
            elif value_type == AttributeValueType.LINK:
                self.fields['value'].widget = forms.URLInput(
                    attrs={'class': 'form-control'},
                )
            elif value_type == AttributeValueType.PASSWORD:
                self.fields['value'].widget = forms.PasswordInput(
                    attrs={'class': 'form-control'},
                )
            elif value_type in { AttributeValueType.IMAGE,
                                 AttributeValueType.PDF,
                                 AttributeValueType.VIDEO, AttributeValueType.AUDIO }:
                # File input for media types
                self.fields['value'].widget = forms.FileInput(
                    attrs={'class': 'form-control'},
                )
            else:
                # Fallback to a simple TextInput
                self.fields['value'].widget = forms.TextInput(
                    attrs={'class': 'form-control'},
                )
        else:
            # If no instance or no value_type, use default TextInput widget
            self.fields['value'].widget = forms.TextInput(
                attrs={'class': 'form-control'},
            )
            
    def clean(self):
        cleaned_data = super().clean()
        value = cleaned_data.get('value')
        value_type = self.instance.value_type

        # Validate based on value_type
        if value_type == AttributeValueType.INTEGER:
            try:
                int(value)
            except ValueError:
                self.add_error('value', 'Value must be an integer.')

        elif value_type == AttributeValueType.FLOAT:
            try:
                float(value)
            except ValueError:
                self.add_error('value', 'Value must be numeric.')

        elif value_type in { AttributeValueType.STRING,
                             AttributeValueType.TEXT }:
            if not isinstance(value, str):
                self.add_error('value', 'Value must be a string.')

        elif value_type == AttributeValueType.EMAIL:
            try:
                validate_email(value)
            except ValidationError:
                self.add_error('value', 'Not a valid email address.')

        elif value_type == AttributeValueType.LINK:
            validate_url = URLValidator()
            try:
                validate_url(value)
            except ValidationError:
                self.add_error('value', 'Not a valid URL.')

        elif value_type == AttributeValueType.PHONE:
            # Simple phone number validation (customize if needed)
            if not value.isdigit() or len(value) < 10:
                self.add_error('value', 'Not a valid phone number.')

        elif value_type == AttributeValueType.BOOLEAN:
            if value not in [True, False, 'True', 'False', 1, 0]:
                self.add_error('value', 'Value must be a boolean.')

        elif value_type == AttributeValueType.DATETIME:
            if not parse_datetime(value):
                self.add_error('value', 'Value must be a valid datetime.')

        elif value_type == AttributeValueType.DATE:
            if not parse_date(value):
                self.add_error('value', 'Value must be a valid date.')

        elif value_type == AttributeValueType.TIME:
            if not parse_time(value):
                self.add_error('value', 'Value must be a valid time.')

        elif value_type == AttributeValueType.JSON:
            try:
                json.loads(value)
            except ValueError:
                self.add_error('value', 'Value must be a valid JSON.')

        elif value_type in { AttributeValueType.PDF,
                             AttributeValueType.IMAGE,
                             AttributeValueType.VIDEO,
                             AttributeValueType.AUDIO }:
            if not default_storage.exists( value ):
                self.add_error('value', f'{value_type} file does not exist.')

        return cleaned_data

    @property
    def is_editable(self):
        return self._is_editable
    
