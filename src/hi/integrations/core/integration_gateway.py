from django.http import HttpRequest, HttpResponse

from .transient_models import IntegrationMetaData


class IntegrationGateway:
    """ 
    Each integration needs to provide an Integration Manager that implements these methods.
    """

    def get_meta_data(self) -> IntegrationMetaData:
        raise NotImplementedError('Subclasses must override this method')
        
    def enable_modal_view( self, request : HttpRequest, *args, **kwargs ) -> HttpResponse:
        # Should return a modal via antinode.modal_from_template() (called async)
        raise NotImplementedError('Subclasses must override this method')
    
    def disable_modal_view( self, request : HttpRequest, *args, **kwargs ) -> HttpResponse:
        # Should return a modal via antinode.modal_from_template() (called async)
        raise NotImplementedError('Subclasses must override this method')
    
    def manage_pane_view( self, request : HttpRequest, *args, **kwargs ) -> HttpResponse:
        # Should return HTML fragment for the management pane of the integration.
        raise NotImplementedError('Subclasses must override this method')
    
