from typing import Dict, List, Optional

from hi.apps.entity.models import Entity
from hi.apps.entity.transient_models import VideoStream
from hi.apps.monitor.periodic_monitor import PeriodicMonitor
from hi.apps.sense.transient_models import SensorResponse

from .integration_controller import IntegrationController
from .integration_manage_view_pane import IntegrationManageViewPane
from .models import IntegrationAttribute
from .transient_models import IntegrationMetaData, IntegrationHealthStatus


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
    
    def notify_settings_changed(self):
        """Notify the integration that its settings have changed.
        
        This method is called when Integration or IntegrationAttribute models
        are modified. Each integration should implement this to reload its
        configuration and notify any dependent components.
        """
        raise NotImplementedError('Subclasses must override this method')
    
    def get_health_status(self) -> IntegrationHealthStatus:
        """Get the current health status of this integration.
        
        Returns:
            IntegrationHealthStatus object with current status, error details,
            and last check time for this integration.
        """
        raise NotImplementedError('Subclasses must override this method')
    
    def validate_configuration(self, integration_attributes: List[IntegrationAttribute]) -> Dict[str, any]:
        """Validate integration configuration by testing API connectivity.
        
        Tests the provided configuration attributes by attempting to create
        and test an API client without affecting the integration's state.
        
        Args:
            integration_attributes: List of IntegrationAttribute objects with configuration
            
        Returns:
            Dictionary with validation result:
            {
                'success': bool,
                'error_message': str or None,
                'error_type': 'config'|'connection'|'auth'|'unknown' or None
            }
        """
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
