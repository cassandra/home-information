import json
from typing import List

from hi.apps.control.enums import ControllerType
from hi.apps.control.models import Controller
from hi.apps.entity.enums import EntityStateType
from hi.apps.entity.models import Entity, EntityState
from hi.apps.sense.enums import SensorType
from hi.apps.sense.models import Sensor


class EntityHelpers:

    @classmethod
    def create_movement_sensor( cls, entity : Entity ):
        name = f'{entity.name} Motion'
        entity_state = EntityState.objects.create(
            entity = entity,
            entity_state_type_str = str( EntityStateType.MOVEMENT ),
            name = name,
            value_range = '',
            units = None,
        )
        sensor = Sensor.objects.create(
            entity_state = entity_state,
            sensor_type_str = str( SensorType.DEFAULT ),
            name = name,
        )
        return sensor

    @classmethod
    def create_video_stream_sensor( cls, entity : Entity ):
        name = f'{entity.name} Stream'
        entity_state = EntityState.objects.create(
            entity = entity,
            entity_state_type_str = str( EntityStateType.VIDEO_STREAM ),
            name = name,
            value_range = '',
            units = None,
        )
        sensor = Sensor.objects.create(
            entity_state = entity_state,
            sensor_type_str = str( SensorType.DEFAULT ),
            name = name,
        )
        return sensor

    @classmethod
    def create_discrete_controller( cls,
                                    entity      : Entity,
                                    name        : str,
                                    value_list  : List[ str ],
                                    is_sensed   : bool         = True ):
        entity_state = EntityState.objects.create(
            entity = entity,
            entity_state_type_str = str( EntityStateType.DICRETE ),
            name = name,
            value_range = json.dumps( value_list ),
            units = None,
        )
        if is_sensed:
            _ = Sensor.objects.create(
                entity_state = entity_state,
                sensor_type_str = str( SensorType.DEFAULT ),
                name = name,
            )
        controller = Controller.objects.create(
            entity_state = entity_state,
            controller_type_str = str( ControllerType.DEFAULT ),
            name = name,
        )
        return controller
