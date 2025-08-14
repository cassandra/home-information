from .audio_manager import AudioManager


class AudioMixin:
    """Mixin to provide easy access to the audio manager."""
    
    def audio_manager(self) -> AudioManager:
        """Get the audio manager singleton instance."""
        manager = AudioManager()
        manager.ensure_initialized()
        return manager
