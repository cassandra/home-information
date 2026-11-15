import os

from django.core.exceptions import ImproperlyConfigured

# This package holds one settings module per environment and is not itself
# a settings module. Selecting it (including via the entry points' default)
# would otherwise boot Django with an empty INSTALLED_APPS.
if os.environ.get( 'DJANGO_SETTINGS_MODULE' ) == __name__:
    raise ImproperlyConfigured(
        'DJANGO_SETTINGS_MODULE must name a concrete settings module such as'
        ' hi.settings.local or hi.settings.production (see local.env.example).'
    )
