import os

SETTINGS_MODULE_ENV_VAR = 'DJANGO_SETTINGS_MODULE'


def require_settings_module():
    """
    Exit with a clear message unless DJANGO_SETTINGS_MODULE is set.

    'hi.settings' is a package of per-environment modules, not a settings
    module, so there is no sensible default. Without this check Django falls
    back to its global defaults (an empty INSTALLED_APPS) and the process
    fails much later, at the first model import, with an unrelated error.
    """
    if os.environ.get( SETTINGS_MODULE_ENV_VAR ):
        return

    raise SystemExit(
        f'{SETTINGS_MODULE_ENV_VAR} is not set. Set it to the settings module '
        'for this environment, e.g. hi.settings.local or '
        'hi.settings.production (see local.env.example).'
    )
