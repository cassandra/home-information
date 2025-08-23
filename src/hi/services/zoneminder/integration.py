import logging
from typing import Optional

from hi.apps.entity.models import Entity
from hi.apps.entity.transient_models import VideoStream
from hi.apps.entity.enums import VideoStreamType
from hi.apps.sense.transient_models import SensorResponse
from hi.integrations.integration_controller import IntegrationController
from hi.integrations.integration_gateway import IntegrationGateway
from hi.integrations.integration_manage_view_pane import IntegrationManageViewPane
from hi.integrations.transient_models import IntegrationMetaData
from hi.apps.monitor.periodic_monitor import PeriodicMonitor

from .zm_controller import ZoneMinderController
from .zm_manage_view_pane import ZmManageViewPane
from .zm_metadata import ZmMetaData
from .monitors import ZoneMinderMonitor
from .zm_mixins import ZoneMinderMixin

logger = logging.getLogger(__name__)


class ZoneMinderGateway( IntegrationGateway, ZoneMinderMixin ):

    def get_metadata(self) -> IntegrationMetaData:
        return ZmMetaData

    def get_manage_view_pane(self) -> IntegrationManageViewPane:
        return ZmManageViewPane()
    
    def get_monitor(self) -> PeriodicMonitor:
        return ZoneMinderMonitor()
    
    def get_controller(self) -> IntegrationController:
        return ZoneMinderController()
    
    def get_entity_video_stream(self, entity: Entity) -> Optional[VideoStream]:
        """Get entity's primary video stream (typically live)"""
        if not entity.has_video_stream:
            return None
            
        # Check if this is a ZoneMinder camera entity
        if (entity.integration_id == ZmMetaData.integration_id
                and entity.integration_name
                and entity.integration_name.startswith(self.zm_manager().ZM_MONITOR_INTEGRATION_NAME_PREFIX)):
            
            # Extract monitor ID from integration name (format: "monitor.{id}")
            try:
                monitor_id = int(entity.integration_name.split('.')[1])
                video_url = self.zm_manager().get_video_stream_url(monitor_id)
                
                return VideoStream(
                    stream_type=VideoStreamType.URL,
                    source_url=video_url,
                    metadata={'monitor_id': monitor_id, 'stream_type': 'live'}
                )
            except (IndexError, ValueError):
                logger.warning(f"Could not parse monitor ID from entity integration name: {entity.integration_name}")
                
        return None
        
    def get_sensor_response_video_stream(self, sensor_response: SensorResponse) -> Optional[VideoStream]:
        """Get video stream from sensor response (recorded events)"""
        if not sensor_response.has_video_stream:
            return None
            
        # Check if this sensor response has an event ID in its detail_attrs
        if (sensor_response.detail_attrs
                and 'event_id' in sensor_response.detail_attrs):
            
            try:
                event_id = int(sensor_response.detail_attrs['event_id'])
                video_url = self.zm_manager().get_event_video_stream_url(event_id)
                
                return VideoStream(
                    stream_type=VideoStreamType.URL,
                    source_url=video_url,
                    metadata={'event_id': event_id, 'stream_type': 'recorded'}
                )
            except (ValueError, TypeError):
                logger.warning(f"Could not parse event ID from sensor response: {sensor_response.detail_attrs}")
                
        return None
