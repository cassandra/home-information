from django.http import Http404

from .integration_manager import IntegrationManager


class IntegrationViewMixin:

    def get_integration_data( self, integration_id : str ):
        try:
            return IntegrationManager().get_integration_data(
                integration_id = integration_id,
            )
        except KeyError:
            raise Http404()
        return
    
    def get_integration_data_list( self, enabled_only = False ):
        return IntegrationManager().get_integration_data_list(
            enabled_only = enabled_only,
        )
    
