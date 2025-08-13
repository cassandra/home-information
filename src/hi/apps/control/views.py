import logging

from django.urls import reverse
from django.views.generic import View

from hi.apps.common.pagination import compute_pagination_from_queryset
from hi.apps.entity.enums import EntityStateType, EntityStateValue
from hi.apps.monitor.status_display_manager import StatusDisplayManager

from hi.hi_async_view import HiModalView

from .controller_history_manager import ControllerHistoryManager
from .control_mixins import ControllerMixin
from .models import Controller, ControllerHistory
from .view_mixins import ControlViewMixin

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
        control_value = request.POST.get( 'value' )

        # Checkbox case results in no value, so we need to normalize those
        # binary states based on EntityStateType.
        #
        if control_value is None:
            control_value = self._get_value_for_missing_input( controller = controller )

        control_result = self.controller_manager().do_control(
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
            ControllerHistoryManager().add_to_controller_history(
                controller = controller,
                value = control_value,
            )

        return self.controller_data_response(
            request = request,
            controller = controller,
            error_list = control_result.error_list,
            override_sensor_value = override_sensor_value,
        )
    
    def _get_value_for_missing_input( self, controller : Controller ) -> str:
        if controller.entity_state.entity_state_type in self.MISSING_VALUE_MAP:
            return str( self.MISSING_VALUE_MAP.get( controller.entity_state.entity_state_type ))
        return 'unknown'


class ControllerHistoryView( HiModalView, ControlViewMixin ):

    CONTROLLER_HISTORY_PAGE_SIZE = 25
    
    def get_template_name( self ) -> str:
        return 'control/modals/controller_history.html'

    def get( self, request, *args, **kwargs ):

        controller = self.get_controller( request, *args, **kwargs )
        base_url = reverse( 'control_controller_history', kwargs = { 'controller_id': controller.id } )

        queryset = ControllerHistory.objects.filter( controller = controller )
        pagination = compute_pagination_from_queryset( request = request,
                                                       queryset = queryset,
                                                       base_url = base_url,
                                                       page_size = self.CONTROLLER_HISTORY_PAGE_SIZE,
                                                       async_urls = True )
        controller_history_list = queryset[pagination.start_offset:pagination.end_offset + 1]

        context = {
            'controller': controller,
            'controller_history_list': controller_history_list,
            'pagination': pagination,
        }
        return self.modal_response( request, context )
