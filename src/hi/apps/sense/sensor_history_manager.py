import logging
from typing import List

from hi.apps.common.singleton import Singleton

from .transient_models import SensorResponse

logger = logging.getLogger(__name__)


class SensorHistoryManager( Singleton ):
    
    def __init_singleton__( self ):
        return
    
    def add_to_sensor_response_history( self, sensor_response_list : List[ SensorResponse ] ):
        if not sensor_response_list:
            return

        # TODO: Implement me!
        return
