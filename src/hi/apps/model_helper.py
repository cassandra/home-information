import json
from typing import Dict

from hi.apps.alert.enums import AlarmLevel
from hi.apps.control.enums import ControllerType
from hi.apps.control.models import Controller
from hi.apps.entity.enums import (
    EntityStateRole,
    EntityStateType,
    EntityStateValue,
    HumidityUnit,
    TemperatureUnit,
)
from hi.apps.entity.models import Entity, EntityState
from hi.apps.event.enums import EventClauseOperator, EventType
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

    # Default alarm lifetime for persistent-state alarms (connectivity,
    # battery, smoke, CO, gas, etc.). After the AlertQueue
    # dedup-anchor refactor, this value governs the post-acknowledgement
    # nag window -- after the operator dismisses, the suppression lasts
    # this long before another bad-state alarm with the same signature
    # can re-surface. Twenty-four hours balances same-day deferral
    # against next-day reminder for the operator who didn't address the
    # underlying condition. Tracked in #378 -- the longer-term answer
    # is a producer-side ``clear_signature`` API that drops acked
    # alerts on state-recovery, after which this constant can give way
    # to per-source decisions.
    NAG_INTERVAL_SECS = 24 * 60 * 60

    DEFAULT_CONNECTIVITY_EVENT_WINDOW_SECS = 180
    DEFAULT_CONNECTIVITY_DEDUPE_WINDOW_SECS = 300
    DEFAULT_CONNECTIVITY_ALARM_LIFETIME_SECS = NAG_INTERVAL_SECS

    DEFAULT_OPEN_CLOSE_EVENT_WINDOW_SECS = 180
    DEFAULT_OPEN_CLOSE_DEDUPE_WINDOW_SECS = 300
    DEFAULT_OPEN_CLOSE_ALARM_LIFETIME_SECS = 600

    DEFAULT_MOVEMENT_EVENT_WINDOW_SECS = 180
    DEFAULT_MOVEMENT_DEDUPE_WINDOW_SECS = 300
    DEFAULT_MOVEMENT_ALARM_LIFETIME_SECS = 600

    DEFAULT_PRESENCE_EVENT_WINDOW_SECS = 180
    DEFAULT_PRESENCE_DEDUPE_WINDOW_SECS = 300
    DEFAULT_PRESENCE_ALARM_LIFETIME_SECS = 600

    DEFAULT_BATTERY_EVENT_WINDOW_SECS = 180
    DEFAULT_BATTERY_DEDUPE_WINDOW_SECS = 300
    DEFAULT_BATTERY_ALARM_LIFETIME_SECS = NAG_INTERVAL_SECS

    # Threshold-based low-battery alarm for continuous BATTERY_LEVEL
    # percentage sensors. Distinct from the discrete HIGH_LOW battery
    # alarm above — the threshold uses EventClauseOperator.LT against
    # a percentage. Dedupe window is one day so a battery flapping
    # near the threshold doesn't spam.
    DEFAULT_BATTERY_LEVEL_THRESHOLD_PERCENT = 20
    DEFAULT_BATTERY_LEVEL_EVENT_WINDOW_SECS = 180
    DEFAULT_BATTERY_LEVEL_DEDUPE_WINDOW_SECS = 86400
    DEFAULT_BATTERY_LEVEL_ALARM_LIFETIME_SECS = NAG_INTERVAL_SECS

    DEFAULT_SMOKE_EVENT_WINDOW_SECS = 180
    DEFAULT_SMOKE_DEDUPE_WINDOW_SECS = 300
    DEFAULT_SMOKE_ALARM_LIFETIME_SECS = NAG_INTERVAL_SECS

    DEFAULT_MOISTURE_EVENT_WINDOW_SECS = 180
    DEFAULT_MOISTURE_DEDUPE_WINDOW_SECS = 300
    DEFAULT_MOISTURE_ALARM_LIFETIME_SECS = NAG_INTERVAL_SECS

    DEFAULT_CO_EVENT_WINDOW_SECS = 180
    DEFAULT_CO_DEDUPE_WINDOW_SECS = 300
    DEFAULT_CO_ALARM_LIFETIME_SECS = NAG_INTERVAL_SECS

    DEFAULT_GAS_EVENT_WINDOW_SECS = 180
    DEFAULT_GAS_DEDUPE_WINDOW_SECS = 300
    DEFAULT_GAS_ALARM_LIFETIME_SECS = NAG_INTERVAL_SECS
    
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
                                    name             : str             = None,
                                    add_default_alarm : bool           = False ) -> Sensor:
        if not name:
            name = f'{entity.name} Connection'
        sensor = cls.create_sensor(
            entity = entity,
            entity_state_type = EntityStateType.CONNECTIVITY,
            name = name,
            integration_key = integration_key,
        )
        if add_default_alarm:
            cls.create_connectivity_event_definition(
                name = f'{sensor.name} Alarm',
                entity_state = sensor.entity_state,
                integration_key = integration_key,
            )
        return sensor
    
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
                                  name             : str             = None,
                                  add_default_alarm : bool           = False ) -> Sensor:
        if not name:
            name = f'{entity.name} Open/Close'
        sensor = cls.create_sensor(
            entity = entity,
            entity_state_type = EntityStateType.OPEN_CLOSE,
            name = name,
            integration_key = integration_key,
        )
        if add_default_alarm:
            cls.create_open_close_event_definition(
                name = f'{sensor.name} Alarm',
                entity_state = sensor.entity_state,
                integration_key = integration_key,
            )
        return sensor
    
    @classmethod
    def create_movement_sensor( cls,
                                entity              : Entity,
                                integration_key     : IntegrationKey  = None,
                                name                : str             = None,
                                provides_event_video_clip : bool          = False,
                                add_default_alarm   : bool            = False ) -> Sensor:
        if not name:
            name = f'{entity.name} Motion'
        sensor = cls.create_sensor(
            entity = entity,
            entity_state_type = EntityStateType.MOVEMENT,
            name = name,
            integration_key = integration_key,
            provides_event_video_clip = provides_event_video_clip,
        )
        if add_default_alarm:
            cls.create_movement_event_definition(
                name = f'{sensor.name} Alarm',
                entity_state = sensor.entity_state,
                integration_key = integration_key,
            )
        return sensor

    @classmethod
    def create_object_presence_sensor( cls,
                                       entity                        : Entity,
                                       integration_key               : IntegrationKey  = None,
                                       name                          : str             = None,
                                       provides_event_video_clip     : bool            = False,
                                       provides_event_video_snapshot : bool            = False ) -> Sensor:
        """OBJECT_PRESENCE sensor — typed discrete state whose value
        space is the canonical object-class bucket set
        (NONE / PERSON / CAR / ANIMAL / PACKAGE / OTHER). The
        integration's converter is responsible for mapping raw
        upstream labels onto the canonical set; the resting value
        is OBJECT_NONE."""
        if not name:
            name = f'{entity.name} Object'
        return cls.create_sensor(
            entity = entity,
            entity_state_type = EntityStateType.OBJECT_PRESENCE,
            name = name,
            integration_key = integration_key,
            provides_event_video_clip = provides_event_video_clip,
            provides_event_video_snapshot = provides_event_video_snapshot,
        )

    @classmethod
    def create_presence_sensor( cls,
                                entity              : Entity,
                                integration_key     : IntegrationKey  = None,
                                name                : str             = None,
                                add_default_alarm   : bool            = False ) -> Sensor:
        if not name:
            name = f'{entity.name} Presence'
        sensor = cls.create_sensor(
            entity = entity,
            entity_state_type = EntityStateType.PRESENCE,
            name = name,
            integration_key = integration_key,
        )
        if add_default_alarm:
            cls.create_presence_event_definition(
                name = f'{sensor.name} Alarm',
                entity_state = sensor.entity_state,
                integration_key = integration_key,
            )
        return sensor

    @classmethod
    def create_smoke_sensor( cls,
                             entity              : Entity,
                             integration_key     : IntegrationKey  = None,
                             name                : str             = None,
                             add_default_alarm   : bool            = False ) -> Sensor:
        if not name:
            name = f'{entity.name} Smoke'
        sensor = cls.create_sensor(
            entity = entity,
            entity_state_type = EntityStateType.SMOKE,
            name = name,
            integration_key = integration_key,
        )
        if add_default_alarm:
            cls.create_smoke_event_definition(
                name = f'{sensor.name} Alarm',
                entity_state = sensor.entity_state,
                integration_key = integration_key,
            )
        return sensor

    @classmethod
    def create_moisture_sensor( cls,
                                entity              : Entity,
                                integration_key     : IntegrationKey  = None,
                                name                : str             = None,
                                add_default_alarm   : bool            = False ) -> Sensor:
        if not name:
            name = f'{entity.name} Moisture'
        sensor = cls.create_sensor(
            entity = entity,
            entity_state_type = EntityStateType.MOISTURE,
            name = name,
            integration_key = integration_key,
        )
        if add_default_alarm:
            cls.create_moisture_event_definition(
                name = f'{sensor.name} Alarm',
                entity_state = sensor.entity_state,
                integration_key = integration_key,
            )
        return sensor

    @classmethod
    def create_co_sensor( cls,
                          entity              : Entity,
                          integration_key     : IntegrationKey  = None,
                          name                : str             = None,
                          add_default_alarm   : bool            = False ) -> Sensor:
        if not name:
            name = f'{entity.name} Carbon Monoxide'
        sensor = cls.create_sensor(
            entity = entity,
            entity_state_type = EntityStateType.CO,
            name = name,
            integration_key = integration_key,
        )
        if add_default_alarm:
            cls.create_co_event_definition(
                name = f'{sensor.name} Alarm',
                entity_state = sensor.entity_state,
                integration_key = integration_key,
            )
        return sensor

    @classmethod
    def create_gas_sensor( cls,
                           entity              : Entity,
                           integration_key     : IntegrationKey  = None,
                           name                : str             = None,
                           add_default_alarm   : bool            = False ) -> Sensor:
        if not name:
            name = f'{entity.name} Gas'
        sensor = cls.create_sensor(
            entity = entity,
            entity_state_type = EntityStateType.GAS,
            name = name,
            integration_key = integration_key,
        )
        if add_default_alarm:
            cls.create_gas_event_definition(
                name = f'{sensor.name} Alarm',
                entity_state = sensor.entity_state,
                integration_key = integration_key,
            )
        return sensor

    @classmethod
    def create_battery_level_sensor( cls,
                                     entity              : Entity,
                                     integration_key     : IntegrationKey  = None,
                                     name                : str             = None,
                                     units               : str             = '%',
                                     add_default_alarm   : bool            = False ) -> Sensor:
        """Continuous battery-percentage sensor. Mirrors the alarm-bearing
        sensor factories (smoke / moisture / CO / gas): when
        ``add_default_alarm`` is True, also wires the canonical
        low-battery threshold alarm via
        ``create_battery_level_event_definition``."""
        if not name:
            name = f'{entity.name} Battery'
        sensor = cls.create_sensor(
            entity = entity,
            entity_state_type = EntityStateType.BATTERY_LEVEL,
            name = name,
            integration_key = integration_key,
            units = units,
        )
        if add_default_alarm:
            cls.create_battery_level_event_definition(
                name = f'{sensor.name} Alarm',
                entity_state = sensor.entity_state,
                integration_key = integration_key,
            )
        return sensor

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
    def create_open_close_controller( cls,
                                      entity           : Entity,
                                      integration_key  : IntegrationKey  = None,
                                      name             : str             = None,
                                      is_sensed        : bool            = True ) -> Controller:
        if not name:
            name = f'{entity.name} Controller'
        return cls.create_controller(
            entity = entity,
            entity_state_type = EntityStateType.OPEN_CLOSE,
            name = name,
            is_sensed = is_sensed,
            integration_key = integration_key,
        )

    @classmethod
    def create_open_close_position_controller(
            cls,
            entity           : Entity,
            integration_key  : IntegrationKey  = None,
            name             : str             = None,
            is_sensed        : bool            = True ) -> Controller:
        if not name:
            name = f'{entity.name} Position'
        # Continuous position 0-100 (closed at 0, open above).
        value_range = { 'min': 0, 'max': 100 }
        return cls.create_controller(
            entity = entity,
            entity_state_type = EntityStateType.OPEN_CLOSE_POSITION,
            name = name,
            is_sensed = is_sensed,
            integration_key = integration_key,
            value_range_str = json.dumps( value_range ),
        )

    @classmethod
    def create_power_level_controller(
            cls,
            entity           : Entity,
            integration_key  : IntegrationKey  = None,
            name             : str             = None,
            is_sensed        : bool            = True ) -> Controller:
        if not name:
            name = f'{entity.name} Level'
        # Generic continuous power/intensity/speed 0-100. Per-context
        # label (e.g., "Speed" for fans) is set by the caller via name.
        value_range = { 'min': 0, 'max': 100 }
        return cls.create_controller(
            entity = entity,
            entity_state_type = EntityStateType.POWER_LEVEL,
            name = name,
            is_sensed = is_sensed,
            integration_key = integration_key,
            value_range_str = json.dumps( value_range ),
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
                       entity                        : Entity,
                       entity_state_type             : EntityStateType,
                       name                          : str               = None,
                       sensor_type                   : SensorType        = SensorType.DEFAULT,
                       integration_key               : IntegrationKey    = None,
                       value_range_str               : str               = '',
                       units                         : str               = None,
                       entity_state_role             : EntityStateRole   = None,
                       provides_event_video_clip     : bool              = False,
                       provides_event_video_snapshot : bool              = False ) -> Sensor:
        if not name:
            name = f'{entity.name}'

        entity_state_kwargs = dict(
            entity = entity,
            entity_state_type_str = str( entity_state_type ),
            name = name,
            value_range_str = value_range_str,
            units = units,
        )
        if entity_state_role is not None:
            entity_state_kwargs['role_str'] = str( entity_state_role )
        entity_state = EntityState.objects.create( **entity_state_kwargs )
        sensor = Sensor(
            entity_state = entity_state,
            name = name,
            sensor_type_str = str( sensor_type ),
            persist_history = bool( entity_state_type not in cls.EXCLUDE_FROM_SENSOR_HISTORY ),
            provides_event_video_clip = provides_event_video_clip,
            provides_event_video_snapshot = provides_event_video_snapshot,
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
                           units              : str               = None,
                           entity_state_role  : EntityStateRole   = None ) -> Controller:
        if not name:
            name = f'{entity.name}'

        entity_state_kwargs = dict(
            entity = entity,
            entity_state_type_str = str( entity_state_type ),
            name = name,
            value_range_str = value_range_str,
            units = units,
        )
        if entity_state_role is not None:
            entity_state_kwargs['role_str'] = str( entity_state_role )
        entity_state = EntityState.objects.create( **entity_state_kwargs )

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
    def create_object_presence_event_definition(
            cls,
            name                 : str,
            entity_state         : EntityState,
            integration_key      : IntegrationKey  = None ) -> EventDefinition:
        # Conservative default: alarm on PERSON only. The
        # EventClauseOperator vocabulary doesn't yet support NEQ/IN
        # (see Issue #346), so "any detection" can't be expressed as
        # a single clause. Operators wanting broader rules (car,
        # package, etc.) can add EventDefinitions in the UI.
        return EventManager().create_simple_alarm_event_definition(
            name = name,
            event_type = EventType.SECURITY,
            entity_state = entity_state,
            value = EntityStateValue.OBJECT_PERSON,
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
    def create_presence_event_definition(
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
            event_window_secs = cls.DEFAULT_PRESENCE_EVENT_WINDOW_SECS,
            dedupe_window_secs = cls.DEFAULT_PRESENCE_DEDUPE_WINDOW_SECS,
            alarm_lifetime_secs = cls.DEFAULT_PRESENCE_ALARM_LIFETIME_SECS,
            integration_key = integration_key,
        )

    @classmethod
    def create_smoke_event_definition(
            cls,
            name                 : str,
            entity_state         : EntityState,
            integration_key      : IntegrationKey  = None ) -> EventDefinition:

        # Smoke is life-safety: both security levels map to CRITICAL.
        # The user's "I'm home, keep things quiet" posture (LOW) does
        # not reduce the urgency of a fire alarm.
        return EventManager().create_simple_alarm_event_definition(
            name = name,
            event_type = EventType.SECURITY,
            entity_state = entity_state,
            value = EntityStateValue.SMOKE_DETECTED,
            security_to_alarm_level = {
                SecurityLevel.HIGH: AlarmLevel.CRITICAL,
                SecurityLevel.LOW: AlarmLevel.CRITICAL,
            },
            event_window_secs = cls.DEFAULT_SMOKE_EVENT_WINDOW_SECS,
            dedupe_window_secs = cls.DEFAULT_SMOKE_DEDUPE_WINDOW_SECS,
            alarm_lifetime_secs = cls.DEFAULT_SMOKE_ALARM_LIFETIME_SECS,
            integration_key = integration_key,
        )

    @classmethod
    def create_moisture_event_definition(
            cls,
            name                 : str,
            entity_state         : EntityState,
            integration_key      : IntegrationKey  = None ) -> EventDefinition:

        # Water leaks are property-damage events: both security
        # levels map to CRITICAL so the operator sees the alarm
        # regardless of HOME / AWAY posture.
        return EventManager().create_simple_alarm_event_definition(
            name = name,
            event_type = EventType.SECURITY,
            entity_state = entity_state,
            value = EntityStateValue.MOISTURE_DETECTED,
            security_to_alarm_level = {
                SecurityLevel.HIGH: AlarmLevel.CRITICAL,
                SecurityLevel.LOW: AlarmLevel.CRITICAL,
            },
            event_window_secs = cls.DEFAULT_MOISTURE_EVENT_WINDOW_SECS,
            dedupe_window_secs = cls.DEFAULT_MOISTURE_DEDUPE_WINDOW_SECS,
            alarm_lifetime_secs = cls.DEFAULT_MOISTURE_ALARM_LIFETIME_SECS,
            integration_key = integration_key,
        )

    @classmethod
    def create_co_event_definition(
            cls,
            name                 : str,
            entity_state         : EntityState,
            integration_key      : IntegrationKey  = None ) -> EventDefinition:

        # Carbon monoxide is life-safety: both security levels map to
        # CRITICAL. CO is odorless and lethal at low concentrations;
        # the HOME / AWAY posture does not reduce urgency.
        return EventManager().create_simple_alarm_event_definition(
            name = name,
            event_type = EventType.SECURITY,
            entity_state = entity_state,
            value = EntityStateValue.CO_DETECTED,
            security_to_alarm_level = {
                SecurityLevel.HIGH: AlarmLevel.CRITICAL,
                SecurityLevel.LOW: AlarmLevel.CRITICAL,
            },
            event_window_secs = cls.DEFAULT_CO_EVENT_WINDOW_SECS,
            dedupe_window_secs = cls.DEFAULT_CO_DEDUPE_WINDOW_SECS,
            alarm_lifetime_secs = cls.DEFAULT_CO_ALARM_LIFETIME_SECS,
            integration_key = integration_key,
        )

    @classmethod
    def create_gas_event_definition(
            cls,
            name                 : str,
            entity_state         : EntityState,
            integration_key      : IntegrationKey  = None ) -> EventDefinition:

        # Combustible-gas leaks (natural gas, propane, methane) are
        # life-safety: both security levels map to CRITICAL.
        return EventManager().create_simple_alarm_event_definition(
            name = name,
            event_type = EventType.SECURITY,
            entity_state = entity_state,
            value = EntityStateValue.GAS_DETECTED,
            security_to_alarm_level = {
                SecurityLevel.HIGH: AlarmLevel.CRITICAL,
                SecurityLevel.LOW: AlarmLevel.CRITICAL,
            },
            event_window_secs = cls.DEFAULT_GAS_EVENT_WINDOW_SECS,
            dedupe_window_secs = cls.DEFAULT_GAS_DEDUPE_WINDOW_SECS,
            alarm_lifetime_secs = cls.DEFAULT_GAS_ALARM_LIFETIME_SECS,
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

    @classmethod
    def create_battery_level_event_definition(
            cls,
            name                 : str,
            entity_state         : EntityState,
            integration_key      : IntegrationKey  = None,
            threshold_percent    : int             = None,
    ) -> EventDefinition:
        """Threshold low-battery alarm against a continuous
        BATTERY_LEVEL percentage sensor. Triggers when the reported
        percent drops below ``threshold_percent`` (default 20).
        Distinct from ``create_battery_event_definition`` above, which
        triggers on the discrete HIGH_LOW battery state."""
        if threshold_percent is None:
            threshold_percent = cls.DEFAULT_BATTERY_LEVEL_THRESHOLD_PERCENT
        return EventManager().create_simple_alarm_event_definition(
            name = name,
            event_type = EventType.MAINTENANCE,
            entity_state = entity_state,
            value = str( threshold_percent ),
            value_operator = EventClauseOperator.LT,
            security_to_alarm_level = {
                SecurityLevel.HIGH: AlarmLevel.INFO,
                SecurityLevel.LOW: AlarmLevel.INFO,
            },
            event_window_secs = cls.DEFAULT_BATTERY_LEVEL_EVENT_WINDOW_SECS,
            dedupe_window_secs = cls.DEFAULT_BATTERY_LEVEL_DEDUPE_WINDOW_SECS,
            alarm_lifetime_secs = cls.DEFAULT_BATTERY_LEVEL_ALARM_LIFETIME_SECS,
            integration_key = integration_key,
        )
