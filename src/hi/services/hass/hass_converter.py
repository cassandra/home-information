import logging
import re
from typing import Dict, List

from django.db import transaction

from hi.apps.attribute.enums import (
    AttributeType,
    AttributeValueType,
)
from hi.apps.entity.enums import (
    EntityStateType,
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
    Converts Home Assistant API states into HI devices with comprehensive service call support.
    
    OVERVIEW:
    - Converts HA API states into HI devices (Entity models)
    - HA devices may consist of multiple states (e.g., light.kitchen + switch.kitchen = one device)
    - Determines which HA devices are imported into HI
    - HA API response doesn't make state-to-device relationships explicit, so we use heuristics
    
    ARCHITECTURE:
    
    1. DEVICE AGGREGATION (heuristic grouping of HassStates into HassDevices):
       - device_group_id: States with same Insteon address are grouped together
       - full_name matching: States with same name but different domains are grouped
       - suffix-based logic: Removes known suffixes (_temperature, _battery) to find base device
       - switch/light deduplication: Avoids creating duplicate entities for dual-domain devices
    
    2. ENTITY-STATE MAPPING (structured mapping from HA domains/device_classes to EntityStateTypes):
       - Uses HASS_STATE_TO_ENTITY_STATE_TYPE_MAPPING table for consistent, predictable mapping
       - Key: (domain, device_class, has_brightness) → EntityStateType
       - Handles special cases: dimmer lights, door sensors, temperature sensors, etc.
       - Replaces old heuristic if/else chains with maintainable lookup tables
    
    3. CONTROLLABILITY DETERMINATION:
       - ON_OFF_CONTROLLABLE_DOMAINS: light, switch (simple on/off control)  
       - COMPLEX_CONTROLLABLE_DOMAINS: cover, fan, climate, etc. (multiple services)
       - SENSOR_ONLY_DOMAINS: binary_sensor, sensor, camera (read-only)
       - Uses _is_controllable_domain_and_type() for precise control determination
    
    4. SERVICE CALL METADATA (storage of service routing info for device control):
       - CONTROL_SERVICE_MAPPING: (domain, EntityStateType) → service names and parameters
       - Metadata stored during import contains: domain, on_service, off_service, capabilities
       - Controller uses metadata directly without runtime lookups or EntityStateType awareness
       - Enables proper HA service calls (turn_on/turn_off) instead of unreliable set_state API
    
    5. CONTROLLER + SENSOR CREATION:
       - Controllable devices: Create Controller (which auto-creates associated Sensor)
       - Sensor-only devices: Create Sensor only
       - All models store integration metadata for service call routing
       - Maintains 1:1 HassState ↔ EntityState mapping with proper separation of concerns
    
    RATIONALE:
    - Centralizes all HA integration complexity in converter (import-time)  
    - Controller becomes simple metadata consumer (runtime)
    - Service calls work reliably vs set_state which only updates HA internal state
    - Structured mappings are maintainable vs scattered heuristic logic
    - Backward compatible with existing device grouping and alarm event creation
    
    FLOW:
    HA API → HassStates → Device Grouping → EntityState Mapping → Service Metadata → 
    Controller/Sensor Creation → Metadata Storage → Runtime Service Calls
    """

    # Ignore all states from these domains - typically non-physical entities
    # that don't represent controllable devices or useful sensors
    #
    IGNORE_DOMAINS = {
        HassApi.AUTOMATION_DOMAIN,
        HassApi.CALENDAR_DOMAIN,
        HassApi.CONVERSATION_DOMAIN,
        HassApi.PERSON_DOMAIN,
        HassApi.SCRIPT_DOMAIN,
        HassApi.TODO_DOMAIN,
        HassApi.TTS_DOMAIN,
        HassApi.ZONE_DOMAIN,
    }
    
    # Legacy alias for backward compatibility (remove after migration)
    IGNORE_PREFIXES = IGNORE_DOMAINS

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

    # Domains for controllable devices that support on/off operations
    #
    ON_OFF_CONTROLLABLE_DOMAINS = {
        HassApi.SWITCH_DOMAIN,
        HassApi.LIGHT_DOMAIN,
    }
    
    # Domains for controllable devices that support more complex operations
    #
    COMPLEX_CONTROLLABLE_DOMAINS = {
        HassApi.COVER_DOMAIN,      # open, close, set_position
        HassApi.FAN_DOMAIN,        # turn_on, turn_off, set_speed
        HassApi.CLIMATE_DOMAIN,    # set_temperature, set_hvac_mode
        HassApi.LOCK_DOMAIN,       # lock, unlock
        HassApi.MEDIA_PLAYER_DOMAIN, # play, pause, volume_set
    }
    
    # All controllable domains
    ALL_CONTROLLABLE_DOMAINS = ON_OFF_CONTROLLABLE_DOMAINS | COMPLEX_CONTROLLABLE_DOMAINS
    
    # Domains for sensor-only devices (read-only)
    #
    SENSOR_ONLY_DOMAINS = {
        HassApi.BINARY_SENSOR_DOMAIN,
        HassApi.SENSOR_DOMAIN,
        HassApi.CAMERA_DOMAIN,
        HassApi.SUN_DOMAIN,
        HassApi.WEATHER_DOMAIN,
    }
    

    # Domains that should be preferred when choosing friendly names for devices
    #
    PREFERRED_NAME_DOMAINS = {
        HassApi.CAMERA_DOMAIN,
        HassApi.CLIMATE_DOMAIN,
        HassApi.LIGHT_DOMAIN,
        HassApi.SUN_DOMAIN,
    }
    
    PREFERRED_NAME_DEVICE_CLASSES = {
        HassApi.MOTION_DEVICE_CLASS,
    }

    # Mapping 1: Import Mapping - determines EntityStateType during import
    # Key: (domain, device_class_or_None, has_brightness_or_None)
    # Value: EntityStateType
    #
    HASS_STATE_TO_ENTITY_STATE_TYPE_MAPPING = {
        
        # Light Domain
        (HassApi.LIGHT_DOMAIN, None, True): EntityStateType.LIGHT_DIMMER,
        (HassApi.LIGHT_DOMAIN, None, False): EntityStateType.ON_OFF,
        (HassApi.LIGHT_DOMAIN, None, None): EntityStateType.ON_OFF,  # Default when brightness unknown
        
        # Switch Domain
        (HassApi.SWITCH_DOMAIN, None, None): EntityStateType.ON_OFF,
        
        # Cover Domain (blinds, curtains, garage doors)
        (HassApi.COVER_DOMAIN, HassApi.DOOR_DEVICE_CLASS, None): EntityStateType.OPEN_CLOSE,
        (HassApi.COVER_DOMAIN, HassApi.GARAGE_DOOR_DEVICE_CLASS, None): EntityStateType.OPEN_CLOSE,
        (HassApi.COVER_DOMAIN, HassApi.WINDOW_DEVICE_CLASS, None): EntityStateType.OPEN_CLOSE,
        (HassApi.COVER_DOMAIN, None, None): EntityStateType.OPEN_CLOSE,  # Default for covers
        
        # Fan Domain
        (HassApi.FAN_DOMAIN, None, None): EntityStateType.ON_OFF,
        
        # Climate Domain
        (HassApi.CLIMATE_DOMAIN, None, None): EntityStateType.TEMPERATURE,
        
        # Lock Domain
        (HassApi.LOCK_DOMAIN, None, None): EntityStateType.ON_OFF,  # on=locked, off=unlocked
        
        # Media Player Domain
        (HassApi.MEDIA_PLAYER_DOMAIN, None, None): EntityStateType.ON_OFF,
        
        # Binary Sensor Domain (read-only sensors)
        (HassApi.BINARY_SENSOR_DOMAIN, HassApi.MOTION_DEVICE_CLASS, None): EntityStateType.MOVEMENT,
        (HassApi.BINARY_SENSOR_DOMAIN, HassApi.CONNECTIVITY_DEVICE_CLASS, None): EntityStateType.CONNECTIVITY,
        (HassApi.BINARY_SENSOR_DOMAIN, HassApi.BATTERY_DEVICE_CLASS, None): EntityStateType.HIGH_LOW,
        (HassApi.BINARY_SENSOR_DOMAIN, HassApi.DOOR_DEVICE_CLASS, None): EntityStateType.OPEN_CLOSE,
        (HassApi.BINARY_SENSOR_DOMAIN, HassApi.GARAGE_DOOR_DEVICE_CLASS, None): EntityStateType.OPEN_CLOSE,
        (HassApi.BINARY_SENSOR_DOMAIN, HassApi.WINDOW_DEVICE_CLASS, None): EntityStateType.OPEN_CLOSE,
        (HassApi.BINARY_SENSOR_DOMAIN, None, None): EntityStateType.ON_OFF,  # Generic binary sensor
        
        # Sensor Domain (read-only sensors)
        (HassApi.SENSOR_DOMAIN, HassApi.TEMPERATURE_DEVICE_CLASS, None): EntityStateType.TEMPERATURE,
        (HassApi.SENSOR_DOMAIN, HassApi.HUMIDITY_DEVICE_CLASS, None): EntityStateType.HUMIDITY,
        (HassApi.SENSOR_DOMAIN, HassApi.TIMESTAMP_DEVICE_CLASS, None): EntityStateType.DATETIME,
        (HassApi.SENSOR_DOMAIN, HassApi.ENUM_DEVICE_CLASS, None): EntityStateType.DISCRETE,
        (HassApi.SENSOR_DOMAIN, None, None): EntityStateType.BLOB,  # Generic sensor
        
        # Other domains (read-only)
        (HassApi.CAMERA_DOMAIN, None, None): EntityStateType.VIDEO_STREAM,
        (HassApi.SUN_DOMAIN, None, None): EntityStateType.MULTVALUED,
        (HassApi.WEATHER_DOMAIN, None, None): EntityStateType.MULTVALUED,
    }

    # Mapping 2: Control Service Mapping - only for controllable EntityStates
    # Key: (domain, EntityStateType)
    # Value: dict with service names and parameter mappings
    #
    CONTROL_SERVICE_MAPPING = {
        
        # Light Domain Services
        (HassApi.LIGHT_DOMAIN, EntityStateType.ON_OFF): {
            'on_service': HassApi.TURN_ON_SERVICE,
            'off_service': HassApi.TURN_OFF_SERVICE,
            'parameters': {},
        },
        (HassApi.LIGHT_DOMAIN, EntityStateType.LIGHT_DIMMER): {
            'on_service': HassApi.TURN_ON_SERVICE,
            'off_service': HassApi.TURN_OFF_SERVICE,
            'set_service': HassApi.TURN_ON_SERVICE,  # For brightness setting
            'parameters': {
                'brightness_pct': 'percentage',  # 0-100
            },
        },
        
        # Switch Domain Services
        (HassApi.SWITCH_DOMAIN, EntityStateType.ON_OFF): {
            'on_service': HassApi.TURN_ON_SERVICE,
            'off_service': HassApi.TURN_OFF_SERVICE,
            'parameters': {},
        },
        
        # Cover Domain Services
        (HassApi.COVER_DOMAIN, EntityStateType.OPEN_CLOSE): {
            'on_service': HassApi.OPEN_COVER_SERVICE,    # 'on' = open
            'off_service': HassApi.CLOSE_COVER_SERVICE,  # 'off' = close
            'set_service': HassApi.SET_COVER_POSITION_SERVICE,
            'parameters': {
                'position': 'percentage',  # 0-100
            },
        },
        
        # Fan Domain Services
        (HassApi.FAN_DOMAIN, EntityStateType.ON_OFF): {
            'on_service': HassApi.TURN_ON_SERVICE,
            'off_service': HassApi.TURN_OFF_SERVICE,
            'set_service': HassApi.SET_PERCENTAGE_SERVICE,
            'parameters': {
                'percentage': 'percentage',  # 0-100
            },
        },
        
        # Climate Domain Services
        (HassApi.CLIMATE_DOMAIN, EntityStateType.TEMPERATURE): {
            'set_service': HassApi.SET_TEMPERATURE_SERVICE,
            'parameters': {
                'temperature': 'temperature',  # Numeric temperature value
            },
        },
        
        # Lock Domain Services
        (HassApi.LOCK_DOMAIN, EntityStateType.ON_OFF): {
            'on_service': HassApi.LOCK_SERVICE,      # 'on' = locked
            'off_service': HassApi.UNLOCK_SERVICE,   # 'off' = unlocked
            'parameters': {},
        },
        
        # Media Player Domain Services
        (HassApi.MEDIA_PLAYER_DOMAIN, EntityStateType.ON_OFF): {
            'on_service': HassApi.TURN_ON_SERVICE,
            'off_service': HassApi.TURN_OFF_SERVICE,
            'set_service': HassApi.VOLUME_SET_SERVICE,
            'parameters': {
                'volume_level': 'percentage_decimal',  # 0.0-1.0
            },
        },
    }

    INSTEON_ADDRESS_ATTR_NAME = 'Insteon Address'

    @classmethod
    def create_hass_state( cls, api_dict : Dict ) -> HassState:

        entity_id = api_dict.get( HassApi.ENTITY_ID_FIELD )

        # Parse domain from entity_id (e.g., 'light' from 'light.living_room_lamp')
        m = re.search( r'^([^\.]+)\.(.+)$', entity_id )
        if m:
            domain = m.group(1)
            full_name = m.group(2)
        else:
            # Fallback for malformed entity_ids
            domain = entity_id
            full_name = entity_id

        # Remove known suffixes to get device name
        name = full_name
        for suffix in cls.STATE_SUFFIXES:
            if not full_name.endswith( suffix ):
                continue
            name = full_name[:-len(suffix)]
            continue

        return HassState(
            api_dict = api_dict,
            entity_id = entity_id,
            domain = domain,
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
        
        # All names (ignoring domain) seen with a known suffix. Values are set of domains seen.
        names_seen_with_suffixes = dict()

        # All full names seen (ignoring suffix). Values are set of domains seen.
        full_names_without_domain = dict()

        # Special group names when there are other attributes that
        # uniquely identify a device.
        #
        group_ids = dict()
        
        for hass_state in hass_entity_id_to_state.values():
            domain = hass_state.domain
            full_name = hass_state.entity_name_sans_prefix
            short_name = hass_state.entity_name_sans_suffix

            if domain in cls.IGNORE_DOMAINS:
                continue

            # All states with same insteon address are from same device
            if hass_state.device_group_id:
                if hass_state.device_group_id not in group_ids:
                    group_ids[hass_state.device_group_id] = set()
                group_ids[hass_state.device_group_id].add( domain )
            
            if full_name not in full_names_without_domain:
                full_names_without_domain[full_name] = set()
            full_names_without_domain[full_name].add( domain )

            if short_name == full_name:
                continue

            if short_name not in names_seen_with_suffixes:
                names_seen_with_suffixes[short_name] = set()
            names_seen_with_suffixes[short_name].add( domain )
            
            continue

        ##########
        # Second pass to heuristically collate states into devices.
        
        hass_device_id_to_device = dict()

        for hass_state in hass_entity_id_to_state.values():

            domain = hass_state.domain
            full_name = hass_state.entity_name_sans_prefix
            short_name = hass_state.entity_name_sans_suffix

            if domain in cls.IGNORE_DOMAINS:
                continue

            # Simplest case of having explicit group id
            if hass_state.device_group_id in hass_device_id_to_device:
                hass_device = hass_device_id_to_device[hass_state.device_group_id]
                hass_device.add_state( hass_state = hass_state )
                continue
                
            # Next case of joining states is when only the domain is different.
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

                # Update integration metadata for existing sensors and controllers
                # Every HassState should have at least a sensor, potentially also a controller
                if sensor or controller:
                    # Use sensor or controller to determine EntityStateType (they should be the same)
                    model_with_entity_state = controller if controller else sensor
                    existing_entity_state_type = model_with_entity_state.entity_state.entity_state_type
                    is_controllable = cls._is_controllable_domain_and_type(hass_state.domain, existing_entity_state_type)
                    
                    # Generate new metadata using existing logic
                    new_metadata = cls._create_service_metadata(hass_state, existing_entity_state_type, is_controllable)
                    
                    # Update metadata for both sensor and controller if they exist
                    for model, model_type in [(sensor, 'sensor'), (controller, 'controller')]:
                        if model:
                            changed_fields = model.update_integration_metadata(new_metadata)
                            if changed_fields:
                                messages.append(f'Updated metadata for {model_type} {model}: {", ".join(changed_fields)}')
                else:
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
            
            if (( hass_state.domain == HassApi.SWITCH_DOMAIN )
                and ( HassApi.LIGHT_DOMAIN in prefixes_seen )):
                ignore_light_state_prefixes.add( hass_state.domain )

            elif (( hass_state.domain == HassApi.LIGHT_DOMAIN )
                  and ( HassApi.SWITCH_DOMAIN in prefixes_seen )):
                ignore_light_state_prefixes.add( hass_state.domain )

            prefixes_seen.add( hass_state.domain )
            continue
        
        prefix_to_entity_state = dict()
        for hass_state in hass_state_list:
            state_integration_key = cls.hass_state_to_integration_key( hass_state = hass_state )

            if (( hass_state.domain == HassApi.LIGHT_DOMAIN )
                and ( hass_state.domain in ignore_light_state_prefixes )):
                continue

            entity_state = cls._create_hass_state_sensor_or_controller(
                hass_device = hass_device,
                hass_state = hass_state,
                entity = entity,
                integration_key = state_integration_key,
                add_alarm_events = add_alarm_events,
            )
            prefix_to_entity_state[hass_state.domain] = entity_state
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
        if not name:
            name = f'{entity.name} ({hass_state.domain})'

        # Use new mapping logic to determine EntityStateType and controllability
        entity_state_type = cls._determine_entity_state_type_from_mapping( hass_state )
        is_controllable = cls._is_controllable_domain_and_type( hass_state.domain, entity_state_type )
        
        # Create domain metadata for service calls - store service routing info directly
        domain_metadata = cls._create_service_metadata( hass_state, entity_state_type, is_controllable )

        ##########
        # Controllers - Create controller (which also creates sensor) for controllable states
        
        if is_controllable:
            controller = cls._create_controller_from_entity_state_type(
                entity_state_type, entity, integration_key, name, domain_metadata
            )
            return controller.entity_state

        ##########
        # Sensors - Create sensor-only for non-controllable states using mapping logic
        
        sensor = cls._create_sensor_from_entity_state_type_with_params(
            entity_state_type, entity, integration_key, name, domain_metadata,
            hass_state, add_alarm_events
        )
        return sensor.entity_state

    @classmethod
    def _create_hass_state_with_mapping( cls,
                                        hass_device       : HassDevice,
                                        hass_state        : HassState,
                                        entity            : Entity,
                                        integration_key   : IntegrationKey,
                                        add_alarm_events  : bool ) -> EntityState:
        """
        New method using mapping tables to determine EntityStateType and create
        appropriate sensor or controller with domain metadata storage.
        """
        
        # Step 1: Determine EntityStateType using our mapping table
        entity_state_type = cls._determine_entity_state_type_from_mapping( hass_state )
        
        # Step 2: Create domain metadata to store for future service calls
        domain_metadata = {
            'domain': hass_state.domain,
            'device_class': hass_state.device_class,
            'has_brightness': cls._has_brightness_capability( hass_state ),
        }
        
        # Step 3: Create IntegrationKey (metadata will be stored separately)
        integration_key_for_storage = integration_key
        
        # Step 4: Determine if this should be a controller or sensor
        is_controllable = cls._is_controllable_domain_and_type( hass_state.domain, entity_state_type )
        
        # Step 5: Create appropriate model (controller or sensor)
        name = hass_state.friendly_name or f'{entity.name} ({hass_state.domain})'
        
        if is_controllable:
            # Create controller and store metadata
            entity_state = cls._create_controller_from_entity_state_type(
                entity_state_type, entity, integration_key_for_storage, name, domain_metadata
            )
        else:
            # Create sensor and store metadata  
            entity_state = cls._create_sensor_from_entity_state_type(
                entity_state_type, entity, integration_key_for_storage, name, domain_metadata
            )
        
        return entity_state

    @classmethod
    def _determine_entity_state_type_from_mapping( cls, hass_state: HassState ) -> EntityStateType:
        """Use mapping table to determine EntityStateType from HassState"""
        
        domain = hass_state.domain
        device_class = hass_state.device_class
        has_brightness = cls._has_brightness_capability( hass_state )
        
        # Try exact match first
        mapping_key = (domain, device_class, has_brightness)
        if mapping_key in cls.HASS_STATE_TO_ENTITY_STATE_TYPE_MAPPING:
            return cls.HASS_STATE_TO_ENTITY_STATE_TYPE_MAPPING[mapping_key]
        
        # Try with None device_class
        mapping_key = (domain, None, has_brightness)
        if mapping_key in cls.HASS_STATE_TO_ENTITY_STATE_TYPE_MAPPING:
            return cls.HASS_STATE_TO_ENTITY_STATE_TYPE_MAPPING[mapping_key]
        
        # Try with None brightness
        mapping_key = (domain, device_class, None)
        if mapping_key in cls.HASS_STATE_TO_ENTITY_STATE_TYPE_MAPPING:
            return cls.HASS_STATE_TO_ENTITY_STATE_TYPE_MAPPING[mapping_key]
        
        # Try with both None
        mapping_key = (domain, None, None)
        if mapping_key in cls.HASS_STATE_TO_ENTITY_STATE_TYPE_MAPPING:
            return cls.HASS_STATE_TO_ENTITY_STATE_TYPE_MAPPING[mapping_key]
        
        # Fallback for unmapped domains
        logger.warning( f'No mapping found for domain {domain}, device_class {device_class}. Using BLOB.' )
        return EntityStateType.BLOB

    @classmethod
    def _has_brightness_capability( cls, hass_state: HassState ) -> bool:
        """Check if a light has brightness/dimming capability"""
        if hass_state.domain != HassApi.LIGHT_DOMAIN:
            return False
        
        # Check if brightness is in the state attributes
        attributes = hass_state.attributes
        return 'brightness' in attributes or 'brightness_pct' in attributes

    @classmethod
    def _is_controllable_domain_and_type( cls, domain: str, entity_state_type: EntityStateType ) -> bool:
        """Check if this domain+type combination is controllable"""
        return (domain, entity_state_type) in cls.CONTROL_SERVICE_MAPPING

    @classmethod  
    def _create_controller_from_entity_state_type( cls, entity_state_type: EntityStateType, 
                                                  entity: Entity, integration_key: IntegrationKey, 
                                                  name: str, domain_metadata: dict ):
        """Create appropriate controller based on EntityStateType"""
        
        if entity_state_type == EntityStateType.ON_OFF:
            controller = HiModelHelper.create_on_off_controller(
                entity = entity,
                integration_key = integration_key,
                name = name,
            )
        elif entity_state_type == EntityStateType.LIGHT_DIMMER:
            controller = HiModelHelper.create_light_dimmer_controller(
                entity = entity,
                integration_key = integration_key,
                name = name,
            )
        elif entity_state_type == EntityStateType.OPEN_CLOSE:
            controller = HiModelHelper.create_open_close_controller(
                entity = entity,
                integration_key = integration_key,
                name = name,
            )
        elif entity_state_type == EntityStateType.TEMPERATURE:
            controller = HiModelHelper.create_temperature_controller(
                entity = entity,
                integration_key = integration_key,
                name = name,
            )
        else:
            # Fallback - shouldn't happen for controllable types
            logger.warning( f'Unknown controllable EntityStateType: {entity_state_type}' )
            controller = HiModelHelper.create_on_off_controller(
                entity = entity,
                integration_key = integration_key,
                name = name,
            )
        
        # Store domain metadata
        controller.integration_metadata = domain_metadata
        controller.save()
        return controller.entity_state

    @classmethod  
    def _create_sensor_from_entity_state_type( cls, entity_state_type: EntityStateType, 
                                              entity: Entity, integration_key: IntegrationKey, 
                                              name: str, domain_metadata: dict ):
        """Create appropriate sensor based on EntityStateType"""
        
        if entity_state_type == EntityStateType.MOVEMENT:
            sensor = HiModelHelper.create_movement_sensor(
                entity = entity,
                integration_key = integration_key,
                name = name,
            )
        elif entity_state_type == EntityStateType.TEMPERATURE:
            sensor = HiModelHelper.create_temperature_sensor(
                entity = entity,
                integration_key = integration_key,
                name = name,
            )
        elif entity_state_type == EntityStateType.HUMIDITY:
            sensor = HiModelHelper.create_humidity_sensor(
                entity = entity,
                integration_key = integration_key,
                name = name,
            )
        elif entity_state_type == EntityStateType.MULTVALUED:
            sensor = HiModelHelper.create_multivalued_sensor(
                entity = entity,
                integration_key = integration_key,
                name = name,
            )
        elif entity_state_type == EntityStateType.VIDEO_STREAM:
            sensor = HiModelHelper.create_video_stream_sensor(
                entity = entity,
                integration_key = integration_key,
                name = name,
            )
        elif entity_state_type == EntityStateType.CONNECTIVITY:
            sensor = HiModelHelper.create_connectivity_sensor(
                entity = entity,
                integration_key = integration_key,
                name = name,
            )
        elif entity_state_type == EntityStateType.HIGH_LOW:
            sensor = HiModelHelper.create_high_low_sensor(
                entity = entity,
                integration_key = integration_key,
                name = name,
            )
        elif entity_state_type == EntityStateType.ON_OFF:
            sensor = HiModelHelper.create_on_off_sensor(
                entity = entity,
                integration_key = integration_key,
                name = name,
            )
        else:
            # Default fallback
            sensor = HiModelHelper.create_blob_sensor(
                entity = entity,
                integration_key = integration_key,
                name = name,
            )
        
        # Store domain metadata for sensors too
        sensor.integration_metadata = domain_metadata
        sensor.save()
        return sensor.entity_state
    
    @classmethod
    def _create_sensor_from_entity_state_type_with_params( cls, entity_state_type: EntityStateType, 
                                                          entity: Entity, integration_key: IntegrationKey, 
                                                          name: str, domain_metadata: dict,
                                                          hass_state: HassState, add_alarm_events: bool ):
        """Create appropriate sensor with legacy parameter handling"""
        
        if entity_state_type == EntityStateType.TEMPERATURE:
            # Handle temperature units from HA data
            unit_str = hass_state.unit_of_measurement or ''
            if 'c' in unit_str.lower():
                temperature_unit = TemperatureUnit.CELSIUS
            else:
                temperature_unit = TemperatureUnit.FAHRENHEIT
            
            sensor = HiModelHelper.create_temperature_sensor(
                entity = entity,
                integration_key = integration_key,
                name = name,
                temperature_unit = temperature_unit,
            )
        elif entity_state_type == EntityStateType.HUMIDITY:
            # Handle humidity units from HA data
            unit_str = hass_state.unit_of_measurement or ''
            if 'kg' in unit_str.lower():
                humidity_unit = HumidityUnit.GRAMS_PER_KILOGRAM
            elif 'g' in unit_str.lower():
                humidity_unit = HumidityUnit.GRAMS_PER_CUBIN_METER
            else:  
                humidity_unit = HumidityUnit.PERCENT

            sensor = HiModelHelper.create_humidity_sensor(
                entity = entity,
                integration_key = integration_key,
                name = name,
                humidity_unit = humidity_unit,
            )
        elif entity_state_type == EntityStateType.DISCRETE:
            # Handle enum device class with options
            name_label_dict = { x: x for x in hass_state.options } if hass_state.options else {}
            sensor = HiModelHelper.create_discrete_sensor(
                entity = entity,
                name_label_dict = name_label_dict,
                integration_key = integration_key,
                name = name,
            )
        elif entity_state_type == EntityStateType.CONNECTIVITY:
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
        elif entity_state_type == EntityStateType.OPEN_CLOSE:
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
        elif entity_state_type == EntityStateType.MOVEMENT:
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
        elif entity_state_type == EntityStateType.HIGH_LOW:
            sensor = HiModelHelper.create_high_low_sensor(
                entity = entity,
                integration_key = integration_key,
                name = name,
            )
            if add_alarm_events and hass_state.device_class == HassApi.BATTERY_DEVICE_CLASS:
                HiModelHelper.create_battery_event_definition(
                    name = f'{sensor.name} Alarm',
                    entity_state = sensor.entity_state,
                    integration_key = integration_key,
                )
        elif entity_state_type == EntityStateType.DATETIME:
            sensor = HiModelHelper.create_datetime_sensor(
                entity = entity,
                integration_key = integration_key,
                name = name,
            )
        elif entity_state_type == EntityStateType.MULTVALUED:
            sensor = HiModelHelper.create_multivalued_sensor(
                entity = entity,
                integration_key = integration_key,
                name = name,
            )
        elif entity_state_type == EntityStateType.VIDEO_STREAM:
            sensor = HiModelHelper.create_video_stream_sensor(
                entity = entity,
                integration_key = integration_key,
                name = name,
            )
        elif entity_state_type == EntityStateType.ON_OFF:
            sensor = HiModelHelper.create_on_off_sensor(
                entity = entity,
                integration_key = integration_key,
                name = name,
            )
        else:
            # Default fallback
            sensor = HiModelHelper.create_blob_sensor(
                entity = entity,
                integration_key = integration_key,
                name = name,
            )
        
        # Store domain metadata for sensors
        sensor.integration_metadata = domain_metadata
        sensor.save()
        return sensor
    
    @classmethod
    def _create_service_metadata( cls, hass_state: HassState, entity_state_type: EntityStateType, is_controllable: bool ) -> dict:
        """Create metadata with service routing information for controllers"""
        
        # Base metadata for all entities
        metadata = {
            'domain': hass_state.domain,
            'device_class': hass_state.device_class,
            'entity_state_type': str(entity_state_type),
            'is_controllable': is_controllable,
        }
        
        # Add service routing information for controllable entities
        if is_controllable:
            mapping_key = (hass_state.domain, entity_state_type)
            if mapping_key in cls.CONTROL_SERVICE_MAPPING:
                service_mapping = cls.CONTROL_SERVICE_MAPPING[mapping_key]
                metadata.update(service_mapping)
            
            # Add special capabilities
            if entity_state_type == EntityStateType.LIGHT_DIMMER:
                metadata['supports_brightness'] = True
                has_brightness = cls._has_brightness_capability( hass_state )
                metadata['has_brightness'] = has_brightness
            else:
                metadata['supports_brightness'] = False
                metadata['has_brightness'] = False
        
        return metadata
    

    @classmethod
    def hass_device_to_entity_name( cls, hass_device : HassDevice ) -> str:

        shortest_id_state = hass_device.hass_state_list[0]
        shortest_id = shortest_id_state.entity_id
        for hass_state in hass_device.hass_state_list:
            friendly_name = hass_state.friendly_name
            if not friendly_name:
                continue
            if hass_state.domain in cls.PREFERRED_NAME_DOMAINS:
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
        domain_set = hass_device.domain_set
        device_class_set = hass_device.device_class_set

        if HassApi.CAMERA_DOMAIN in domain_set:
            return EntityType.CAMERA
        if HassApi.WEATHER_DOMAIN in domain_set:
            return EntityType.WEATHER_STATION
        if HassApi.TIMESTAMP_DEVICE_CLASS in device_class_set:
            return EntityType.TIME_SOURCE
        if ( HassApi.BINARY_SENSOR_DOMAIN in domain_set
             and device_class_set.intersection( HassApi.OPEN_CLOSE_DEVICE_CLASS_SET )):
            return EntityType.OPEN_CLOSE_SENSOR
        if HassApi.MOTION_DEVICE_CLASS in device_class_set:
            return EntityType.MOTION_SENSOR
        if ( HassApi.LIGHT_DOMAIN in domain_set
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

        if hass_state.domain == HassApi.SUN_DOMAIN:
            return hass_state.state_value
        
        elif hass_state.domain == HassApi.WEATHER_DOMAIN:
            return hass_state.state_value
        
        elif hass_state.domain == HassApi.BINARY_SENSOR_DOMAIN:

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
    
    
