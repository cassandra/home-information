from hi.apps.console.console_manager import ConsoleManager


def settings_context(request):
    console_manager = ConsoleManager()
    return {
        'CONSOLE_AUDIO_MAP': console_manager.get_console_audio_map(),
        'SLEEP_OVERLAY_OPACITY': console_manager.get_sleep_overlay_opacity(),
    }
