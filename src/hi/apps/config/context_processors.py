from hi.apps.console.console_manager import ConsoleManager
from hi.apps.console.settings import ConsoleSetting

from .settings_manager import SettingsManager


def settings_context(request):
    console_manager = ConsoleManager()
    return {
        'USER_TIMEZONE': SettingsManager().get_setting_value( ConsoleSetting.TIMEZONE ),
        'CONSOLE_AUDIO_MAP': console_manager.get_console_audio_map(),
        'SLEEP_OVERLAY_OPACITY': console_manager.get_sleep_overlay_opacity(),
    }
