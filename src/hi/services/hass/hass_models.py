from dataclasses import dataclass
from typing import Dict, Optional


class HassApi:
    """ Central place for translating  HAss API response strings and internal variables. """
    
    ATTRIBUTES_FIELD = 'attributes'
    ENTITY_ID_FIELD = 'entity_id'
    STATE_FIELD = 'state'
        
    # Home Assistant Domain Constants
    AUTOMATION_DOMAIN = 'automation'
    BINARY_SENSOR_DOMAIN = 'binary_sensor'
    CALENDAR_DOMAIN = 'calendar'
    CAMERA_DOMAIN = 'camera'
    CLIMATE_DOMAIN = 'climate'
    CONVERSATION_DOMAIN = 'conversation'
    COVER_DOMAIN = 'cover'
    FAN_DOMAIN = 'fan'
    LIGHT_DOMAIN = 'light'
    LOCK_DOMAIN = 'lock'
    MEDIA_PLAYER_DOMAIN = 'media_player'
    PERSON_DOMAIN = 'person'
    SCRIPT_DOMAIN = 'script'
    SENSOR_DOMAIN = 'sensor'
    SUN_DOMAIN = 'sun'
    SWITCH_DOMAIN = 'switch'
    TODO_DOMAIN = 'todo'
    TTS_DOMAIN = 'tts'
    WEATHER_DOMAIN = 'weather'
    ZONE_DOMAIN = 'zone'
    
    # Home Assistant Service Name Constants
    TURN_ON_SERVICE = 'turn_on'
    TURN_OFF_SERVICE = 'turn_off'
    OPEN_COVER_SERVICE = 'open_cover'
    CLOSE_COVER_SERVICE = 'close_cover'
    SET_COVER_POSITION_SERVICE = 'set_cover_position'
    SET_TEMPERATURE_SERVICE = 'set_temperature'
    SET_HVAC_MODE_SERVICE = 'set_hvac_mode'
    LOCK_SERVICE = 'lock'
    UNLOCK_SERVICE = 'unlock'
    MEDIA_PLAY_SERVICE = 'media_play'
    MEDIA_PAUSE_SERVICE = 'media_pause'
    MEDIA_STOP_SERVICE = 'media_stop'
    VOLUME_SET_SERVICE = 'volume_set'
    SET_PERCENTAGE_SERVICE = 'set_percentage'
    OSCILLATE_SERVICE = 'oscillate'
    SET_DIRECTION_SERVICE = 'set_direction'
    SET_PRESET_MODE_SERVICE = 'set_preset_mode'
    SET_FAN_MODE_SERVICE = 'set_fan_mode'
    ENABLE_MOTION_DETECTION_SERVICE = 'enable_motion_detection'
    DISABLE_MOTION_DETECTION_SERVICE = 'disable_motion_detection'
    
    # Legacy aliases for backward compatibility (remove after migration)
    AUTOMATION_ID_PREFIX = AUTOMATION_DOMAIN
    BINARY_SENSOR_ID_PREFIX = BINARY_SENSOR_DOMAIN
    CALENDAR_ID_PREFIX = CALENDAR_DOMAIN
    CAMERA_ID_PREFIX = CAMERA_DOMAIN
    CLIMATE_ID_PREFIX = CLIMATE_DOMAIN
    CONVERSATION_ID_PREFIX = CONVERSATION_DOMAIN
    LIGHT_ID_PREFIX = LIGHT_DOMAIN
    PERSON_ID_PREFIX = PERSON_DOMAIN
    SCRIPT_ID_PREFIX = SCRIPT_DOMAIN
    SENSOR_ID_PREFIX = SENSOR_DOMAIN
    SUN_ID_PREFIX = SUN_DOMAIN
    SWITCH_ID_PREFIX = SWITCH_DOMAIN
    TODO_ID_PREFIX = TODO_DOMAIN
    TTS_ID_PREFIX = TTS_DOMAIN
    WEATHER_ID_PREFIX = WEATHER_DOMAIN
    ZONE_ID_PREFIX = ZONE_DOMAIN

    BATTERY_ID_SUFFIX = '_battery'
    EVENTS_last_HOUR_ID_SUFFIX = '_events_last_hour'
    HUMIDITY_ID_SUFFIX = '_humidity'
    ILLUMINANCE_ID_SUFFIX = '_illuminance'
    LIGHT_ID_SUFFIX = '_light'
    MOISTURE_ID_SUFFIX = '_moisture'
    MOTION_ID_SUFFIX = '_motion'
    OCCUPANCY_ID_SUFFIX = '_occupancy'
    PRESSURE_ID_SUFFIX = '_pressure'
    STATE_ID_SUFFIX = '_state'
    STATUS_ID_SUFFIX = '_status'
    TEMPERATURE_ID_SUFFIX = '_temperature'
    WIND_SPEED_ID_SUFFIX = '_wind_speed'
    # Sun
    NEXT_DAWN_ID_SUFFIX = '_next_dawn'
    NEXT_DUSK_ID_SUFFIX = '_next_dusk'
    NEXT_MIDNIGHT_ID_SUFFIX = '_next_midnight'
    NEXT_NOON_ID_SUFFIX = '_next_noon'
    NEXT_RISING_ID_SUFFIX = '_next_rising'
    NEXT_SETTING_ID_SUFFIX = '_next_setting'
    # Printer (IPP integration cartridge sensors)
    BLACK_CARTRIDGE_ID_SUFFIX = '_black_cartridge'
    CYAN_CARTRIDGE_ID_SUFFIX = '_cyan_cartridge'
    MAGENTA_CARTRIDGE_ID_SUFFIX = '_magenta_cartridge'
    YELLOW_CARTRIDGE_ID_SUFFIX = '_yellow_cartridge'
    
    DEVICE_CLASS_ATTR = 'device_class'
    FRIENDLY_NAME_ATTR = 'friendly_name'
    INSTEON_ADDRESS_ATTR = 'insteon_address'
    OPTIONS_ATTR = 'options'
    UNIT_OF_MEASUREMENT_ATTR = 'unit_of_measurement'
    
    BATTERY_DEVICE_CLASS = 'battery'
    BLIND_DEVICE_CLASS = 'blind'  # cover domain
    CARBON_MONOXIDE_DEVICE_CLASS = 'carbon_monoxide'
    CONNECTIVITY_DEVICE_CLASS = 'connectivity'
    DOOR_DEVICE_CLASS = 'door'
    ENUM_DEVICE_CLASS = 'enum'
    GARAGE_DEVICE_CLASS = 'garage'  # cover domain
    GARAGE_DOOR_DEVICE_CLASS = 'garage_door'  # binary_sensor domain
    GAS_DEVICE_CLASS = 'gas'
    HUMIDITY_DEVICE_CLASS = 'humidity'
    ILLUMINANCE_DEVICE_CLASS = 'illuminance'
    LIGHT_DEVICE_CLASS = 'light'
    MOISTURE_DEVICE_CLASS = 'moisture'
    MOTION_DEVICE_CLASS = 'motion'
    OCCUPANCY_DEVICE_CLASS = 'occupancy'
    OPENING_DEVICE_CLASS = 'opening'
    OUTLET_DEVICE_CLASS = 'outlet'
    POWER_DEVICE_CLASS = 'power'
    PRESENCE_DEVICE_CLASS = 'presence'
    PRESSURE_DEVICE_CLASS = 'pressure'
    SMOKE_DEVICE_CLASS = 'smoke'
    TEMPERATURE_DEVICE_CLASS = 'temperature'
    TIMESTAMP_DEVICE_CLASS = 'timestamp'
    WIND_SPEED_DEVICE_CLASS = 'wind_speed'
    WINDOW_DEVICE_CLASS = 'window'

    OPEN_CLOSE_DEVICE_CLASS_SET = { DOOR_DEVICE_CLASS,
                                    GARAGE_DOOR_DEVICE_CLASS,
                                    OPENING_DEVICE_CLASS,
                                    WINDOW_DEVICE_CLASS }

    MOTION_LIKE_DEVICE_CLASS_SET = { MOTION_DEVICE_CLASS,
                                     OCCUPANCY_DEVICE_CLASS,
                                     PRESENCE_DEVICE_CLASS }

    # Climate-domain attributes and wire values.
    CURRENT_TEMPERATURE_ATTR = 'current_temperature'
    CURRENT_HUMIDITY_ATTR    = 'current_humidity'
    TARGET_TEMPERATURE_ATTR  = 'temperature'           # HA's setpoint attribute name
    TARGET_TEMP_LOW_ATTR     = 'target_temp_low'
    TARGET_TEMP_HIGH_ATTR    = 'target_temp_high'
    HVAC_MODE_ATTR           = 'hvac_mode'
    HVAC_MODES_ATTR          = 'hvac_modes'
    HVAC_ACTION_ATTR         = 'hvac_action'
    FAN_MODE_ATTR            = 'fan_mode'
    FAN_MODES_ATTR           = 'fan_modes'
    TEMPERATURE_UNIT_ATTR    = 'temperature_unit'
    HVAC_MODE_HEAT_COOL      = 'heat_cool'             # dual-setpoint mode wire value

    # Light-domain attributes.
    BRIGHTNESS_ATTR             = 'brightness'
    BRIGHTNESS_PCT_PARAM        = 'brightness_pct'     # service-call parameter name
    COLOR_MODE_ATTR             = 'color_mode'
    COLOR_TEMP_KELVIN_ATTR      = 'color_temp_kelvin'
    HS_COLOR_ATTR               = 'hs_color'
    MIN_COLOR_TEMP_KELVIN_ATTR  = 'min_color_temp_kelvin'
    MAX_COLOR_TEMP_KELVIN_ATTR  = 'max_color_temp_kelvin'
    SUPPORTED_COLOR_MODES_ATTR  = 'supported_color_modes'

    # Color mode wire values (the value space of the COLOR_MODE_ATTR).
    COLOR_MODE_UNKNOWN     = 'unknown'
    COLOR_MODE_ONOFF       = 'onoff'
    COLOR_MODE_BRIGHTNESS  = 'brightness'
    COLOR_MODE_COLOR_TEMP  = 'color_temp'
    COLOR_MODE_HS          = 'hs'
    COLOR_MODE_RGB         = 'rgb'
    COLOR_MODE_RGBW        = 'rgbw'
    COLOR_MODE_RGBWW       = 'rgbww'
    COLOR_MODE_WHITE       = 'white'
    COLOR_MODE_XY          = 'xy'

    # Fan-domain attributes and wire values.
    PERCENTAGE_ATTR       = 'percentage'
    OSCILLATING_ATTR      = 'oscillating'
    DIRECTION_ATTR        = 'direction'
    PRESET_MODE_ATTR      = 'preset_mode'
    PRESET_MODES_ATTR     = 'preset_modes'

    # Camera-domain attributes and state values.
    MOTION_DETECTION_ATTR = 'motion_detection'
    CAMERA_STATE_IDLE = 'idle'
    CAMERA_STATE_STREAMING = 'streaming'
    CAMERA_STATE_RECORDING = 'recording'
    FAN_DIRECTION_FORWARD = 'forward'
    FAN_DIRECTION_REVERSE = 'reverse'

    # Cover-domain attributes.
    CURRENT_POSITION_ATTR = 'current_position'
    POSITION_PARAM        = 'position'                 # service-call parameter name

    # Media-player-domain service parameter.
    VOLUME_LEVEL_PARAM    = 'volume_level'



