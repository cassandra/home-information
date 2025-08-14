import logging
from typing import Dict

from hi.apps.common.singleton import Singleton
from hi.apps.config.settings_mixins import SettingsMixin

from .audio_file import AudioFile
from .audio_signal import AudioSignal

logger = logging.getLogger(__name__)


class AudioManager(Singleton, SettingsMixin):
    """
    Enhanced audio manager that replaces console audio functionality.
    
    Provides audio signal to URL mapping for the enhanced audio system
    that supports weather vs event differentiation and tornado-specific handling.
    """

    def __init_singleton__(self):
        self._was_initialized = False
        return

    def ensure_initialized(self):
        if self._was_initialized:
            return
        
        self.settings_manager().register_change_listener(self._reload_audio_map)
        self._audio_map = self._build_audio_map()
        self._was_initialized = True
        return

    def get_audio_map(self) -> Dict[str, str]:
        """Get mapping of audio signal names to their file URLs."""
        return self._audio_map

    def _reload_audio_map(self):
        """Reload audio map when settings change."""
        logger.debug('Reloading audio map')
        self._audio_map = self._build_audio_map()
        return

    def _build_audio_map(self) -> Dict[str, str]:
        """Build audio signal to URL mapping from current settings."""
        logger.debug('Building audio map')
        settings_manager = self.settings_manager()

        audio_map = dict()
        for audio_signal in AudioSignal:
            if audio_signal.audio_setting:
                attr_value = settings_manager.get_setting_value(audio_signal.audio_setting)
                if attr_value:
                    audio_file = AudioFile.from_name(attr_value)
                    audio_map[audio_signal.label] = audio_file.url
            continue
        return audio_map