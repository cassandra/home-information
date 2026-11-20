from django import forms

from .constants import UserConstants


class SigninMagicCodeForm(forms.Form):

    email_address = forms.CharField(
        max_length = 128,
        widget = forms.HiddenInput(),
    )

    magic_code = forms.CharField(
        label = '',
        max_length = 2 * UserConstants.MAGIC_CODE_KEYPAD.length,
        widget = forms.TextInput( attrs = { 'autofocus': 'autofocus',
                                            'placeholder': 'access code',
                                            'width': str(2 * UserConstants.MAGIC_CODE_KEYPAD.length) } ),
        required = True )
