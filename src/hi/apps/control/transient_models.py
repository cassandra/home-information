from dataclasses import dataclass
from typing import List

from django.urls import reverse

from hi.apps.sense.transient_models import SensorResponse

from .models import Controller


@dataclass
class ControllerData:
    controller              : Controller
    latest_sensor_response  : SensorResponse
    error_list              : List[ str ]    = None

    @property
    def entity(self):
        return self.controller.entity_state.entity

    @property
    def entity_state(self):
        return self.controller.entity_state

    @property
    def controller_history_url(self):
        return reverse( 'control_controller_history',
                        kwargs = { 'controller_id': self.controller.id })        
        
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
    
