from .audio_mixins import AudioMixin


def audio_context(request):
    """Provide audio-related context variables for templates."""
    audio_manager = AudioMixin().audio_manager()
    return {
        'AUDIO_MAP': audio_manager.get_audio_map(),
    }