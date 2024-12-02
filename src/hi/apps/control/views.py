import logging

from django.views.generic import View

from hi.integrations.core.integration_factory import IntegrationFactory
from .view_mixin import ControlViewMixin

logger = logging.getLogger(__name__)


class ControllerView( View, ControlViewMixin ):

    def post( self, request, *args, **kwargs ):
        controller = self.get_controller( request, *args, **kwargs )
        control_value = request.POST.get( 'value' )
        logger.debug( f'Setting discrete controller = "{control_value}"' )



        

        # Check the entity_state_type and sanity check/conmvert as needed.

        # zzz Sanity check value is in value_range


        # zzz Check against latest state value????



        
        
        error_messages = list()

        integration_gateway = IntegrationFactory().get_integration_gateway(
            integration_id = controller.integration_id,
        )

        control_result = integration_gateway.do_control(
            controller_integration_key = controller.integration_key,
            control_value = control_value,
        )

        return self.controller_data_response(
            request = request,
            controller = controller,
            error_messages = error_messages,
        )
