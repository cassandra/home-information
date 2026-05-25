from asgiref.sync import sync_to_async
import logging

from django.conf import settings

from hi.apps.common.singleton import Singleton

from hi.integrations.integration_manager import IntegrationManager
from hi.testing.dev_overrides import DevOverrideManager

from .controller_history_manager import ControllerHistoryManager
from .models import Controller
from .transient_models import ControllerOutcome

logger = logging.getLogger(__name__)


class ControllerManager( Singleton ):
    
    def __init_singleton__( self ):
        self._was_initialized = False
        return
    
    def ensure_initialized(self):
        if self._was_initialized:
            return
        # Any future heavyweight initializations go here (e.g., any DB operations).
        self._was_initialized = True
        return

    def do_control( self,
                    controller     : Controller,
                    control_value  : str ) -> ControllerOutcome:
        logger.debug( f'Controller action: {controller} = {control_value}' )

        integration_gateway = IntegrationManager().get_integration_gateway(
            integration_id = controller.integration_id,
        )
        connector = integration_gateway.get_connector()
        if connector is None:
            raise RuntimeError(
                f'No connector for integration {controller.integration_id}; '
                f'cannot route control action.'
            )
        integration_controller = connector.get_controller()
        if integration_controller is None:
            raise RuntimeError(
                f'Integration {controller.integration_id} has no controller; '
                f'cannot route control action.'
            )

        integration_details = controller.get_integration_details()
        if settings.DEBUG and settings.DEBUG_TRACE_STATE:
            DevOverrideManager.trace_state(
                'hi.control.out',
                integration_name = integration_details.key.integration_name,
                hi_entity_state_id = controller.entity_state.id,
                hi_value = control_value,
            )

        control_result = integration_controller.do_control(
            integration_details = integration_details,
            hi_control_value = control_value,
        )
        if not control_result.has_errors:
            ControllerHistoryManager().add_to_controller_history(
                controller = controller,
                value = control_result.new_value,
            )
        
        return ControllerOutcome(
            controller = controller,
            new_value = control_result.new_value,
            error_list = control_result.error_list,
        )

    async def do_control_async( self,
                                controller    : Controller,
                                control_value : str ) -> ControllerOutcome:
        return await sync_to_async( self.do_control )(
            controller = controller,
            control_value = control_value,
        )
    
