import logging

from django.views.generic import View

from hi.apps.entity.enums import EntityStateType, EntityStateValue
from hi.apps.monitor.status_display_manager import StatusDisplayManager

from .control_mixins import ControllerMixin
from .models import Controller
from hi.apps.control.view_mixins import ControlViewMixin

logger = logging.getLogger(__name__)


class ControllerView( View, ControlViewMixin, ControllerMixin ):

    MISSING_VALUE_MAP = {
        EntityStateType.MOVEMENT: EntityStateValue.IDLE,
        EntityStateType.PRESENCE: EntityStateValue.IDLE,
        EntityStateType.ON_OFF: EntityStateValue.OFF,
        EntityStateType.OPEN_CLOSE: EntityStateValue.CLOSED,
        EntityStateType.CONNECTIVITY: EntityStateValue.DISCONNECTED,
        EntityStateType.HIGH_LOW: EntityStateValue.LOW,
    }
        
    def post( self, request, *args, **kwargs ):
        controller = self.get_controller( request, *args, **kwargs )
        display_control_value = request.POST.get( 'value' )

        # Checkbox case results in no value, so we need to normalize those
        # binary states based on EntityStateType.
        #
        if display_control_value is None:
            display_control_value = self._get_value_for_missing_input(
                controller = controller,
            )

        control_value = self.to_entity_state_value(
            display_value = display_control_value,
            entity_state = controller.entity_state,
        )

        controller_outcome = self.controller_manager().do_control(
            controller = controller,
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
        #     polling happening before the server has been able to update
        #     itrs values.  This override is temporary and expires in a
        #     time just longer than the polling intervals' maximum gaps.
        
        if controller_outcome.has_errors:
            override_sensor_value = None
        else:
            override_sensor_value = control_value
            StatusDisplayManager().add_entity_state_value_override(
                entity_state = controller.entity_state,
                override_value = override_sensor_value,
            )

        return self.controller_data_response(
            request = request,
            controller = controller,
            error_list = controller_outcome.error_list,
            override_sensor_value = override_sensor_value,
        )
    
    def _get_value_for_missing_input( self, controller : Controller ) -> str:
        if controller.entity_state.entity_state_type in self.MISSING_VALUE_MAP:
            return str( self.MISSING_VALUE_MAP.get( controller.entity_state.entity_state_type ))
        return 'unknown'
