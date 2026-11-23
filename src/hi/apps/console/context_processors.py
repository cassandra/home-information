from django.utils.functional import SimpleLazyObject

from hi.apps.console.console_helper import ConsoleSettingsHelper
from hi.apps.console.sleep_mode import SleepModeCookie


def settings_context(request):
    console_helper = ConsoleSettingsHelper()
    return {
        'USER_TIMEZONE': console_helper.get_tz_name(),
        'SLEEP_OVERLAY_OPACITY': console_helper.get_sleep_overlay_opacity(),
        'SLEEP_MODE_ACTIVE': SleepModeCookie.is_active( request ),
    }


def device_capabilities_context(request):
    # Lazy, like client_config: only templates that use it pay for it.
    return {
        'device_capabilities': SimpleLazyObject( lambda: request.device_capabilities ),
    }
