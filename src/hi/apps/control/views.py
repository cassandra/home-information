import logging

from django.views.generic import View

from hi.apps.monitor.status_display_manager import StatusDisplayManager

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

        # Because we use polling to fetch state/sensor values, when using a
        # controller to change the value, the value can immediately differ
        # from what we saw in the last polling interval.  This is
        # exacerbated because the server polls the sources for the value
        # and the UI/client polls the server. These two polling intervals
        # are not coordinated. To solve for this we do two things.
        #
        #  1) We immediately render to updated value to the UI/client.
        #
        #  2) We temporarily override the value in the
        #     StatusDisplayManager. This is to guard against the UI/client
        #     polling happening beforee the server has been able to update
        #     itrs values.  This override is temporary and expires in a
        #     time just longer than the polling intervals' maximum gaps.

        if control_result.has_errors:
            override_sensor_value = None
        else:
            override_sensor_value = control_value
            StatusDisplayManager().add_entity_state_value_override(
                entity_state = controller.entity_state,
                override_value = control_value,
            )
            
        return self.controller_data_response(
            request = request,
            controller = controller,
            error_list = control_result.error_list,
            override_sensor_value = override_sensor_value,
        )
