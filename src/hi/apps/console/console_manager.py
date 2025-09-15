import logging
from typing import Dict, List, Optional
from cachetools import TTLCache

from django.http import HttpRequest
from django.template.loader import get_template

from hi.constants import DIVID

from hi.apps.common.singleton import Singleton
from hi.apps.config.settings_mixins import SettingsMixin
from hi.apps.entity.entity_manager import EntityManager
from hi.apps.entity.models import Entity, EntityState
from hi.apps.entity.enums import EntityStateType
from hi.apps.sense.sensor_response_manager import SensorResponseMixin

from .constants import ConsoleConstants
from .transient_models import CameraControlDisplayData

logger = logging.getLogger(__name__)


class ConsoleManager( Singleton, SettingsMixin, SensorResponseMixin ):

    # TTL cache settings
    CAMERA_CONTROL_CACHE_SIZE = 5
    CAMERA_CONTROL_CACHE_TTL_SECS = 300  # 5 minutes

    # Priority order for status entity state selection
    STATUS_ENTITY_STATE_PRIORITY = [
        EntityStateType.MOVEMENT,
        EntityStateType.PRESENCE, 
        EntityStateType.OPEN_CLOSE,
        EntityStateType.ON_OFF,
        EntityStateType.HIGH_LOW,
        EntityStateType.CONNECTIVITY,
    ]

    def __init_singleton__(self):
        self._was_initialized = False
        self._camera_control_cache = TTLCache(
            maxsize=self.CAMERA_CONTROL_CACHE_SIZE,
            ttl=self.CAMERA_CONTROL_CACHE_TTL_SECS
        )
        return

    def ensure_initialized(self):
        if self._was_initialized:
            return
        
        EntityManager().register_change_listener( self._invalidate_camera_control_cache )

        self._was_initialized = True
        return

    def get_status_id_replace_map( self, request : HttpRequest ) -> Dict[ str, str ]:

        context = dict()
        template = get_template( ConsoleConstants.DATETIME_HEADER_TEMPLATE_NAME )
        datetime_header_html_str = template.render( context, request = request )
        return {
            DIVID['DATETIME_HEADER']: datetime_header_html_str,
        }
        
    def get_camera_control_display_list(self) -> List[CameraControlDisplayData]:
        """Get camera control display data with TTL caching."""
        self.ensure_initialized()
        
        cache_key = 'camera_control_display_list'
        cached_result = self._camera_control_cache.get(cache_key)
        
        if cached_result is not None:
            return cached_result
        
        # Build fresh data
        display_data_list = self._build_camera_control_display_list()
        self._camera_control_cache[cache_key] = display_data_list
        
        return display_data_list

    def get_video_stream_entity_list(self) -> List[Entity]:
        """Legacy method - now extracts entities from camera control display data."""
        display_data_list = self.get_camera_control_display_list()
        return [data.entity for data in display_data_list]

    def _invalidate_camera_control_cache(self):
        """Invalidate cache when entity data changes."""
        self._camera_control_cache.clear()
        return

    def _build_camera_control_display_list(self) -> List[CameraControlDisplayData]:
        """Build camera control display data with status entity states."""
        # Get entities with prefetched states in one efficient query
        entity_list = list(
            Entity.objects
            .filter(has_video_stream=True)
            .prefetch_related('states')
            .order_by('name')
        )
        
        display_data_list = []
        for entity in entity_list:
            status_entity_state = self._find_priority_entity_state(entity)
            display_data = CameraControlDisplayData(
                entity=entity,
                status_entity_state=status_entity_state
            )
            display_data_list.append(display_data)
        
        return display_data_list

    def _find_priority_entity_state(self, entity: Entity) -> Optional[EntityState]:
        """Find the highest priority entity state for the given entity."""
        # Get all states once - benefits from prefetch_related caching
        entity_states = entity.states.all()
        
        # Process in memory - no additional DB queries
        for state_type in self.STATUS_ENTITY_STATE_PRIORITY:
            for entity_state in entity_states:
                if entity_state.entity_state_type_str == str(state_type):
                    return entity_state
        
        return None
    
