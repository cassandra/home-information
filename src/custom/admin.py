from django.contrib import admin

from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _


from .forms import (
    CustomUserChangeForm,
    CustomUserCreationForm,
)
from .models import CustomUser


@admin.register( CustomUser )
class CustomUserAdmin( UserAdmin ):
    model = CustomUser
    add_form = CustomUserCreationForm

    # Fields for the user creation form
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "first_name",
                    "last_name",
                    "is_staff",
                ),
            },
        ),
    )

    # Fields for the user edit form
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_("Personal info"), {"fields": ("first_name", "last_name")}),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "email_verified",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )

    form = CustomUserChangeForm
    add_form = CustomUserCreationForm
    list_display = ("email", "uuid", "first_name", "last_name", "email_verified", "is_staff")
    list_filter = ("is_staff", "is_superuser", "is_active", "groups")
    search_fields = ( "email", "uuid" )
    ordering = ("id",)
