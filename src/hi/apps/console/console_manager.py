import logging
from typing import Dict

from django.http import HttpRequest
from django.template.loader import get_template

from hi.apps.common.singleton import Singleton
from hi.apps.config.settings_manager import SettingsManager

from .audio_file import AudioFile
from .audio_signal import AudioSignal
from .constants import ConsoleConstants

logger = logging.getLogger(__name__)


class ConsoleManager(Singleton):

    def __init_singleton__(self):
        self._console_audio_map = self._build_console_audio_map()
        SettingsManager().register_change_listener( self._reload_console_audio_map )
        return

    def is_console_locked( self, request : HttpRequest ) -> bool:
        return request.session.get( ConsoleConstants.CONSOLE_LOCKED_SESSION_VAR, False )

    def get_console_audio_map( self ) -> Dict[ str, str ]:
        return self._console_audio_map
    
    def _reload_console_audio_map( self ) -> Dict[ str, str ]:
        logger.debug( 'Reloading console audio map' )
        self._console_audio_map = self._build_console_audio_map()
        return
    
    def _build_console_audio_map( self ) -> Dict[ str, str ]:
        logger.debug( 'Building console audio map' )
        settings_manager = SettingsManager()
        console_audio_map = dict()
        for audio_signal in AudioSignal:
            if audio_signal.console_setting:
                attr_value = settings_manager.get_setting_value( audio_signal.console_setting )
                if attr_value:
                    audio_file = AudioFile.from_name( attr_value )
                    console_audio_map[str(audio_signal)] = audio_file.url
            continue
        return console_audio_map
    
