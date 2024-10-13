import logging

from django.views.generic import View

from hi.views import bad_request_response

from .integration_factory import IntegrationFactory

logger = logging.getLogger(__name__)


class IntegrationViewMixin:

    def get_integration_config_tab_context(self):
        return {
            'integration_data_list': IntegrationFactory().get_integration_data_list(),
        }

    
class IntegrationActionView( View ):

    def get(self, request, *args, **kwargs):

        error_message = None
        try:        
            integration_id = kwargs.get('integration_id')
            action = kwargs.get('action')

            integration_gateway = IntegrationFactory().get_integration_gateway(
                integration_id = integration_id,
            )
        
            if action == 'enable':
                return integration_gateway.enable_modal_view( request = request, *args, **kwargs )
            elif action == 'disable':
                return integration_gateway.disable_modal_view( request = request, *args, **kwargs )
            elif action == 'manage':
                return integration_gateway.manage_pane_view( request = request, *args, **kwargs )

            error_message = f'Unknown integration action "{action}".'
        except Exception as e:
            error_message = str(e)

        return bad_request_response( request, message = error_message )
