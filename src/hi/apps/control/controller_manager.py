from asgiref.sync import sync_to_async
import logging

from hi.apps.common.singleton import Singleton

from hi.integrations.integration_manager import IntegrationManager
from hi.integrations.transient_models import IntegrationControlResult

from .models import Controller

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
                    control_value  : str ) -> IntegrationControlResult:
        logger.debug( f'Controller action: {controller} = {control_value}' )

        integration_gateway = IntegrationManager().get_integration_gateway(
            integration_id = controller.integration_id,
        )
        integration_controller = integration_gateway.get_controller()
        
        control_result = integration_controller.do_control(
            integration_key = controller.integration_key,
            control_value = control_value,
        )
        return control_result

    async def do_control_async( self,
                                controller    : Controller,
                                control_value : str ) -> IntegrationControlResult:
        return await sync_to_async( self.do_control )(
            controller = controller,
            control_value = control_value,
        )
    
