from django import forms

from .constants import UserConstants


class SigninMagicCodeForm(forms.Form):
    """ Validates the access code page's submit; the page renders its own inputs. """

    email_address = forms.CharField(
        max_length = 128,
    )

    # Room for a code pasted or typed with separators, which redeeming ignores.
    magic_code = forms.CharField(
        max_length = 2 * UserConstants.MAGIC_CODE_KEYPAD.length,
    )
