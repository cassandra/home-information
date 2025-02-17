import logging
import re
from typing import Dict, List

from django.db import transaction

from hi.apps.attribute.enums import (
    AttributeType,
    AttributeValueType,
)
from hi.apps.entity.enums import (
    EntityType,
    EntityStateValue,
    HumidityUnit,
    TemperatureUnit,
)
from hi.apps.entity.models import Entity, EntityAttribute, EntityState
from hi.apps.model_helper import HiModelHelper

from hi.integrations.integration_key import IntegrationKey

from .enums import HassStateValue
from .hass_metadata import HassMetaData
from .hass_models import HassApi, HassState, HassDevice

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
        HassApi.AUTOMATION_ID_PREFIX,
        HassApi.CALENDAR_ID_PREFIX,
        HassApi.CONVERSATION_ID_PREFIX,
        HassApi.PERSON_ID_PREFIX,
        HassApi.SCRIPT_ID_PREFIX,
        HassApi.TODO_ID_PREFIX,
        HassApi.TTS_ID_PREFIX,
        HassApi.ZONE_ID_PREFIX,
    }

    # Suffixes that suggest the HAss state may be part of another device
    # and the "name" of the device precedes the suffix.
    #
    STATE_SUFFIXES = {

        HassApi.BATTERY_ID_SUFFIX,
        HassApi.EVENTS_last_HOUR_ID_SUFFIX,
        HassApi.HUMIDITY_ID_SUFFIX,
        HassApi.LIGHT_ID_SUFFIX,
        HassApi.MOTION_ID_SUFFIX,
        HassApi.STATE_ID_SUFFIX,
        HassApi.STATUS_ID_SUFFIX,
        HassApi.TEMPERATURE_ID_SUFFIX,

        # Sun
        HassApi.NEXT_SETTING_ID_SUFFIX,
        HassApi.NEXT_RISING_ID_SUFFIX,
        HassApi.NEXT_NOON_ID_SUFFIX,
        HassApi.NEXT_MIDNIGHT_ID_SUFFIX,
        HassApi.NEXT_DUSK_ID_SUFFIX,
        HassApi.NEXT_DAWN_ID_SUFFIX,

        # Printer
        HassApi.BLACK_CARTRIDGE_ID_SUFFIX,
    }

    # HAss entity id prefixes that define an two-value (on-off) switch
    #
    SWITCH_PREFIXES = {
        HassApi.SWITCH_ID_PREFIX,
        HassApi.LIGHT_ID_PREFIX,
    }
    SENSOR_PREFIXES = {
        HassApi.BINARY_SENSOR_ID_PREFIX,
        HassApi.SENSOR_ID_PREFIX,
    }

    PREFERRED_NAME_PREFIXES = {
        HassApi.CAMERA_ID_PREFIX,
        HassApi.CLIMATE_ID_PREFIX,
        HassApi.LIGHT_ID_PREFIX,
        HassApi.SUN_ID_PREFIX,
    }
    PREFERRED_NAME_DEVICE_CLASSES = {
        HassApi.MOTION_DEVICE_CLASS,
    }

    INSTEON_ADDRESS_ATTR_NAME = 'Insteon Address'

    @classmethod
    def create_hass_state( cls, api_dict : Dict ) -> HassState:

        entity_id = api_dict.get( HassApi.ENTITY_ID_FIELD )

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
    def hass_states_to_hass_devices( cls,
                                     hass_entity_id_to_state : Dict[ str, HassState ]
                                     ) -> Dict[ str, HassDevice ]:
        """
        The Home Assistant (HAss) model we see by fetching the HAss states does
        not explicitly define the 'devices' that those states are attached
        to.  These devices are the model equivalent of the 'Entity' model,
        while HAss states will map 1-to-1 with the 'EntityState' models.
        Thus, we use this routine to heuristally collate the HA states into
        HAss devices to help map from the HAss model to this app's model.
        """
        
        ##########
        # First pass to gather candidate device names.
        
        # All names (ignoring prefix) seen with a known suffix. Values are set of prefixes seen.
        names_seen_with_suffixes = dict()

        # All full names seen (ignoring suffix). Values are set of prefixes seen.
        full_names_without_prefix = dict()

        # Special group names when there are othere attributes that
        # uniquely identify a device.
        #
        group_ids = dict()
        
        for hass_state in hass_entity_id_to_state.values():
            prefix = hass_state.entity_id_prefix
            full_name = hass_state.entity_name_sans_prefix
            short_name = hass_state.entity_name_sans_suffix

            if prefix in cls.IGNORE_PREFIXES:
                continue

            # All states with same insteon address are from same device
            if hass_state.device_group_id:
                if hass_state.device_group_id not in group_ids:
                    group_ids[hass_state.device_group_id] = set()
                group_ids[hass_state.device_group_id].add( prefix )
            
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

            # Simplest case of having explicit group id
            if hass_state.device_group_id in hass_device_id_to_device:
                hass_device = hass_device_id_to_device[hass_state.device_group_id]
                hass_device.add_state( hass_state = hass_state )
                continue
                
            # Next case of joining states is when only the prefix is different.
            if full_name in hass_device_id_to_device:
                hass_device = hass_device_id_to_device[full_name]
                hass_device.add_state( hass_state = hass_state )
                continue

            # Next case is when the short name matches to another state
            if short_name in hass_device_id_to_device:
                hass_device = hass_device_id_to_device[short_name]
                hass_device.add_state( hass_state = hass_state )
                continue
            
            # Note that if no known suffix was found, short_name == full_name

            if hass_state.device_group_id:
                device_id = hass_state.device_group_id
            else:
                device_id = short_name

            hass_device = HassDevice( device_id = device_id )
            hass_device.add_state( hass_state )
            hass_device_id_to_device[device_id] = hass_device
            continue

        return hass_device_id_to_device
    
    @classmethod
    def create_models_for_hass_device( cls,
                                       hass_device       : HassDevice,
                                       add_alarm_events  : bool  ) -> Entity:
        
        with transaction.atomic():

            entity_integration_key = cls.hass_device_to_integration_key( hass_device = hass_device )
            entity_name = cls.hass_device_to_entity_name( hass_device )
            entity_type = cls.hass_device_to_entity_type( hass_device )
            
            entity = Entity(
                name = entity_name,
                entity_type_str = str(entity_type),
                can_user_delete = HassMetaData.allow_entity_deletion,
            )
            entity.integration_key = entity_integration_key
            entity.save()
            
            insteon_address = cls.hass_device_to_insteon_address( hass_device )
            if insteon_address:
                EntityAttribute.objects.create(
                    entity = entity,
                    name = cls.INSTEON_ADDRESS_ATTR_NAME,
                    value = insteon_address,
                    value_type_str = str( AttributeValueType.TEXT ),
                    attribute_type_str = str( AttributeType.PREDEFINED ),
                    is_editable = False,
                    is_required = False,
                )

            cls._create_hass_sensors_and_controllers(
                entity = entity,
                hass_device = hass_device,
                hass_state_list = hass_device.hass_state_list,
                add_alarm_events = add_alarm_events,
            )

        return entity
    
    @classmethod
    def update_models_for_hass_device( cls, entity : Entity, hass_device : HassDevice ) -> List[str]:

        messages = list()
        with transaction.atomic():

            entity_name = cls.hass_device_to_entity_name( hass_device )
            entity_type = cls.hass_device_to_entity_type( hass_device )
            if entity.name != entity_name:
                messages.append(f'Name changed for {entity}. Setting to "{entity_name}"')
                entity.name = entity_name
                entity.save()

            if entity.entity_type != entity_type:
                messages.append(f'Type changed for {entity}. Setting to "{entity_type}"')
                entity.entity_type = entity_type
                entity.save()
            
            insteon_address = cls.hass_device_to_insteon_address( hass_device )
            try:
                attribute = entity.attributes.get( name = cls.INSTEON_ADDRESS_ATTR_NAME )
            except EntityAttribute.DoesNotExist:
                attribute = None

            if attribute and insteon_address:
                if attribute.value == insteon_address:
                    pass
                    
                else:
                    messages.append( f'Insteon address changed for {entity}. Setting to {insteon_address}' )
                    attribute.value = insteon_address
                    attribute.save()
                    
            elif attribute and not insteon_address:
                messages.append( f'Insteon address removed for {entity}. Removing {insteon_address}' )
                attribute.delete()
                
            elif not attribute and insteon_address:
                messages.append( f'No insteon address for {entity}. Adding {insteon_address}' )
                EntityAttribute.objects.create(
                    entity = entity,
                    name = cls.INSTEON_ADDRESS_ATTR_NAME,
                    value = insteon_address,
                    value_type_str = str( AttributeValueType.TEXT ),
                    attribute_type_str = str( AttributeType.PREDEFINED ),
                    is_editable = False,
                    is_required = False,
                )
            else:
                pass
                
            # HAss states becomes a HI state with a Sensor and some may
            # have also require a Controller.
            #
            entiity_sensors = dict()
            entiity_controllers = dict()
            for entity_state in entity.states.all():
                entiity_sensors.update({ x.integration_key: x for x in entity_state.sensors.all() })
                entiity_controllers.update({ x.integration_key: x for x in entity_state.controllers.all() })
                continue

            new_hass_state_list = list()
            seen_state_integration_keys = set()
            for hass_state in hass_device.hass_state_list:
                
                state_integration_key = cls.hass_state_to_integration_key( hass_state = hass_state )
                seen_state_integration_keys.add( state_integration_key )
                
                sensor = entiity_sensors.get( state_integration_key )
                controller = entiity_controllers.get( state_integration_key )

                if not sensor and not controller:
                    messages.append( f'Missing sensors/controllers for {entity}. Adding {hass_state}' )
                    new_hass_state_list.append( hass_state )
                    
                continue

            if new_hass_state_list:
                cls._create_hass_sensors_and_controllers(
                    entity = entity,
                    hass_device = hass_device,
                    hass_state_list = new_hass_state_list,
                    add_alarm_events = False,
                )
            
            for integration_key, sensor in entiity_sensors.items():
                if integration_key not in seen_state_integration_keys:
                    messages.append(f'Removing sensor {sensor} from {entity}' )
                    sensor.delete()
                continue

            for integration_key, controller in entiity_controllers.items():
                if integration_key not in seen_state_integration_keys:
                    messages.append(f'Removing controller {controller} from {entity}' )
                    controller.delete()
                continue

        if not messages:
            messages.append( f'No changes found for {entity}.' )
        return messages

    @classmethod
    def _create_hass_sensors_and_controllers( cls,
                                              entity            : Entity,
                                              hass_device       : HassDevice,
                                              hass_state_list   : List[ HassState ],
                                              add_alarm_events  : bool ):
        """
        Each HAss state of the device becomes a HI state with a Sensor.
        Some may have also require a Controller.
        """
        
        # Observations:
        #
        #   - Some insteon light switches have both a 'switch' and 'light'
        #     HAss state.  These are just one actualy device state but HAss
        #     create duplicates to allow the switch to be treated as a
        #     "light" or something else if it is controlling something
        #     else. Thus, this is a HAss-internal artifact and not an
        #     instrinsic state of the device.
        #
        #   - Some light switches only have 'light' HAss state. e.g., Dimmers
        #
        # To deal with this, we have a special case so that we only create
        # one underlying EntityState and Sensor for the two different HAss
        # perspectives.  A HassState is really the equivalent of a Sensor
        # in our data model and we do not need the duplicates that are just
        # a HAss-specific need.

        prefixes_seen = set()
        ignore_light_state_prefixes = set()
        
        for hass_state in hass_state_list:
            
            if (( hass_state.entity_id_prefix == HassApi.SWITCH_ID_PREFIX )
                and ( HassApi.LIGHT_ID_PREFIX in prefixes_seen )):
                ignore_light_state_prefixes.add( hass_state.entity_id_prefix )

            elif (( hass_state.entity_id_prefix == HassApi.LIGHT_ID_PREFIX )
                  and ( HassApi.SWITCH_ID_PREFIX in prefixes_seen )):
                ignore_light_state_prefixes.add( hass_state.entity_id_prefix )

            prefixes_seen.add( hass_state.entity_id_prefix )
            continue
        
        prefix_to_entity_state = dict()
        for hass_state in hass_state_list:
            state_integration_key = cls.hass_state_to_integration_key( hass_state = hass_state )

            if (( hass_state.entity_id_prefix == HassApi.LIGHT_ID_PREFIX )
                and ( hass_state.entity_id_prefix in ignore_light_state_prefixes )):
                continue

            entity_state = cls._create_hass_state_sensor_or_controller(
                hass_device = hass_device,
                hass_state = hass_state,
                entity = entity,
                integration_key = state_integration_key,
                add_alarm_events = add_alarm_events,
            )
            prefix_to_entity_state[hass_state.entity_id_prefix] = entity_state
            continue
        return
    
    @classmethod
    def _create_hass_state_sensor_or_controller( cls,
                                                 hass_device       : HassDevice,
                                                 hass_state        : HassState,
                                                 entity            : Entity,
                                                 integration_key   : IntegrationKey,
                                                 add_alarm_events  : bool ) -> EntityState: 
        name = hass_state.friendly_name
        device_class = hass_state.device_class
        if not name:
            name = f'{entity.name} ({hass_state.entity_id_prefix})'

        ##########
        # Controllers - Only for states we explicitly know are controllable.
        
        if hass_state.entity_id_prefix in cls.SWITCH_PREFIXES:
            controller = HiModelHelper.create_on_off_controller(
                entity = entity,
                integration_key = integration_key,
                name = name,
            )
            return controller.entity_state

        ##########
        # Sensors - All HAss states are at least a sensor except for those
        # we know are controllable.  

        if hass_state.entity_id_prefix == HassApi.SUN_ID_PREFIX:
            sensor = HiModelHelper.create_multivalued_sensor(
                entity = entity,
                integration_key = integration_key,
                name = name,
            )
            return sensor.entity_state

        if hass_state.entity_id_prefix == HassApi.WEATHER_ID_PREFIX:
            sensor = HiModelHelper.create_multivalued_sensor(
                entity = entity,
                integration_key = integration_key,
                name = name,
            )
            return sensor.entity_state

        if hass_state.entity_id_prefix == HassApi.BINARY_SENSOR_ID_PREFIX:
            sensor = cls._create_hass_state_binary_sensor(
                hass_device = hass_device,
                hass_state = hass_state,
                entity = entity,
                integration_key = integration_key,
                add_alarm_events = add_alarm_events,
            )
            return        
        
        if device_class == HassApi.TEMPERATURE_DEVICE_CLASS:
            if 'c' in hass_state.unit_of_measurement.lower():
                temperature_unit = TemperatureUnit.CELSIUS
            else:
                temperature_unit = TemperatureUnit.FAHRENHEIT

            sensor = HiModelHelper.create_temperature_sensor(
                entity = entity,
                integration_key = integration_key,
                name = name,
                temperature_unit = temperature_unit,
            )
            return sensor.entity_state

        if device_class == HassApi.HUMIDITY_DEVICE_CLASS:
            if 'kg' in hass_state.unit_of_measurement.lower():
                humidity_unit = HumidityUnit.GRAMS_PER_KILOGRAM
            elif 'g' in hass_state.unit_of_measurement.lower():
                humidity_unit = HumidityUnit.GRAMS_PER_CUBIN_METER
            else:  
                humidity_unit = HumidityUnit.PERCENT

            sensor = HiModelHelper.create_humidity_sensor(
                entity = entity,
                integration_key = integration_key,
                name = name,
                humidity_unit = humidity_unit,
            )
            return sensor.entity_state

        if device_class == HassApi.TIMESTAMP_DEVICE_CLASS:
            sensor = HiModelHelper.create_datetime_sensor(
                entity = entity,
                integration_key = integration_key,
                name = name,
            )
            return sensor.entity_state

        if device_class == HassApi.ENUM_DEVICE_CLASS:
            sensor = HiModelHelper.create_discrete_sensor(
                entity = entity,
                name_label_dict = { x: x for x in hass_state.options },
                integration_key = integration_key,
                name = name,
            )
            return sensor.entity_state

        sensor = HiModelHelper.create_blob_sensor(
            entity = entity,
            integration_key = integration_key,
            name = name,
        )
        return sensor.entity_state
    
    @classmethod
    def _create_hass_state_binary_sensor( cls,
                                          hass_device       : HassDevice,
                                          hass_state        : HassState,
                                          entity            : Entity,
                                          integration_key   : IntegrationKey,
                                          add_alarm_events  : bool ):
        name = hass_state.friendly_name
        device_class = hass_state.device_class
        if not name and device_class:
            name = f'{entity.name} ({device_class})'
        elif not name:
            name = f'{entity.name} ({hass_state.entity_id_prefix})'

        if hass_state.device_class == HassApi.CONNECTIVITY_DEVICE_CLASS:
            sensor = HiModelHelper.create_connectivity_sensor(
                entity = entity,
                integration_key = integration_key,
                name = name,
            )
            if add_alarm_events:
                HiModelHelper.create_connectivity_event_definition(
                    name = f'{sensor.name} Alarm',
                    entity_state = sensor.entity_state,
                    integration_key = integration_key,
                )
        elif hass_state.device_class in HassApi.OPEN_CLOSE_DEVICE_CLASS_SET:
            sensor = HiModelHelper.create_open_close_sensor(
                entity = entity,
                integration_key = integration_key,
                name = name,
            )
            if add_alarm_events:
                HiModelHelper.create_open_close_event_definition(
                    name = f'{sensor.name} Alarm',
                    entity_state = sensor.entity_state,
                    integration_key = integration_key,
                )
        elif hass_state.device_class == HassApi.MOTION_DEVICE_CLASS:
            sensor = HiModelHelper.create_movement_sensor(
                entity = entity,
                integration_key = integration_key,
                name = name,
            )
            if add_alarm_events:
                HiModelHelper.create_movement_event_definition(
                    name = f'{sensor.name} Alarm',
                    entity_state = sensor.entity_state,
                    integration_key = integration_key,
                )
        elif hass_state.device_class == HassApi.LIGHT_DEVICE_CLASS:
            HiModelHelper.create_on_off_sensor(
                entity = entity,
                integration_key = integration_key,
                name = name,
            )
        elif hass_state.device_class == HassApi.BATTERY_DEVICE_CLASS:
            sensor = HiModelHelper.create_high_low_sensor(
                entity = entity,
                integration_key = integration_key,
                name = name,
            )
            if add_alarm_events:
                HiModelHelper.create_battery_event_definition(
                    name = f'{sensor.name} Alarm',
                    entity_state = sensor.entity_state,
                    integration_key = integration_key,
                )
        else:
            HiModelHelper.create_on_off_sensor(
                entity = entity,
                integration_key = integration_key,
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
        return hass_device.device_id
        
    @classmethod
    def hass_device_to_entity_type( cls, hass_device : HassDevice ) -> EntityType:
        prefix_set = hass_device.entity_id_prefix_set
        device_class_set = hass_device.device_class_set

        if HassApi.CAMERA_ID_PREFIX in prefix_set:
            return EntityType.CAMERA
        if HassApi.WEATHER_ID_PREFIX in prefix_set:
            return EntityType.WEATHER_STATION
        if HassApi.TIMESTAMP_DEVICE_CLASS in device_class_set:
            return EntityType.TIME_SOURCE
        if ( HassApi.BINARY_SENSOR_ID_PREFIX in prefix_set
             and device_class_set.intersection( HassApi.OPEN_CLOSE_DEVICE_CLASS_SET )):
            return EntityType.OPEN_CLOSE_SENSOR
        if HassApi.MOTION_DEVICE_CLASS in device_class_set:
            return EntityType.MOTION_SENSOR
        if ( HassApi.LIGHT_ID_PREFIX in prefix_set
             or HassApi.LIGHT_DEVICE_CLASS in device_class_set ):
            return EntityType.LIGHT
        if HassApi.OUTLET_DEVICE_CLASS in device_class_set:
            return EntityType.WALL_SWITCH
        if HassApi.TEMPERATURE_DEVICE_CLASS in device_class_set:
            return EntityType.THERMOSTAT
        if HassApi.CONNECTIVITY_DEVICE_CLASS in device_class_set:
            return EntityType.HEALTHCHECK
  
        return EntityType.OTHER
            
    @classmethod
    def hass_device_to_insteon_address( cls, hass_device : HassDevice ) -> str:
        for hass_state in hass_device.hass_state_list:
            if hass_state.insteon_address:
                return hass_state.insteon_address
            continue
        return None

    @classmethod
    def hass_device_to_integration_key( cls, hass_device : HassDevice ) -> IntegrationKey:
        return IntegrationKey(
            integration_id = HassMetaData.integration_id,
            integration_name = hass_device.device_id,
        )

    @classmethod
    def hass_state_to_integration_key( cls, hass_state : HassState ) -> IntegrationKey:
        return IntegrationKey(
            integration_id = HassMetaData.integration_id,
            integration_name = hass_state.entity_id,
        )
    
    @classmethod
    def hass_state_to_sensor_value_str( self, hass_state : HassState ) -> str:

        if hass_state.entity_id_prefix == HassApi.SUN_ID_PREFIX:
            return hass_state.state_value
        
        elif hass_state.entity_id_prefix == HassApi.WEATHER_ID_PREFIX:
            return hass_state.state_value
        
        elif hass_state.entity_id_prefix == HassApi.BINARY_SENSOR_ID_PREFIX:

            if hass_state.state_value.lower() == HassStateValue.ON:
                if hass_state.device_class in HassApi.MOTION_DEVICE_CLASS:
                    return str(EntityStateValue.ACTIVE)
                elif hass_state.device_class in HassApi.BATTERY_DEVICE_CLASS:
                    return str(EntityStateValue.LOW)
                elif hass_state.device_class in HassApi.OPEN_CLOSE_DEVICE_CLASS_SET:
                    return str(EntityStateValue.OPEN)
                elif hass_state.device_class in HassApi.CONNECTIVITY_DEVICE_CLASS:
                    return str(EntityStateValue.CONNECTED)
                else:
                    return str(EntityStateValue.ON)
                
            elif hass_state.state_value.lower() == HassStateValue.OFF:
                if hass_state.device_class in HassApi.MOTION_DEVICE_CLASS:
                    return str(EntityStateValue.IDLE)
                elif hass_state.device_class in HassApi.BATTERY_DEVICE_CLASS:
                    return str(EntityStateValue.HIGH)
                elif hass_state.device_class in HassApi.OPEN_CLOSE_DEVICE_CLASS_SET:
                    return str(EntityStateValue.CLOSED)
                elif hass_state.device_class in HassApi.CONNECTIVITY_DEVICE_CLASS:
                    return str(EntityStateValue.DISCONNECTED)
                else:
                    return str(EntityStateValue.OFF)
            else:
                logger.warning( f'Unknown HAss binary state value "{hass_state.state_value}".' )
                return None
            
        elif hass_state.device_class == HassApi.TEMPERATURE_DEVICE_CLASS:
            return hass_state.state_value
            
        elif hass_state.device_class == HassApi.HUMIDITY_DEVICE_CLASS:
            return hass_state.state_value

        elif hass_state.device_class == HassApi.TIMESTAMP_DEVICE_CLASS:
            return hass_state.state_value

        elif hass_state.device_class == HassApi.ENUM_DEVICE_CLASS:
            return hass_state.state_value

        return hass_state.state_value

    @classmethod
    def hass_entity_id_to_state_value_str( self,
                                           hass_entity_id  : str,
                                           hi_value        : str) -> str:
        if hi_value is None:
            return HassStateValue.OFF
        if hi_value.lower() in [ str(EntityStateValue.OPEN), str(EntityStateValue.ON) ]:
            return HassStateValue.ON
        if hi_value.lower() in [ str(EntityStateValue.CLOSED), str(EntityStateValue.OFF) ]:
            return HassStateValue.OFF
        return hi_value
    
    
