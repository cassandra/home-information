from dataclasses import dataclass
from datetime import datetime
from typing import List

from django.urls import reverse

from hi.apps.sense.transient_models import SensorResponse

from .models import Controller, ControllerHistory


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
class ControllerHistoryResponse:
    """Adapter exposing a ControllerHistory row through the surface the
    per-state-type value templates read from a SensorResponse:
    ``.value``, ``.timestamp``, ``.entity_state``. Used by the controller
    history list so it dispatches through
    ``EntityStateType.value_template_name`` — the canonical read-only
    value display — instead of the interactive controller widget.

    The loop-variable name ``sensor_response`` in the per-state-type
    templates is a duck-typed slot: both ``SensorResponse`` and this
    adapter satisfy the access pattern. A neutral rename of the
    template variable lives with the merged-history work in #323."""

    value      : str
    timestamp  : datetime
    controller : Controller

    @classmethod
    def from_controller_history( cls, controller_history : ControllerHistory ) -> 'ControllerHistoryResponse':
        return cls(
            value = controller_history.value,
            timestamp = controller_history.created_datetime,
            controller = controller_history.controller,
        )

    @property
    def entity_state(self):
        return self.controller.entity_state


@dataclass
class ControllerOutcome:
    controller              : Controller
    new_value               : str
    error_list              : List[ str ]    = None
    
    @property
    def has_errors(self):
        return bool( self.error_list )
    
