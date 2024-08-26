from dataclasses import dataclass
from typing import Dict


class HassApi:
    """ Central place for translating  HAss API response strings and internal variables. """
    
    ATTRIBUTES_FIELD = 'attributes'
    ENTITY_ID_FIELD = 'entity_id'
    STATE_FIELD = 'state'
        
    AUTOMATION_ID_PREFIX = 'automation'
    BINARY_SENSOR_ID_PREFIX = 'binary_sensor'
    CALENDAR_ID_PREFIX = 'calendar'
    CAMERA_ID_PREFIX = 'camera'
    CLIMATE_ID_PREFIX = ''
    CONVERSATION_ID_PREFIX = 'conversation'
    LIGHT_ID_PREFIX = 'light'
    PERSON_ID_PREFIX = 'person'
    SCRIPT_ID_PREFIX = 'script'
    SENSOR_ID_PREFIX = 'sensor'
    SUN_ID_PREFIX = 'sun'
    SWITCH_ID_PREFIX = 'switch'
    TODO_ID_PREFIX = 'todo'
    TTS_ID_PREFIX = 'tts'
    WEATHER_ID_PREFIX = 'weather'
    ZONE_ID_PREFIX = 'zone'

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

    DOOR_DEVICE_CLASS_SET = { DOOR_DEVICE_CLASS, GARAGE_DOOR_DEVICE_CLASS }
    

@dataclass
class HassState:
    """ Wraps the JSON object from the API """

    api_dict                 : Dict
    entity_id                : str
    entity_id_prefix         : str
    entity_name_sans_prefix  : str
    entity_name_sans_suffix  : str
    ignore                   : bool  = True
    
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
        self._state_list = list()
        return

    def __str__(self):
        return f'HassDevice: {self.device_id}'
    
    def __repr__(self):
        return self.__str__()

    @property
    def device_id(self):
        return self._device_id

    def add_state( self, hass_state : HassState ):
        self._state_list.append( hass_state )
        return

    @property
    def hass_state_list(self):
        return self._state_list
    
    @property
    def device_class_set(self):
        return { x.device_class for x in self._state_list if x.device_class }
    
    @property
    def entity_id_prefix_set(self):
        return { x.entity_id_prefix for x in self._state_list }
    
    def to_dict(self):
        return {
            'device_id': self.device_id,
            'num_states': len(self._state_list),
            'prefixes': list( self.entity_id_prefix_set ),
            'states': [ x.api_dict for x in self._state_list ],
        }
