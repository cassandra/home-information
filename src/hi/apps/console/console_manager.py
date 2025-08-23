import logging
from typing import List

from hi.apps.common.singleton import Singleton
from hi.apps.config.settings_mixins import SettingsMixin
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
        # TODO: Phase 4 - Rebuild this method to use has_video_stream=True entities
        # and the new VideoStream infrastructure instead of VIDEO_STREAM EntityStates.
        # VideoStreamEntity dataclass will likely be replaced with direct Entity + VideoStream approach.
        # For now, returning empty list since VIDEO_STREAM EntityState has been removed.
        
        return []
    
