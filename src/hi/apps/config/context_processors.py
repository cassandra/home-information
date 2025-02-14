from hi.apps.console.console_mixin import ConsoleMixin
from hi.apps.console.settings import ConsoleSetting

from .settings_mixins import SettingsMixin


def settings_context(request):
    settings_manager = SettingsMixin().settings_manager()
    console_manager = ConsoleMixin().console_manager()
    return {
        'USER_TIMEZONE': settings_manager.get_setting_value( ConsoleSetting.TIMEZONE ),
        'CONSOLE_AUDIO_MAP': console_manager.get_console_audio_map(),
        'SLEEP_OVERLAY_OPACITY': console_manager.get_sleep_overlay_opacity(),
    }
