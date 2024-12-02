from dataclasses import dataclass
from typing import List

from hi.apps.sense.transient_models import SensorResponse

from .models import Controller


@dataclass
class ControllerData:
    controller              : Controller
    latest_sensor_response  : SensorResponse
    error_messages          : List[ str ]    = None
    
    
