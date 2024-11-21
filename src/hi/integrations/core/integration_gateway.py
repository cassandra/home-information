from django.http import HttpRequest, HttpResponse

from hi.apps.monitor.periodic_monitor import PeriodicMonitor

from .transient_models import IntegrationMetaData


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
    
