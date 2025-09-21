from typing import List, Optional

from hi.apps.entity.models import Entity
from hi.apps.entity.transient_models import VideoStream
from hi.apps.monitor.periodic_monitor import PeriodicMonitor
from hi.apps.sense.transient_models import SensorResponse
from hi.apps.system.health_status_provider import HealthStatusProvider

from .integration_controller import IntegrationController
from .integration_manage_view_pane import IntegrationManageViewPane
from .models import IntegrationAttribute
from .transient_models import (
    IntegrationMetaData,
    IntegrationValidationResult,
)


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
        """
        This method is called when Integration or IntegrationAttribute models
        are modified. Each integration should implement this to reload its
        configuration and notify any dependent components.
        """
        raise NotImplementedError('Subclasses must override this method')
    
    def get_health_status_provider(self) -> HealthStatusProvider:
        raise NotImplementedError('Subclasses must override this method')
    
    def validate_configuration(
            self,
            integration_attributes: List[IntegrationAttribute]
    ) -> IntegrationValidationResult:
        raise NotImplementedError('Subclasses must override this method')
    
    def get_entity_video_stream(self, entity: Entity) -> Optional[VideoStream]:
        return None
        
    def get_sensor_response_video_stream(
            self,
            sensor_response: SensorResponse) -> Optional[VideoStream]:
        return None
