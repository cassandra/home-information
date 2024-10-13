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

from hi.integrations.core.integration_key import IntegrationKey


class HiModelHelper:
    """ Model creation helpers. """
    
    @classmethod
    def create_blob_sensor( cls,
                            entity           : Entity,
                            integration_key  : IntegrationKey  = None,
                            name             : str             = None ):
        if not name:
            name = f'{entity.name} Blob'
        return cls.create_sensor(
            entity = entity,
            entity_state_type = EntityStateType.BLOB,
            name = name,
            integration_key = integration_key,
        )
    
    @classmethod
    def create_multivalued_sensor( cls,
                                   entity           : Entity,
                                   integration_key  : IntegrationKey  = None,
                                   name             : str             = None ):
        if not name:
            name = f'{entity.name} Values'
        return cls.create_sensor(
            entity = entity,
            entity_state_type = EntityStateType.MULTVALUED,
            name = name,
            integration_key = integration_key,
        )
    
    @classmethod
    def create_connectivity_sensor( cls,
                                    entity           : Entity,
                                    integration_key  : IntegrationKey  = None,
                                    name             : str             = None ):
        if not name:
            name = f'{entity.name} Connection'
        return cls.create_sensor(
            entity = entity,
            entity_state_type = EntityStateType.CONNECTIVITY,
            name = name,
            integration_key = integration_key,
        )
    
    @classmethod
    def create_datetime_sensor( cls,
                                entity           : Entity,
                                integration_key  : IntegrationKey  = None,
                                name             : str             = None ):
        if not name:
            name = f'{entity.name} Date/Time'
        return cls.create_sensor(
            entity = entity,
            entity_state_type = EntityStateType.DATETIME,
            name = name,
            integration_key = integration_key,
        )
    
    @classmethod
    def create_discrete_sensor( cls,
                                entity           : Entity,
                                values           : List[ str ],
                                integration_key  : IntegrationKey  = None,
                                name             : str             = None ):
        if not name:
            name = f'{entity.name} Value'
        return cls.create_sensor(
            entity = entity,
            entity_state_type = EntityStateType.DISCRETE,
            name = name,
            integration_key = integration_key,
            value_range = json.dumps( values ),
        )
    
    @classmethod
    def create_high_low_sensor( cls,
                                entity           : Entity,
                                integration_key  : IntegrationKey  = None,
                                name             : str             = None ):
        if not name:
            name = f'{entity.name} Level'
        return cls.create_sensor(
            entity = entity,
            entity_state_type = EntityStateType.HIGH_LOW,
            name = name,
            integration_key = integration_key,
        )
    
    @classmethod
    def create_temperature_sensor( cls,
                                   entity           : Entity,
                                   temperature_unit : TemperatureUnit,
                                   integration_key  : IntegrationKey  = None,
                                   name             : str             = None ):
        if not name:
            name = f'{entity.name} Temperature'
        return cls.create_sensor(
            entity = entity,
            entity_state_type = EntityStateType.TEMPERATURE,
            name = name,
            integration_key = integration_key,
            units = str(temperature_unit),
        )
    
    @classmethod
    def create_humidity_sensor( cls,
                                entity           : Entity,
                                humidity_unit    : HumidityUnit,
                                integration_key  : IntegrationKey  = None,
                                name             : str             = None ):
        if not name:
            name = f'{entity.name} Humidity'
        return cls.create_sensor(
            entity = entity,
            entity_state_type = EntityStateType.HUMIDITY,
            name = name,
            integration_key = integration_key,
            units = str(humidity_unit),
        )
    
    @classmethod
    def create_on_off_sensor( cls,
                              entity           : Entity,
                              integration_key  : IntegrationKey  = None,
                              name             : str             = None ):
        if not name:
            name = f'{entity.name} On/Off'
        return cls.create_sensor(
            entity = entity,
            entity_state_type = EntityStateType.ON_OFF,
            name = name,
            integration_key = integration_key,
        )
    
    @classmethod
    def create_open_close_sensor( cls,
                                  entity           : Entity,
                                  integration_key  : IntegrationKey  = None,
                                  name             : str             = None ):
        if not name:
            name = f'{entity.name} Open/Close'
        return cls.create_sensor(
            entity = entity,
            entity_state_type = EntityStateType.OPEN_CLOSE,
            name = name,
            integration_key = integration_key,
        )
    
    @classmethod
    def create_movement_sensor( cls,
                                entity           : Entity,
                                integration_key  : IntegrationKey  = None,
                                name             : str             = None ):
        if not name:
            name = f'{entity.name} Motion'
        return cls.create_sensor(
            entity = entity,
            entity_state_type = EntityStateType.MOVEMENT,
            name = name,
            integration_key = integration_key,
        )

    @classmethod
    def create_video_stream_sensor( cls,
                                    entity           : Entity,
                                    integration_key  : IntegrationKey  = None,
                                    name             : str             = None ):
        if not name:
            name = f'{entity.name} Stream'
        return cls.create_sensor(
            entity = entity,
            entity_state_type = EntityStateType.VIDEO_STREAM,
            name = name,
            integration_key = integration_key,
        )

    @classmethod
    def create_on_off_controller( cls,
                                  entity           : Entity,
                                  integration_key  : IntegrationKey  = None,
                                  name             : str            = None,
                                  is_sensed        : bool           = True ):
        if not name:
            name = f'{entity.name} Controller'
        return cls.create_controller(
            entity = entity,
            entity_state_type = EntityStateType.ON_OFF,
            name = name,
            is_sensed = is_sensed,
            integration_key = integration_key,
        )

    @classmethod
    def create_discrete_controller( cls,
                                    entity           : Entity,
                                    value_list       : List[ str ],
                                    integration_key  : IntegrationKey  = None,
                                    name             : str            = None,
                                    is_sensed        : bool           = True ):
        if not name:
            name = f'{entity.name} Controller'
        return cls.create_controller(
            entity = entity,
            entity_state_type = EntityStateType.DISCRETE,
            name = name,
            is_sensed = is_sensed,
            integration_key = integration_key,
            value_range = json.dumps( value_list ),
        )

    @classmethod
    def create_sensor( cls,
                       entity             : Entity,
                       entity_state_type  : EntityStateType,
                       name               : str               = None,
                       sensor_type        : SensorType        = SensorType.DEFAULT,
                       integration_key    : IntegrationKey    = None,
                       value_range        : str               = '',
                       units              : str               = None ):
        if not name:
            name = f'{entity.name}'

        entity_state = EntityState.objects.create(
            entity = entity,
            entity_state_type_str = str( entity_state_type ),
            name = name,
            value_range = value_range,
            units = units,
        )
        sensor = Sensor(
            entity_state = entity_state,
            sensor_type_str = str( sensor_type ),
            name = name,
        )
        sensor.integration_key = integration_key
        sensor.save()
        return sensor
    
    @classmethod
    def create_controller( cls,
                           entity             : Entity,
                           entity_state_type  : EntityStateType,
                           name               : str               = None,
                           controller_type    : ControllerType    = ControllerType.DEFAULT,
                           is_sensed          : bool              = True,
                           integration_key    : IntegrationKey    = None,
                           value_range        : str               = '',
                           units              : str               = None ):
        if not name:
            name = f'{entity.name}'
            
        entity_state = EntityState.objects.create(
            entity = entity,
            entity_state_type_str = str( entity_state_type ),
            name = name,
            value_range = value_range,
            units = units,
        )
        
        if is_sensed:
            sensor = Sensor(
                entity_state = entity_state,
                name = name,
                sensor_type_str = str( SensorType.DEFAULT ),
            )
            sensor.integration_key = integration_key
            sensor.save()
            
        controller = Controller(
            entity_state = entity_state,
            controller_type_str = str( controller_type ),
            name = name,
        )
        controller.integration_key = integration_key
        controller.save()
        return controller
    