@dataclass
class HassState:
    """ Wraps the JSON object from the API """

    api_dict                 : Dict
    entity_id                : str
    domain                   : str
    entity_name_sans_prefix  : str
    entity_name_sans_suffix  : str
    ignore                   : bool  = True
    
    # Legacy property for backward compatibility (remove after migration)
    @property
    def entity_id_prefix(self) -> str:
        return self.domain
    
    def __str__(self):
        return f'HassState: {self.entity_id}'
    
    def __repr__(self):
        return self.__str__()

    @property
    def attributes(self):
        attributes = self.api_dict.get( HassApi.ATTRIBUTES_FIELD )
        if not attributes:
            attributes = dict()
        return attributes

    @property
    def friendly_name(self):
        return self.attributes.get( HassApi.FRIENDLY_NAME_ATTR )

    @property
    def state_value(self):
        return self.api_dict.get( HassApi.STATE_FIELD )
        
    @property
    def device_class(self):
        return self.attributes.get( HassApi.DEVICE_CLASS_ATTR )

    @property
    def insteon_address(self):
        return self.attributes.get( HassApi.INSTEON_ADDRESS_ATTR )
    
    @property
    def unit_of_measurement(self):
        return self.attributes.get( HassApi.UNIT_OF_MEASUREMENT_ATTR )

    @property
    def options(self):
        return self.attributes.get( HassApi.OPTIONS_ATTR, list() )

    @property
    def device_group_id(self):
        # When there are other attributes that can uniquely identify a
        # device for a collection of states, this is used to collate all
        # the states into a single device.
        if self.insteon_address:
            return f'insteon:{self.insteon_address}'
        return None


