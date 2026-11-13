import os

from django.core.exceptions import ImproperlyConfigured

SETTINGS_MODULE_VAR = 'DJANGO_SETTINGS_MODULE'


def require_settings_module() -> None:
    """
    Fail fast when DJANGO_SETTINGS_MODULE is not set.

    There is deliberately no default. The bare 'hi.settings' package has no
    __init__.py, so it imports as an empty namespace package and Django would
    boot with no INSTALLED_APPS, failing much later with an unrelated-looking
    error.
    """
    if os.environ.get( SETTINGS_MODULE_VAR ):
        return
    raise ImproperlyConfigured(
        f'{SETTINGS_MODULE_VAR} is not set. Set it to one of the modules in'
        ' hi/settings/, e.g., hi.settings.local or hi.settings.production'
        ' (see local.env.example).'
    )
