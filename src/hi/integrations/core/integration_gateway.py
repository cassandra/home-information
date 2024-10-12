from django.http import HttpRequest, HttpResponse

from .enums import IntegrationType
from .models import Integration


class IntegrationGateway:
    """ 
    Each integration needs to provide an Integration Manager that implements these methods.
    """
    
    def enable( self, request : HttpRequest, *args, **kwargs ) -> HttpResponse:
        # Should return a modal via antinode.modal_from_template() (called async)
        raise NotImplementedError('Subclasses must override this method')
    
    def disable( self, request : HttpRequest, *args, **kwargs ) -> HttpResponse:
        # Should return a modal via antinode.modal_from_template() (called async)
        raise NotImplementedError('Subclasses must override this method')
    
    def manage( self, request : HttpRequest, *args, **kwargs ) -> HttpResponse:
        # Should return HTML fragment for the management pane of the integration.
        raise NotImplementedError('Subclasses must override this method')

    def get_integration( self, integration_type : IntegrationType ) -> Integration:
        try:
            return Integration.objects.get( integration_type_str = str(integration_type) )
        except Integration.DoesNotExist:
            return Integration(
                integration_type_str = str(integration_type),
                is_enabled = False,
            )

    
