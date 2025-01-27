from django import forms

from .magic_code_generator import MagicCodeGenerator


class SigninMagicCodeForm(forms.Form):

    email_address = forms.CharField(
        max_length = 128,
        widget = forms.HiddenInput(),
    )

    magic_code = forms.CharField(
        label = '',
        max_length = 2 * MagicCodeGenerator.MAGIC_CODE_LENGTH,
        widget = forms.TextInput( attrs = { 'autofocus': 'autofocus',
                                            'placeholder': 'access code',
                                            'width': str(2 * MagicCodeGenerator.MAGIC_CODE_LENGTH) } ),
        required = True )
