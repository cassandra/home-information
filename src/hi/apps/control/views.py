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

        integration_gateway = IntegrationFactory().get_integration_gateway(
            integration_id = controller.integration_id,
        )
        integration_controller = integration_gateway.get_controller()
        
        control_result = integration_controller.do_control(
            integration_key = controller.integration_key,
            control_value = control_value,
        )
        if control_result.has_errors:
            override_sensor_value = None
        else:
            override_sensor_value = control_value
            
        return self.controller_data_response(
            request = request,
            controller = controller,
            error_list = control_result.error_list,
            override_sensor_value = override_sensor_value,
        )
