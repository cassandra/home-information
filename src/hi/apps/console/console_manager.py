import logging
from typing import Dict, List

from hi.apps.common.singleton import Singleton
from hi.apps.config.settings_mixins import SettingsMixin
from hi.apps.entity.enums import EntityStateType
from hi.apps.entity.entity_manager import EntityManager

from hi.apps.sense.sensor_response_manager import SensorResponseMixin

from .transient_models import VideoStreamEntity

logger = logging.getLogger(__name__)


class ConsoleManager( Singleton, SettingsMixin, SensorResponseMixin ):

    def __init_singleton__(self):
        self._was_initialized = False
        return

    def ensure_initialized(self):
        if self._was_initialized:
            return
        
        EntityManager().register_change_listener( self._reload_video_stream_entity_list )

        self._video_stream_entity_list = self._build_video_stream_entity_list()

        self._was_initialized = True
        return

    def get_video_stream_entity_list( self ) -> List[ VideoStreamEntity ]:
        return self._video_stream_entity_list

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
    
