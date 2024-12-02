from django.http import HttpRequest, HttpResponse

from hi.apps.monitor.periodic_monitor import PeriodicMonitor

from .integration_key import IntegrationKey
from .transient_models import IntegrationControlResult, IntegrationMetaData


class IntegrationGateway:
    """ 
    Each integration needs to provide an Integration Manager that implements these methods.
    """

    def get_meta_data(self) -> IntegrationMetaData:
        raise NotImplementedError('Subclasses must override this method')
        
    def get_monitor(self) -> PeriodicMonitor:
        raise NotImplementedError('Subclasses must override this method')
        
    def enable_modal_view( self, request : HttpRequest, *args, **kwargs ) -> HttpResponse:
        # Should return a modal via antinode.modal_from_template() (called async)
        raise NotImplementedError('Subclasses must override this method')
    
    def disable_modal_view( self, request : HttpRequest, *args, **kwargs ) -> HttpResponse:
        # Should return a modal via antinode.modal_from_template() (called async)
        raise NotImplementedError('Subclasses must override this method')
    
    def sensor_response_details_view( self,
                                      request      : HttpRequest,
                                      details_str  : str ) -> HttpResponse:
        # Should return a modal via antinode.modal_from_template() (called async)
        raise NotImplementedError('Subclasses must override this method')

    def do_control( self,
                    controller_integration_key  : IntegrationKey,
                    control_value               : str             ) -> IntegrationControlResult:
        # Should return a modal via antinode.modal_from_template() (called async)
        raise NotImplementedError('Subclasses must override this method')
