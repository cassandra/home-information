from dataclasses import dataclass
from typing import Dict


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
    LIGHT_ID_SUFFIX = '_light'
    MOTION_ID_SUFFIX = '_motion'
    STATE_ID_SUFFIX = '_state'
    STATUS_ID_SUFFIX = '_status'
    TEMPERATURE_ID_SUFFIX = '_temperature'
    # Sun
    NEXT_DAWN_ID_SUFFIX = '_next_dawn'
    NEXT_DUSK_ID_SUFFIX = '_next_dusk'
    NEXT_MIDNIGHT_ID_SUFFIX = '_next_midnight'
    NEXT_NOON_ID_SUFFIX = '_next_noon'
    NEXT_RISING_ID_SUFFIX = '_next_rising'
    NEXT_SETTING_ID_SUFFIX = '_next_setting'
    # Printer
    BLACK_CARTRIDGE_ID_SUFFIX = '_black_cartridge'
    
    DEVICE_CLASS_ATTR = 'device_class'
    FRIENDLY_NAME_ATTR = 'friendly_name'
    INSTEON_ADDRESS_ATTR = 'insteon_address'
    OPTIONS_ATTR = 'options'
    UNIT_OF_MEASUREMENT_ATTR = 'unit_of_measurement'
    
    BATTERY_DEVICE_CLASS = 'battery'
    CONNECTIVITY_DEVICE_CLASS = 'connectivity'
    DOOR_DEVICE_CLASS = 'door'
    ENUM_DEVICE_CLASS = 'enum'
    GARAGE_DOOR_DEVICE_CLASS = 'garage_door'
    HUMIDITY_DEVICE_CLASS = 'humidity'
    LIGHT_DEVICE_CLASS = 'light'
    MOTION_DEVICE_CLASS = 'motion'
    OUTLET_DEVICE_CLASS = 'outlet'
    TEMPERATURE_DEVICE_CLASS = 'temperature'
    TIMESTAMP_DEVICE_CLASS = 'timestamp'
    WINDOW_DEVICE_CLASS = 'window'

    OPEN_CLOSE_DEVICE_CLASS_SET = { DOOR_DEVICE_CLASS,
                                    GARAGE_DOOR_DEVICE_CLASS,
                                    WINDOW_DEVICE_CLASS }
    

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
