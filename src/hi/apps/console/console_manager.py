import logging
from typing import Dict, List

from django.http import HttpRequest

from hi.apps.common.singleton import Singleton
from hi.apps.config.settings_mixins import SettingsMixin
from hi.apps.entity.enums import EntityStateType
from hi.apps.entity.entity_manager import EntityManager
from hi.apps.security.security_mixins import SecurityMixin
from hi.apps.sense.sensor_response_manager import SensorResponseMixin
from hi.apps.weather.weather_mixins import WeatherMixin

from .audio_file import AudioFile
from .audio_signal import AudioSignal
from .constants import ConsoleConstants
from .settings import ConsoleSetting
from .transient_models import VideoStreamEntity

logger = logging.getLogger(__name__)


class ConsoleManager( Singleton, SecurityMixin, SettingsMixin, SensorResponseMixin, WeatherMixin ):

    def __init_singleton__(self):
        self._was_initialized = False
        return

    def ensure_initialized(self):
        if self._was_initialized:
            return
        
        self.settings_manager().register_change_listener( self._reload_console_audio_map )
        EntityManager().register_change_listener( self._reload_video_stream_entity_list )

        self._console_audio_map = self._build_console_audio_map()
        self._video_stream_entity_list = self._build_video_stream_entity_list()

        self._was_initialized = True
        return

    def is_console_locked( self, request : HttpRequest ) -> bool:
        return request.session.get( ConsoleConstants.CONSOLE_LOCKED_SESSION_VAR, False )

    def get_console_audio_map( self ) -> Dict[ str, str ]:
        return self._console_audio_map

    def get_side_template_name_and_context( self, request, *args, **kwargs ):
        context = {
            'weather_overview_data': self.weather_manager().get_weather_overview_data(),
            'security_status_data': self.security_manager().get_security_status_data(),
            'video_stream_entity_list': self._video_stream_entity_list
        }
        return ( 'console/panes/hi_grid_side.html', context )
    
    def get_sleep_overlay_opacity( self ) -> str:
        return self.settings_manager().get_setting_value( ConsoleSetting.SLEEP_OVERLAY_OPACITY )

    def _reload_console_audio_map( self ):
        logger.debug( 'Reloading console audio map' )
        self._console_audio_map = self._build_console_audio_map()
        return

    def _reload_video_stream_entity_list(self):
        self._video_stream_entity_list = self._build_video_stream_entity_list()
        return

    def _build_video_stream_entity_list(self) -> List[ VideoStreamEntity ]:
        # An Entity could have multiple video stream states, and/or
        # multiple sensors for those states. This is an uncommon thing, but
        # supported and dealt with below.
        
        video_stream_entity_list = list()

        entity_list = EntityManager().get_view_stream_entities()
        for entity in entity_list:
            for entity_state in entity.states.all():
                if entity_state.entity_state_type != EntityStateType.VIDEO_STREAM:
                    continue
                for sensor in entity_state.sensors.all():
                    video_stream_entity = VideoStreamEntity(
                        entity = entity,
                        entity_state = entity_state,
                        sensor = sensor,
                    )
                    video_stream_entity_list.append( video_stream_entity )
                    continue
                continue
            continue

        video_stream_entity_list.sort( key = lambda item : item.entity.name )
        return video_stream_entity_list
        
    def _build_console_audio_map( self ) -> Dict[ str, str ]:
        logger.debug( 'Building console audio map' )
        settings_manager = self.settings_manager()

        console_audio_map = dict()
        for audio_signal in AudioSignal:
            if audio_signal.console_setting:
                attr_value = settings_manager.get_setting_value( audio_signal.console_setting )
                if attr_value:
                    audio_file = AudioFile.from_name( attr_value )
                    console_audio_map[str(audio_signal)] = audio_file.url
            continue
        return console_audio_map
    
