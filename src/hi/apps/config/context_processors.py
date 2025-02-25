from hi.apps.console.console_helper import ConsoleSettingsHelper
from hi.apps.console.console_mixins import ConsoleMixin


def settings_context(request):
    console_helper = ConsoleSettingsHelper()
    console_manager = ConsoleMixin().console_manager()
    return {
        'USER_TIMEZONE': console_helper.get_tz_name(),
        'SLEEP_OVERLAY_OPACITY': console_helper.get_sleep_overlay_opacity(),
        'CONSOLE_AUDIO_MAP': console_manager.get_console_audio_map(),
    }
