from .settings_manager import SettingsManager


def settings_context(request):
    settings_manager = SettingsManager()
    return {
        'CONSOLE_AUDIO_MAP': settings_manager.get_console_audio_map(),
    }
