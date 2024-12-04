import logging
from typing import List

from hi.apps.common.singleton import Singleton
from hi.apps.monitor.status_display_manager import StatusDisplayManager

from .models import Controller
from .transient_models import ControllerData

logger = logging.getLogger(__name__)


class ControllerManager( Singleton ):
    
    def __init_singleton__( self ):
        return
    
    def get_controller_data( self, controller : Controller, error_list : List[ str ] = None ):

        latest_sensor_response = StatusDisplayManager().get_latest_sensor_response(
            entity_state = controller.entity_state,
        )
        return ControllerData(
            controller = controller,
            latest_sensor_response = latest_sensor_response,
            error_list = error_list,
        )
