from hi.apps.monitor.periodic_monitor import PeriodicMonitor

from .integration_controller import IntegrationController
from .transient_models import IntegrationMetaData


class IntegrationGateway:
    """ 
    Each integration needs to provide an Integration Manager that implements these methods.
    """

    def get_metadata(self) -> IntegrationMetaData:
        raise NotImplementedError('Subclasses must override this method')
        
    def get_monitor(self) -> PeriodicMonitor:
        raise NotImplementedError('Subclasses must override this method')
    
    def get_controller(self) -> IntegrationController:
        raise NotImplementedError('Subclasses must override this method')
