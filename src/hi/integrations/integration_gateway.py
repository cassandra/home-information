from typing import Optional

from hi.apps.entity.models import Entity
from hi.apps.entity.transient_models import VideoStream
from hi.apps.monitor.periodic_monitor import PeriodicMonitor
from hi.apps.sense.transient_models import SensorResponse

from .integration_controller import IntegrationController
from .integration_manage_view_pane import IntegrationManageViewPane
from .transient_models import IntegrationMetaData


class IntegrationGateway:
    """ 
    Each integration needs to provide an Integration Manager that implements these methods.
    """

    def get_metadata(self) -> IntegrationMetaData:
        raise NotImplementedError('Subclasses must override this method')
        
    def get_manage_view_pane(self) -> IntegrationManageViewPane:
        raise NotImplementedError('Subclasses must override this method')
    
    def get_monitor(self) -> PeriodicMonitor:
        raise NotImplementedError('Subclasses must override this method')
    
    def get_controller(self) -> IntegrationController:
        raise NotImplementedError('Subclasses must override this method')
    
    def get_entity_video_stream(self, entity: Entity) -> Optional[VideoStream]:
        """Get entity's primary video stream (typically live)
        
        Args:
            entity: Entity instance to get video stream for
            
        Returns:
            VideoStream object or None if entity has no video stream
        """
        return None
        
    def get_sensor_response_video_stream(self, sensor_response: SensorResponse) -> Optional[VideoStream]:
        """Get video stream from sensor response (recorded events)
        
        Args:
            sensor_response: SensorResponse instance to get video stream for
            
        Returns:
            VideoStream object or None if sensor response has no video stream
        """
        return None
