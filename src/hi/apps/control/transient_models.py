from dataclasses import dataclass
from typing import List

from hi.apps.sense.transient_models import SensorResponse

from .models import Controller


@dataclass
class ControllerData:
    controller              : Controller
    latest_sensor_response  : SensorResponse
    error_list              : List[ str ]    = None
    
    @property
    def css_class(self):
        return self.controller.entity_state.css_class
    

@dataclass
class ControllerOutcome:
    controller              : Controller
    new_value               : str
    error_list              : List[ str ]    = None
    
    @property
    def has_errors(self):
        return bool( self.error_list )
    
