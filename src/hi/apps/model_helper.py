import json
from typing import List

from hi.apps.control.enums import ControllerType
from hi.apps.control.models import Controller
from hi.apps.entity.enums import (
    EntityStateType,
    HumidityUnit,
    TemperatureUnit,
)    
from hi.apps.entity.models import Entity, EntityState
from hi.apps.sense.enums import SensorType
from hi.apps.sense.models import Sensor


class HiModelHelper:
    """ Model creation helpers. """
    
    @classmethod
    def create_blob_sensor( cls,
                            entity           : Entity,
                            integration_id   : str      = None,
                            name             : str      = None ):
        if not name:
            name = f'{entity.name} Blob'
        entity_state = EntityState.objects.create(
            entity = entity,
            entity_state_type_str = str( EntityStateType.BLOB ),
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
    def create_multivalued_sensor( cls,
                                   entity           : Entity,
                                   integration_id   : str      = None,
                                   name             : str      = None ):
        if not name:
            name = f'{entity.name} Values'
        entity_state = EntityState.objects.create(
            entity = entity,
            entity_state_type_str = str( EntityStateType.MULTVALUED ),
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
    def create_connectivity_sensor( cls,
                                    entity           : Entity,
                                    integration_id   : str      = None,
                                    name             : str      = None ):
        if not name:
            name = f'{entity.name} Connection'
        entity_state = EntityState.objects.create(
            entity = entity,
            entity_state_type_str = str( EntityStateType.CONNECTIVITY ),
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
    def create_datetime_sensor( cls,
                                entity           : Entity,
                                integration_id   : str      = None,
                                name             : str      = None ):
        if not name:
            name = f'{entity.name} Date/Time'
        entity_state = EntityState.objects.create(
            entity = entity,
            entity_state_type_str = str( EntityStateType.DATETIME ),
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
    def create_discrete_sensor( cls,
                                entity           : Entity,
                                values           : List[ str ],
                                integration_id   : str      = None,
                                name             : str      = None ):
        if not name:
            name = f'{entity.name} Value'
        entity_state = EntityState.objects.create(
            entity = entity,
            entity_state_type_str = str( EntityStateType.DICRETE ),
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
    def create_high_low_sensor( cls,
                                entity           : Entity,
                                integration_id   : str      = None,
                                name             : str      = None ):
        if not name:
            name = f'{entity.name} Level'
        entity_state = EntityState.objects.create(
            entity = entity,
            entity_state_type_str = str( EntityStateType.HIGH_LOW ),
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
    def create_temperature_sensor( cls,
                                   entity           : Entity,
                                   temperature_unit : TemperatureUnit,
                                   integration_id   : str      = None,
                                   name             : str      = None ):
        if not name:
            name = f'{entity.name} Temperature'
        entity_state = EntityState.objects.create(
            entity = entity,
            entity_state_type_str = str( EntityStateType.TEMPERATURE ),
            name = name,
            value_range = '',
            units = str(temperature_unit),
        )
        sensor = Sensor.objects.create(
            entity_state = entity_state,
            sensor_type_str = str( SensorType.DEFAULT ),
            name = name,
        )
        return sensor
    
    @classmethod
    def create_humidity_sensor( cls,
                                entity           : Entity,
                                humidity_unit    : HumidityUnit,
                                integration_id   : str      = None,
                                name             : str      = None ):
        if not name:
            name = f'{entity.name} Humidity'
        entity_state = EntityState.objects.create(
            entity = entity,
            entity_state_type_str = str( EntityStateType.HUMIDITY ),
            name = name,
            value_range = '',
            units = str(humidity_unit),
        )
        sensor = Sensor.objects.create(
            entity_state = entity_state,
            sensor_type_str = str( SensorType.DEFAULT ),
            name = name,
        )
        return sensor
    
    @classmethod
    def create_on_off_sensor( cls,
                              entity           : Entity,
                              integration_id   : str      = None,
                              name             : str      = None ):
        if not name:
            name = f'{entity.name} On/Off'
        entity_state = EntityState.objects.create(
            entity = entity,
            entity_state_type_str = str( EntityStateType.ON_OFF ),
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
    def create_open_close_sensor( cls,
                                  entity           : Entity,
                                  integration_id   : str      = None,
                                  name             : str      = None ):
        if not name:
            name = f'{entity.name} Open/Close'
        entity_state = EntityState.objects.create(
            entity = entity,
            entity_state_type_str = str( EntityStateType.OPEN_CLOSE ),
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
    def create_movement_sensor( cls,
                                entity          : Entity,
                                integration_id  : str      = None,
                                name            : str      = None ):
        if not name:
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
    def create_video_stream_sensor( cls,
                                    entity          : Entity,
                                    integration_id  : str      = None,
                                    name            : str      = None ):
        if not name:
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
    def create_on_off_controller( cls,
                                  entity          : Entity,
                                  integration_id  : str      = None,
                                  name            : str      = None,
                                  is_sensed       : bool     = True ):
        if not name:
            name = f'{entity.name} Controller'
        entity_state = EntityState.objects.create(
            entity = entity,
            entity_state_type_str = str( EntityStateType.ON_OFF ),
            name = name,
            value_range = '',
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

    @classmethod
    def create_discrete_controller( cls,
                                    entity          : Entity,
                                    value_list      : List[ str ],
                                    integration_id  : str          = None,
                                    name            : str          = None,
                                    is_sensed       : bool         = True ):
        if not name:
            name = f'{entity.name} Controller'
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
    
