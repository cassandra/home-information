import logging
import re
from typing import Dict

from django.db import transaction

from hi.apps.entity.enums import (
    AttributeName,
    AttributeType,
    AttributeValueType,
    EntityType,
    HumidityUnit,
    TemperatureUnit,
)
from hi.apps.entity.models import Entity, Attribute
from hi.apps.model_helper import HiModelHelper

from hi.integrations.core.enums import IntegrationType

from .hass_models import HassState, HassDevice

logger = logging.getLogger(__name__)


class HassConverter:
    """
    - Converts HAss API states into devices.
    - HAss devices might consist of multiple states.
    - A HAss device is the equivalent of an HI Entity.
    - Determines which HAss devices will be imported into HI.
    - The HAss API reponse does not make the the state to device relationship explicit.
    """

    # Ignore all states that have these prefixes.
    #
    IGNORE_PREFIXES = {
        'automation',
        'calendar',
        'conversation',
        'person',
        'script',
        'todo',
        'tts',
        'zone',
    }

    # Suffixes that suggest the HAss state may be part of another device
    # and the "name" of the device precedes the suffix.
    #
    STATE_SUFFIXES = {
        '_battery',
        '_events_last_hour',
        '_humidity',
        '_light',
        '_motion',
        '_state',
        '_status',
        '_temperature',

        # Sun
        '_next_setting',
        '_next_rising',
        '_next_noon',
        '_next_midnight',
        '_next_dusk',
        '_next_dawn',

        # Printer
        '_black_cartridge',
    }

    # HAss entity id prefixes that define an two-value (on-off) switch
    #
    SWITCH_PREFIXES = {
        'switch',
        'light',
    }
    SENSOR_PREFIXES = {
        'sensor',
        'binary_sensor',
    }

    PREFERRED_NAME_PREFIXES = {
        'camera',
        'light',
        'sun',
        'climate',
    }
    PREFERRED_NAME_DEVICE_CLASSES = {
        'motion',
    }
    
    @classmethod
    def create_hass_state( cls, api_dict : Dict ) -> HassState:

        entity_id = api_dict.get( 'entity_id' )

        # Since a device/entity can have multiple HAss states, and since the API does not 
        m = re.search( r'^([^\.]+)\.(.+)$', entity_id )
        if m:
            prefix = m.group(1)
            full_name = m.group(2)
        else:
            prefix = entity_id
            full_name = entity_id

        name = full_name
        for suffix in cls.STATE_SUFFIXES:
            if not full_name.endswith( suffix ):
                continue
            name = full_name[:-len(suffix)]
            continue

        return HassState(
            api_dict = api_dict,
            entity_id = entity_id,
            entity_id_prefix = prefix,
            entity_name_sans_prefix = full_name,
            entity_name_sans_suffix = name,
        )
    
    @classmethod
    def hass_states_to_hass_devices(
            cls,
            hass_entity_id_to_state : Dict[ str, HassState ] ) -> Dict[ str, HassDevice ]:

        ##########
        # First pass to gather candidate device names.
        
        # All names (ignoring prefix) seen with a known suffix. Values are set of prefixes seen.
        names_seen_with_suffixes = dict()

        # All full names seen (ignoring suffix). Values are set of prefixes seen.
        full_names_without_prefix = dict()

        for hass_state in hass_entity_id_to_state.values():
            prefix = hass_state.entity_id_prefix
            full_name = hass_state.entity_name_sans_prefix
            short_name = hass_state.entity_name_sans_suffix

            if prefix in cls.IGNORE_PREFIXES:
                continue
            
            if full_name not in full_names_without_prefix:
                full_names_without_prefix[full_name] = set()
            full_names_without_prefix[full_name].add( prefix )

            if short_name == full_name:
                continue

            if short_name not in names_seen_with_suffixes:
                names_seen_with_suffixes[short_name] = set()
                names_seen_with_suffixes[short_name].add( prefix )
            
            continue

        ##########
        # Second pass to heuristically collate states into devices.
        
        hass_device_id_to_device = dict()

        for hass_state in hass_entity_id_to_state.values():

            prefix = hass_state.entity_id_prefix
            full_name = hass_state.entity_name_sans_prefix
            short_name = hass_state.entity_name_sans_suffix

            if prefix in cls.IGNORE_PREFIXES:
                continue

            # Simplest case of joining states is when only the prefix is different.
            if full_name in hass_device_id_to_device:
                hass_device = hass_device_id_to_device[full_name]
                hass_device.add_state( hass_state = hass_state )
                continue

            # Next simplest is when the short name matches to another state
            if short_name in hass_device_id_to_device:
                hass_device = hass_device_id_to_device[short_name]
                hass_device.add_state( hass_state = hass_state )
                continue

            # Note that if no known suffix was found, short_name == full_name
            
            hass_device = HassDevice( device_id = short_name )
            hass_device.add_state( hass_state )
            hass_device_id_to_device[short_name] = hass_device
            continue
        
        return hass_device_id_to_device
    
    @classmethod
    def create_models_for_hass_device( cls, hass_device : HassDevice ) -> Entity:

        entity_name = cls.hass_device_to_entity_name( hass_device )
        entity_type = cls.hass_device_to_entity_type( hass_device )
        
        with transaction.atomic():

            entity = Entity.objects.create(
                name = entity_name,
                entity_type_str = str(entity_type),
                integration_type_str = str(IntegrationType.HASS),
                integration_id = str( hass_device.device_id )
            )
            insteon_address = cls.hass_device_to_insteon_address( hass_device )
            if insteon_address:
                Attribute.objects.create(
                    entity = entity,
                    name = AttributeName.INSTEON_ADDRESS,
                    value = insteon_address,
                    attribute_value_type_str = str( AttributeValueType.STRING ),
                    attribute_type_str = str( AttributeType.PREDEFINED ),
                    is_editable = False,
                    is_required = False,
                )

            # Each HAss state of the device becomes a HI state with a Sensor.
            # Some may have also require a Controller.
            #
            for hass_state in hass_device.hass_state_list:
                
                cls._create_hass_state_sensor_or_controller(
                    hass_device = hass_device,
                    hass_state = hass_state,
                    entity = entity,
                )
                continue
            
        return entity
    
    @classmethod
    def _create_hass_state_sensor_or_controller( cls,
                                                 hass_device  : HassDevice,
                                                 hass_state  : HassState,
                                                 entity       : Entity ):
        # Observations:
        #
        #   - Some light switches have both a 'switch' and 'light' HAss state.
        #   - Some light switches only have 'switch' HAss state.
        #   - Some light switches only have 'light' HAss state.
 
        name = hass_state.friendly_name
        device_class = hass_state.device_class
        if not name:
            name = f'{entity.name} ({hass_state.entity_id_prefix})'

        ##########
        # Controllers - Only for states we explicitly know are controllable.
        
        if hass_state.entity_id_prefix in cls.SWITCH_PREFIXES:
            HiModelHelper.create_on_off_controller(
                entity = entity,
                integration_id = hass_state.entity_id,
                name = name,
            )
            return

        ##########
        # Sensors - All HAss states are at least a sensor except for those
        # we know are controllable.  

        if hass_state.entity_id_prefix == 'sun':
            HiModelHelper.create_multivalued_sensor(
                entity = entity,
                integration_id = hass_state.entity_id,
                name = name,
            )
            return

        if hass_state.entity_id_prefix == 'weather':
            HiModelHelper.create_multivalued_sensor(
                entity = entity,
                integration_id = hass_state.entity_id,
                name = name,
            )
            return

        if hass_state.entity_id_prefix == 'binary_sensor':
            cls._create_hass_state_binary_sensor(
                hass_device = hass_device,
                hass_state = hass_state,
                entity = entity,
            )
            return        
        
        if device_class == 'temperature':
            if 'c' in hass_state.unit_of_measurement.lower():
                temperature_unit = TemperatureUnit.CELSIUS
            else:
                temperature_unit = TemperatureUnit.FAHRENHEIT

            HiModelHelper.create_temperature_sensor(
                entity = entity,
                integration_id = hass_state.entity_id,
                name = name,
                temperature_unit = temperature_unit,
            )
            return

        if device_class == 'humidity':
            if 'kg' in hass_state.unit_of_measurement.lower():
                humidity_unit = HumidityUnit.GRAMS_PER_KILOGRAM
            elif 'g' in hass_state.unit_of_measurement.lower():
                humidity_unit = HumidityUnit.GRAMS_PER_CUBIN_METER
            else:  
                humidity_unit = HumidityUnit.PERCENT

            HiModelHelper.create_humidity_sensor(
                entity = entity,
                integration_id = hass_state.entity_id,
                name = name,
                humidity_unit = humidity_unit,
            )
            return

        if device_class == 'timestamp':
            HiModelHelper.create_datetime_sensor(
                entity = entity,
                integration_id = hass_state.entity_id,
                name = name,
            )
            return

        if device_class == 'enum':
            HiModelHelper.create_discrete_sensor(
                entity = entity,
                values = hass_state.options,
                integration_id = hass_state.entity_id,
                name = name,
            )
            return

        HiModelHelper.create_blob_sensor(
            entity = entity,
            integration_id = hass_state.entity_id,
            name = name,
        )
        return
    
    @classmethod
    def _create_hass_state_binary_sensor( cls,
                                          hass_device  : HassDevice,
                                          hass_state  : HassState,
                                          entity       : Entity ):
        name = hass_state.friendly_name
        device_class = hass_state.device_class
        if not name and device_class:
            name = f'{entity.name} ({device_class})'
        elif not name:
            name = f'{entity.name} ({hass_state.entity_id_prefix})'
            
        if hass_state.device_class == 'connectivity':
            HiModelHelper.create_connectivity_sensor(
                entity = entity,
                integration_id = hass_state.entity_id,
                name = name,
            )
        elif 'door' in hass_state.device_class:
            HiModelHelper.create_open_close_sensor(
                entity = entity,
                integration_id = hass_state.entity_id,
                name = name,
            )
        elif hass_state.device_class == 'motion':
            HiModelHelper.create_movement_sensor(
                entity = entity,
                integration_id = hass_state.entity_id,
                name = name,
            )
        elif hass_state.device_class == 'light':
            HiModelHelper.create_on_off_sensor(
                entity = entity,
                integration_id = hass_state.entity_id,
                name = name,
            )
        elif hass_state.device_class == 'battery':
            HiModelHelper.create_high_low_sensor(
                entity = entity,
                integration_id = hass_state.entity_id,
                name = name,
            )
        else:
            HiModelHelper.create_on_off_sensor(
                entity = entity,
                integration_id = hass_state.entity_id,
                name = name,
            )
        return

    @classmethod
    def hass_device_to_entity_name( cls, hass_device : HassDevice ) -> str:

        shortest_id_state = hass_device.hass_state_list[0]
        shortest_id = shortest_id_state.entity_id
        for hass_state in hass_device.hass_state_list:
            friendly_name = hass_state.friendly_name
            if not friendly_name:
                continue
            if hass_state.entity_id_prefix in cls.PREFERRED_NAME_PREFIXES:
                return friendly_name
            if hass_state.device_class in cls.PREFERRED_NAME_DEVICE_CLASSES:
                return friendly_name
            if len(hass_state.entity_id) < len(shortest_id):
                shortest_id = hass_state.entity_id
                shortest_id_state = hass_state
            continue

        friendly_name = shortest_id_state.friendly_name
        if friendly_name:
            return friendly_name
        return hass_device.entity_id
        
    @classmethod
    def hass_device_to_entity_type( cls, hass_device : HassDevice ) -> EntityType:
        prefix_set = hass_device.entity_id_prefix_set
        device_class_set = hass_device.device_class_set
        device_class_str = ' '.join( device_class_set )
        
        if 'camera' in prefix_set:
            return EntityType.CAMERA
        if 'timestamp' in device_class_set:
            return EntityType.TIME_SOURCE
        if 'binary_sensor' in prefix_set and 'door' in device_class_str:
            return EntityType.OPEN_CLOSE_DETECTOR
        if 'motion' in device_class_set:
            return EntityType.MOTION_SENSOR
        if 'light' in prefix_set or 'light' in device_class_set:
            return EntityType.LIGHT
        if 'outlet' in device_class_set:
            return EntityType.WALL_SWITCH
        if 'temperature' in device_class_set:
            return EntityType.THERMOSTAT
        if 'connectivity' in device_class_set:
            return EntityType.HEALTHCHECK
        if 'weather' in prefix_set:
            return EntityType.WEATHER_STATION

        return EntityType.OTHER
            
    @classmethod
    def hass_device_to_insteon_address( cls, hass_device : HassDevice ) -> str:
        for hass_state in hass_device.hass_state_list:
            if hass_state.insteon_address:
                return hass_state.insteon_address
            continue
        return None