@dataclass
class HassServiceCall:
    """Outbound HA service call composed from a HI control value."""

    domain          : str
    service         : str
    hass_entity_id  : str
    service_data    : Optional[Dict] = None


class HassDevice:
    """ An aggregate of one or more HassStates associated with a single device. """
    
    def __init__( self, device_id : str ):
        self._device_id = device_id
        self._hass_state_list = list()
        return

    def __str__(self):
        return f'HassDevice: {self.device_id}'
    
    def __repr__(self):
        return self.__str__()

    @property
    def device_id(self):
        return self._device_id

    def add_state( self, hass_state : HassState ):
        self._hass_state_list.append( hass_state )
        return

    @property
    def hass_state_list(self):
        return self._hass_state_list
    
    @property
    def device_class_set(self):
        return { x.device_class for x in self._hass_state_list if x.device_class }
    
    @property
    def domain_set(self):
        return { x.domain for x in self._hass_state_list }
    
    # Legacy property for backward compatibility (remove after migration)
    @property
    def entity_id_prefix_set(self):
        return self.domain_set
    
    def to_dict(self):
        return {
            'device_id': self.device_id,
            'num_states': len(self._hass_state_list),
            'prefixes': list( self.entity_id_prefix_set ),
            'states': [ x.api_dict for x in self._hass_state_list ],
        }
