import json
from typing import Dict

from hi.apps.alert.enums import AlarmLevel
from hi.apps.control.enums import ControllerType
from hi.apps.control.models import Controller
from hi.apps.entity.enums import (
    EntityStateType,
    EntityStateValue,
    HumidityUnit,
    TemperatureUnit,
)    
from hi.apps.entity.models import Entity, EntityState
from hi.apps.event.enums import EventType
from hi.apps.event.event_manager import EventManager
from hi.apps.event.models import EventDefinition
from hi.apps.security.enums import SecurityLevel
from hi.apps.sense.enums import SensorType
from hi.apps.sense.models import Sensor

from hi.integrations.transient_models import IntegrationKey


class HiModelHelper:
    """ Model creation helpers. """

    EXCLUDE_FROM_SENSOR_HISTORY = {
        EntityStateType.DATETIME,
        EntityStateType.BLOB,
        EntityStateType.MULTIVALUED,
    }

    DEFAULT_CONNECTIVITY_EVENT_WINDOW_SECS = 180
    DEFAULT_CONNECTIVITY_DEDUPE_WINDOW_SECS = 300
    DEFAULT_CONNECTIVITY_ALARM_LIFETIME_SECS = 0
    
    DEFAULT_OPEN_CLOSE_EVENT_WINDOW_SECS = 180
    DEFAULT_OPEN_CLOSE_DEDUPE_WINDOW_SECS = 300
    DEFAULT_OPEN_CLOSE_ALARM_LIFETIME_SECS = 600

    DEFAULT_MOVEMENT_EVENT_WINDOW_SECS = 180
    DEFAULT_MOVEMENT_DEDUPE_WINDOW_SECS = 300
    DEFAULT_MOVEMENT_ALARM_LIFETIME_SECS = 600

    DEFAULT_BATTERY_EVENT_WINDOW_SECS = 180
    DEFAULT_BATTERY_DEDUPE_WINDOW_SECS = 300
    DEFAULT_BATTERY_ALARM_LIFETIME_SECS = 0
    
    @classmethod
    def create_blob_sensor( cls,
                            entity           : Entity,
                            integration_key  : IntegrationKey  = None,
                            name             : str             = None ) -> Sensor:
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
                                   name             : str             = None ) -> Sensor:
        if not name:
            name = f'{entity.name} Values'
        return cls.create_sensor(
            entity = entity,
            entity_state_type = EntityStateType.MULTIVALUED,
            name = name,
            integration_key = integration_key,
        )
    
    @classmethod
    def create_connectivity_sensor( cls,
                                    entity           : Entity,
                                    integration_key  : IntegrationKey  = None,
                                    name             : str             = None ) -> Sensor:
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
                                name             : str             = None ) -> Sensor:
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
                                name_label_dict  : Dict[ str, str ],
                                integration_key  : IntegrationKey  = None,
                                name             : str             = None ) -> Sensor:
        if not name:
            name = f'{entity.name} Value'
        return cls.create_sensor(
            entity = entity,
            entity_state_type = EntityStateType.DISCRETE,
            name = name,
            integration_key = integration_key,
            value_range_str = json.dumps( name_label_dict ),
        )
    
    @classmethod
    def create_high_low_sensor( cls,
                                entity           : Entity,
                                integration_key  : IntegrationKey  = None,
                                name             : str             = None ) -> Sensor:
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
                                   name             : str             = None ) -> Sensor:
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
                                name             : str             = None ) -> Sensor:
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
                              name             : str             = None ) -> Sensor:
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
                                  name             : str             = None ) -> Sensor:
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
                                entity              : Entity,
                                integration_key     : IntegrationKey  = None,
                                name                : str             = None,
                                provides_video_stream : bool          = False ) -> Sensor:
        if not name:
            name = f'{entity.name} Motion'
        return cls.create_sensor(
            entity = entity,
            entity_state_type = EntityStateType.MOVEMENT,
            name = name,
            integration_key = integration_key,
            provides_video_stream = provides_video_stream,
        )

    @classmethod
    def create_on_off_controller( cls,
                                  entity           : Entity,
                                  integration_key  : IntegrationKey  = None,
                                  name             : str             = None,
                                  is_sensed        : bool            = True ) -> Controller:
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
    def add_on_off_controller( cls,
                               entity           : Entity,
                               entity_state     : EntityState,
                               integration_key  : IntegrationKey  = None,
                               name             : str             = None,
                               is_sensed        : bool            = True  ) -> Controller:
        if not name:
            name = f'{entity.name} Controller'
        return cls.add_controller(
            entity = entity,
            entity_state = entity_state,
            name = name,
            is_sensed = is_sensed,
            integration_key = integration_key,
        )

    @classmethod
    def create_discrete_controller( cls,
                                    entity           : Entity,
                                    name_label_dict  : Dict[ str, str ],
                                    integration_key  : IntegrationKey  = None,
                                    name             : str             = None,
                                    is_sensed        : bool            = True ) -> Controller:
        if not name:
            name = f'{entity.name} Controller'
        return cls.create_controller(
            entity = entity,
            entity_state_type = EntityStateType.DISCRETE,
            name = name,
            is_sensed = is_sensed,
            integration_key = integration_key,
            value_range_str = json.dumps( name_label_dict ),
        )

    @classmethod
    def create_light_dimmer_controller( cls,
                                        entity           : Entity,
                                        integration_key  : IntegrationKey  = None,
                                        name             : str             = None,
                                        is_sensed        : bool            = True ) -> Controller:
        if not name:
            name = f'{entity.name} Dimmer'
        # Light dimmer range: 0-100 (percentage)
        value_range = {'min': 0, 'max': 100}
        return cls.create_controller(
            entity = entity,
            entity_state_type = EntityStateType.LIGHT_DIMMER,
            name = name,
            is_sensed = is_sensed,
            integration_key = integration_key,
            value_range_str = json.dumps( value_range ),
        )

    @classmethod
    def create_sensor( cls,
                       entity             : Entity,
                       entity_state_type  : EntityStateType,
                       name               : str               = None,
                       sensor_type        : SensorType        = SensorType.DEFAULT,
                       integration_key    : IntegrationKey    = None,
                       value_range_str    : str               = '',
                       units              : str               = None,
                       provides_video_stream : bool           = False ) -> Sensor:
        if not name:
            name = f'{entity.name}'

        entity_state = EntityState.objects.create(
            entity = entity,
            entity_state_type_str = str( entity_state_type ),
            name = name,
            value_range_str = value_range_str,
            units = units,
        )
        sensor = Sensor(
            entity_state = entity_state,
            name = name,
            sensor_type_str = str( sensor_type ),
            persist_history = bool( entity_state_type not in cls.EXCLUDE_FROM_SENSOR_HISTORY ),
            provides_video_stream = provides_video_stream,
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
                           value_range_str    : str               = '',
                           units              : str               = None ) -> Controller:
        if not name:
            name = f'{entity.name}'
            
        entity_state = EntityState.objects.create(
            entity = entity,
            entity_state_type_str = str( entity_state_type ),
            name = name,
            value_range_str = value_range_str,
            units = units,
        )

        return cls.add_controller(
            entity = entity,
            entity_state = entity_state,
            name = name,
            is_sensed = is_sensed,
            integration_key = integration_key,
        )
    
    @classmethod
    def add_controller( cls,
                        entity             : Entity,
                        entity_state       : EntityState,
                        name               : str               = None,
                        controller_type    : ControllerType    = ControllerType.DEFAULT,
                        is_sensed          : bool              = True,
                        integration_key    : IntegrationKey    = None ) -> Controller:
        if not name:
            name = f'{entity.name}'
            
        if is_sensed:
            sensor = Sensor(
                entity_state = entity_state,
                name = name,
                sensor_type_str = str( SensorType.DEFAULT ),
                persist_history = bool( entity_state.entity_state_type
                                        not in cls.EXCLUDE_FROM_SENSOR_HISTORY ),
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

    @classmethod
    def create_connectivity_event_definition(
            cls,
            name                 : str,
            entity_state         : EntityState,
            integration_key      : IntegrationKey  = None ) -> EventDefinition:
        
        return EventManager().create_simple_alarm_event_definition(
            name = name,
            event_type = EventType.INFORMATION,
            entity_state = entity_state,
            value = EntityStateValue.DISCONNECTED,
            security_to_alarm_level = {
                SecurityLevel.HIGH: AlarmLevel.WARNING,
                SecurityLevel.LOW: AlarmLevel.WARNING,
            },
            event_window_secs = cls.DEFAULT_CONNECTIVITY_EVENT_WINDOW_SECS,
            dedupe_window_secs = cls.DEFAULT_CONNECTIVITY_DEDUPE_WINDOW_SECS,
            alarm_lifetime_secs = cls.DEFAULT_CONNECTIVITY_ALARM_LIFETIME_SECS,
            integration_key = integration_key,
        )      

    @classmethod
    def create_open_close_event_definition(
            cls,
            name                 : str,
            entity_state         : EntityState,
            integration_key      : IntegrationKey  = None ) -> EventDefinition:
        
        return EventManager().create_simple_alarm_event_definition(
            name = name,
            event_type = EventType.SECURITY,
            entity_state = entity_state,
            value = EntityStateValue.OPEN,
            security_to_alarm_level = {
                SecurityLevel.HIGH: AlarmLevel.CRITICAL,
                SecurityLevel.LOW: AlarmLevel.INFO,
            },
            event_window_secs = cls.DEFAULT_OPEN_CLOSE_EVENT_WINDOW_SECS,
            dedupe_window_secs = cls.DEFAULT_OPEN_CLOSE_DEDUPE_WINDOW_SECS,
            alarm_lifetime_secs = cls.DEFAULT_OPEN_CLOSE_ALARM_LIFETIME_SECS,
            integration_key = integration_key,
        )

    @classmethod
    def create_movement_event_definition(
            cls,
            name                 : str,
            entity_state         : EntityState,
            integration_key      : IntegrationKey  = None ) -> EventDefinition:
        
        return EventManager().create_simple_alarm_event_definition(
            name = name,
            event_type = EventType.SECURITY,
            entity_state = entity_state,
            value = EntityStateValue.ACTIVE,
            security_to_alarm_level = {
                SecurityLevel.HIGH: AlarmLevel.CRITICAL,
                SecurityLevel.LOW: AlarmLevel.INFO,
            },
            event_window_secs = cls.DEFAULT_MOVEMENT_EVENT_WINDOW_SECS,
            dedupe_window_secs = cls.DEFAULT_MOVEMENT_DEDUPE_WINDOW_SECS,
            alarm_lifetime_secs = cls.DEFAULT_MOVEMENT_ALARM_LIFETIME_SECS,
            integration_key = integration_key,
        )

    @classmethod
    def create_battery_event_definition(
            cls,
            name                 : str,
            entity_state         : EntityState,
            integration_key      : IntegrationKey  = None ) -> EventDefinition:
        
        return EventManager().create_simple_alarm_event_definition(
            name = name,
            event_type = EventType.MAINTENANCE,
            entity_state = entity_state,
            value = EntityStateValue.LOW,
            security_to_alarm_level = {
                SecurityLevel.HIGH: AlarmLevel.INFO,
                SecurityLevel.LOW: AlarmLevel.INFO,
            },
            event_window_secs = cls.DEFAULT_BATTERY_EVENT_WINDOW_SECS,
            dedupe_window_secs = cls.DEFAULT_BATTERY_DEDUPE_WINDOW_SECS,
            alarm_lifetime_secs = cls.DEFAULT_BATTERY_ALARM_LIFETIME_SECS,
            integration_key = integration_key,
        )
