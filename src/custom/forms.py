from django import forms
from django.contrib.auth.forms import (
    ReadOnlyPasswordHashField,
)
from django.utils.translation import gettext_lazy as _

from .models import CustomUser


class CustomUserCreationForm( forms.ModelForm ):

    class Meta:
        model = CustomUser
        fields = (
            'email',
            'first_name',
            'last_name',
            'is_staff',
        )

    def save(self, commit=True):
        # Save without setting a password
        user = super().save( commit = False )
        if commit:
            user.save()
        return user


class CustomUserChangeForm(forms.ModelForm):

    password = ReadOnlyPasswordHashField(
        label = _("Password"),
        help_text = _(
            "Raw passwords are not stored, so there is no way to see this "
            "user’s password, but you can change the password using "
            '<a href="{}">this form</a>.'
        ),
    )

    class Meta:
        model = CustomUser
        fields = "__all__"
        field_classes = { "email": forms.CharField }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        password = self.fields.get("password")
        if password:
            password.help_text = password.help_text.format(
                f"../../{self.instance.pk}/password/"
            )
        user_permissions = self.fields.get("user_permissions")
        if user_permissions:
            user_permissions.queryset = user_permissions.queryset.select_related(
                "content_type"
            )
