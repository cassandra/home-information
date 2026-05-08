import json
import logging
import re
from typing import Dict, List, Optional, Set, Tuple

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

from hi.integrations.integration_converter_mixin import IntegrationConverterMixin
from hi.integrations.transient_models import IntegrationKey

from .enums import HassStateValue
from .hass_metadata import HassMetaData
from .hass_models import HassApi, HassServiceCall, HassState, HassDevice
from .hass_service_composer import HassServiceComposer

logger = logging.getLogger(__name__)


class HassConverter( IntegrationConverterMixin ):
    """
    Bidirectional bridge between HI's data model and Home
    Assistant's API.

    Terminology:
    - domain        : HA top-level category (``light``, ``switch``,
                      ``binary_sensor``, ``sensor``, ``cover``, ...).
                      The prefix of an entity_id (``light.x`` →
                      domain ``light``).
    - device_class  : Subtype within a domain (``motion``,
                      ``temperature``, ``door``, ...). Reported in
                      the HA state's attributes.
    - entity, state : A single HA entity (one entity_id) and the
                      bundle HA returns for it from
                      ``/api/states/{entity_id}`` (top-level
                      ``state`` field + ``attributes`` dict).
                      ``HassState`` wraps one HA state.
    - substate      : One meaningful atom inside a HA state that
                      maps to one HI EntityState. Simple entities
                      have one substate; color bulbs have several
                      (brightness, hue, saturation, color_temp).
    - device        : An aggregate of HA entities believed to
                      belong to one physical thing. Heuristic
                      grouping (Insteon address, name suffixes)
                      since HA's API doesn't make the relationship
                      explicit.

    Three jobs:
    1. Import-time: HA API → HI Entity + Sensor + Controller
       models. Aggregates entities into devices, maps each substate
       to an EntityStateType, decides controller-vs-sensor, attaches
       an integration_payload carrying service-routing info for
       outbound calls.
    2. Inbound runtime (``hass_state_to_sensor_value_map``): one HA
       state → ``Dict[IntegrationKey, value]``, one entry per
       substate.
    3. Outbound runtime (``hi_value_to_hass_service_call``): one HI
       control value + integration_payload → ``HassServiceCall``.
       Bridge methods parse HI values via ``to_ha_*`` boundary
       helpers and delegate pure HA-side composition to
       ``HassServiceComposer``.
    """

    @staticmethod
    def parse_import_allowlist( allowlist_text : str ) -> Tuple[ Set[str], Set[Tuple[str, str]] ]:
        """Parse allowlist text into domain-only and domain:class rule sets.
        Returns:
            (allowed_domains, allowed_domain_classes) where:
            - allowed_domains: set of domains where all classes are allowed
            - allowed_domain_classes: set of (domain, device_class) tuples
        """
        allowed_domains = set()
        allowed_domain_classes = set()
        for line in allowlist_text.strip().splitlines():
            rule = line.strip()
            if not rule:
                continue
            if ':' in rule:
                domain, device_class = rule.split( ':', 1 )
                allowed_domain_classes.add( ( domain.strip(), device_class.strip() ) )
            else:
                allowed_domains.add( rule )
        return ( allowed_domains, allowed_domain_classes )

    @staticmethod
    def is_state_allowed( hass_state,
                          allowed_domains        : Set[str],
                          allowed_domain_classes  : Set[Tuple[str, str]] ) -> bool:
        """Check if a state matches the allowlist. The allowlist is the sole
        authority when configured — IGNORE_DOMAINS is not consulted."""
        domain = hass_state.domain
        if domain in allowed_domains:
            return True
        device_class = hass_state.device_class or ''
        if ( domain, device_class ) in allowed_domain_classes:
            return True
        return False

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
        HassApi.MEDIA_PLAYER_DOMAIN,  # play, pause, volume_set
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
        # Note: CAMERA_DOMAIN entities should have has_video_stream=True but no VIDEO_STREAM EntityState
        (HassApi.SUN_DOMAIN, None, None): EntityStateType.MULTIVALUED,
        (HassApi.WEATHER_DOMAIN, None, None): EntityStateType.MULTIVALUED,
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
                                     hass_entity_id_to_state  : Dict[ str, HassState ],
                                     import_allowlist          : Optional[str] = None,
                                     ) -> Dict[ str, HassDevice ]:
        """
        The Home Assistant (HAss) model we see by fetching the HAss states does
        not explicitly define the 'devices' that those states are attached
        to.  These devices are the model equivalent of the 'Entity' model,
        while HAss states will map 1-to-1 with the 'EntityState' models.
        Thus, we use this routine to heuristally collate the HA states into
        HAss devices to help map from the HAss model to this app's model.
        """
        
        # When an allowlist is configured, it is the sole authority on what
        # gets imported. When not configured, fall back to IGNORE_DOMAINS.
        if import_allowlist:
            allowed_domains, allowed_domain_classes = cls.parse_import_allowlist( import_allowlist )
            use_allowlist = True
        else:
            allowed_domains = set()
            allowed_domain_classes = set()
            use_allowlist = False

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

            if use_allowlist:
                if not cls.is_state_allowed( hass_state, allowed_domains, allowed_domain_classes ):
                    continue
            elif domain in cls.IGNORE_DOMAINS:
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

            if use_allowlist:
                if not cls.is_state_allowed( hass_state, allowed_domains, allowed_domain_classes ):
                    continue
            elif domain in cls.IGNORE_DOMAINS:
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
                                       add_alarm_events  : bool,
                                       entity            : Optional[Entity] = None ) -> Entity:
        """
        Create or repopulate the integration-owned components for a
        HassDevice. When ``entity`` is None (the standard import path),
        a fresh Entity is created from the upstream device. When
        ``entity`` is provided (the auto-reconnect path from Issue
        #281), the integration-owned fields on that entity are
        repopulated; the entity's ``name`` is deliberately preserved
        because the user may have edited it before/after the
        intervening disconnect.
        """
        with transaction.atomic():

            entity_integration_key = cls.hass_device_to_integration_key( hass_device = hass_device )

            if entity is None:
                entity = Entity(
                    name = cls.hass_device_to_entity_name( hass_device ),
                    entity_type_str = str( cls.hass_device_to_entity_type( hass_device ) ),
                )

            # Integration-owned: re-applied on both fresh-create and
            # reconnect so the entity reflects current upstream state.
            entity.integration_key = entity_integration_key
            entity.can_user_delete = HassMetaData.allow_entity_deletion
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
        """Refresh integration-owned components on an existing entity.

        ``entity.name`` and ``entity.entity_type`` are user-editable
        in HI's UI on HASS entities (``can_add_custom_attributes``
        defaults to True), so they're treated as user-owned after
        creation: this method does not touch them on update. The
        operator's choice of name and type sticks across refreshes.
        Symmetric to the create-vs-reconnect distinction in
        ``create_models_for_hass_device``, which already preserves
        ``name`` on the reconnect path.
        """

        messages = list()
        with transaction.atomic():

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
                # Hard-delete: integration-owned attribute (not
                # user-editable). Soft-delete would surface this
                # in the "Deleted Attributes" section with a
                # restore button, creating an inconsistency
                # against upstream's source of truth.
                attribute.delete( hard_delete = True )
                
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

                # Substates are derived EntityStates of the same
                # HA state; register their keys so the cleanup
                # loop below spares them, and refresh their
                # controller payloads so payload-shape changes
                # propagate to existing records.
                for substate_type in cls._substate_types_for_hass_state( hass_state ):
                    sub_key = cls._substate_integration_key(
                        hass_state = hass_state,
                        entity_state_type = substate_type,
                    )
                    seen_state_integration_keys.add( sub_key )
                    sub_controller = entiity_controllers.get( sub_key )
                    if sub_controller:
                        sub_payload = cls._substate_integration_payload(
                            hass_state = hass_state,
                            substate_type = substate_type,
                        )
                        changed_fields = sub_controller.update_integration_payload( sub_payload )
                        if changed_fields:
                            messages.append(
                                f'Updated payload for substate controller {sub_controller}:'
                                f' {", ".join(changed_fields)}'
                            )
                    continue
                
                sensor = entiity_sensors.get( state_integration_key )
                controller = entiity_controllers.get( state_integration_key )

                # Update integration payload for existing sensors and controllers
                # Every HassState should have at least a sensor, potentially also a controller
                if sensor or controller:
                    # Use sensor or controller to determine EntityStateType (they should be the same)
                    model_with_entity_state = controller if controller else sensor
                    existing_entity_state_type = model_with_entity_state.entity_state.entity_state_type
                    is_controllable = cls._is_controllable_domain_and_type(hass_state.domain, existing_entity_state_type)

                    # Generate new payload using existing logic
                    new_payload = cls._create_service_payload(hass_state, existing_entity_state_type, is_controllable)

                    # Update payload for both sensor and controller if they exist
                    for model, model_type in [(sensor, 'sensor'), (controller, 'controller')]:
                        if model:
                            changed_fields = model.update_integration_payload(new_payload)
                            if changed_fields:
                                messages.append(f'Updated payload for {model_type} {model}: {", ".join(changed_fields)}')

                    # Create any newly-implied substate controllers
                    # (e.g., a bulb that gained color modes since
                    # it was first imported).
                    created = cls._create_substate_controllers(
                        entity = entity,
                        hass_state = hass_state,
                        existing_controllers = entiity_controllers,
                    )
                    for new_controller in created:
                        messages.append( f'Added substate controller {new_controller}' )
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
                ignore_light_state_prefixes.add( HassApi.LIGHT_DOMAIN )

            elif (( hass_state.domain == HassApi.LIGHT_DOMAIN )
                  and ( HassApi.SWITCH_DOMAIN in prefixes_seen )):
                ignore_light_state_prefixes.add( HassApi.LIGHT_DOMAIN )

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

            # Some HA states decompose into multiple HI
            # EntityStates; create the additional substate
            # controllers (currently only light's color attributes
            # — HUE, SATURATION, COLOR_TEMPERATURE).
            cls._create_substate_controllers(
                entity = entity,
                hass_state = hass_state,
            )
            continue
        return

    @classmethod
    def _create_substate_controllers(
            cls,
            entity                : Entity,
            hass_state            : HassState,
            existing_controllers  : Optional[ Dict ] = None,
    ) -> List:
        """Idempotent: creates a controller for each substate
        implied by ``hass_state`` that doesn't already exist.
        ``existing_controllers`` maps integration_key -> Controller
        for the entity's already-known controllers; pass it to
        avoid re-creating substates on re-sync. Returns the list
        of newly-created controllers."""
        substate_types = cls._substate_types_for_hass_state( hass_state )
        if not substate_types:
            return []
        if existing_controllers is None:
            existing_controllers = {}
        base_name = hass_state.friendly_name or entity.name
        created = []
        for substate_type in substate_types:
            substate_integration_key = cls._substate_integration_key(
                hass_state = hass_state,
                entity_state_type = substate_type,
            )
            if substate_integration_key in existing_controllers:
                continue
            controller_name = f'{base_name} {substate_type.label}'
            value_range_str = json.dumps(
                cls._CONTROLLER_STATE_VALUE_RANGES[ substate_type ]
            )
            controller = HiModelHelper.create_controller(
                entity = entity,
                entity_state_type = substate_type,
                name = controller_name,
                integration_key = substate_integration_key,
                value_range_str = value_range_str,
            )
            controller.integration_payload = cls._substate_integration_payload(
                hass_state = hass_state,
                substate_type = substate_type,
            )
            controller.save()
            created.append( controller )
            continue
        return created

    @classmethod
    def _substate_integration_payload(
            cls,
            hass_state    : HassState,
            substate_type : EntityStateType,
    ) -> dict:
        return {
            'domain': hass_state.domain,
            'is_controllable': True,
            'substate': cls._HASS_SUBSTATE_SUFFIXES[ substate_type ],
            'parent_entity_id': hass_state.entity_id,
        }

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
        
        # Create domain payload for service calls - store service routing info directly
        domain_payload = cls._create_service_payload( hass_state, entity_state_type, is_controllable )

        ##########
        # Controllers - Create controller (which also creates sensor) for controllable states
        
        if is_controllable:
            controller = cls._create_controller_from_entity_state_type(
                entity_state_type, entity, integration_key, name, domain_payload
            )
            return controller.entity_state

        ##########
        # Sensors - Create sensor-only for non-controllable states using mapping logic
        
        sensor = cls._create_sensor_from_entity_state_type_with_params(
            entity_state_type, entity, integration_key, name, domain_payload,
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
        appropriate sensor or controller with domain payload storage.
        """
        
        # Step 1: Determine EntityStateType using our mapping table
        entity_state_type = cls._determine_entity_state_type_from_mapping( hass_state )
        
        # Step 2: Create domain payload to store for future service calls
        domain_payload = {
            'domain': hass_state.domain,
            'device_class': hass_state.device_class,
            'has_brightness': cls._has_brightness_capability( hass_state ),
        }
        
        # Step 3: Create IntegrationKey (payload will be stored separately)
        integration_key_for_storage = integration_key
        
        # Step 4: Determine if this should be a controller or sensor
        is_controllable = cls._is_controllable_domain_and_type( hass_state.domain, entity_state_type )
        
        # Step 5: Create appropriate model (controller or sensor)
        name = hass_state.friendly_name or f'{entity.name} ({hass_state.domain})'
        
        if is_controllable:
            # Create controller and store payload
            controller = cls._create_controller_from_entity_state_type(
                entity_state_type, entity, integration_key_for_storage, name, domain_payload
            )
            entity_state = controller.entity_state
        else:
            # Create sensor and store payload  
            sensor = cls._create_sensor_from_entity_state_type(
                entity_state_type, entity, integration_key_for_storage, name, domain_payload
            )
            entity_state = sensor.entity_state
            
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

    # HA color/light modes that imply the light supports a
    # variable brightness level. Used by ``_has_brightness_capability``
    # to recognize a dimmer-capable light from its declared
    # ``supported_color_modes`` even when the live ``brightness``
    # attribute is absent — which HA does when the light is off.
    # Without this, a known dimmer that's currently off would
    # collapse into the on/off path and lose its dimmer state
    # type on every off→on transition.
    _BRIGHTNESS_SUPPORTING_COLOR_MODES = {
        'brightness',
        'color_temp',
        'hs',
        'rgb',
        'rgbw',
        'rgbww',
        'white',
        'xy',
    }

    # Modes whose presence in ``supported_color_modes`` means the
    # light can produce chromatic color (hue/saturation pair, with
    # rgb/xy as alternate representations of the same chromaticity).
    # ``color_temp`` is excluded — it's white-light Kelvin, a
    # separate axis with its own EntityStateType.
    _CHROMATIC_COLOR_MODES = {
        'hs',
        'rgb',
        'rgbw',
        'rgbww',
        'xy',
    }

    # Suffix appended to a HA entity_id to form the integration
    # key for each substate of a one-to-many HA-state-to-HI-state
    # decomposition. The parent (e.g., a light's brightness) keeps
    # the bare entity_id; each substate gets its own suffix.
    _HASS_SUBSTATE_SUFFIXES = {
        EntityStateType.HUE: 'hue',
        EntityStateType.SATURATION: 'saturation',
        EntityStateType.COLOR_TEMPERATURE: 'color_temp',
    }

    # Value ranges for controllers, keyed by EntityStateType.
    # Stored on the EntityState's value_range_str so client-side
    # widgets and any server-side validation share one source of
    # truth.
    _CONTROLLER_STATE_VALUE_RANGES = {
        EntityStateType.HUE: { 'min': 0, 'max': 360 },
        EntityStateType.SATURATION: { 'min': 0, 'max': 100 },
        EntityStateType.COLOR_TEMPERATURE: { 'min': 2000, 'max': 6500 },
    }

    @classmethod
    def _substate_types_for_hass_state(
            cls, hass_state: HassState ) -> List[ EntityStateType ]:
        """Return the color-related EntityStateTypes that a single
        HA ``light.x`` state implies via its ``supported_color_modes``
        declaration. A color bulb that supports HS (or RGB / XY,
        which are alternate representations of HS chromaticity)
        contributes ``HUE`` and ``SATURATION``; one that supports
        ``color_temp`` contributes ``COLOR_TEMPERATURE``. Both
        sets of sub-states can be present simultaneously when
        the bulb supports both modes — HA's ``color_mode``
        attribute then selects which is currently authoritative,
        but HI presents both controls and lets the operator drive
        whichever they want.
        """
        if hass_state.domain != HassApi.LIGHT_DOMAIN:
            return []
        supported = hass_state.attributes.get( 'supported_color_modes' )
        if not isinstance( supported, list ):
            return []

        substate_types = []
        if any( m in cls._CHROMATIC_COLOR_MODES for m in supported ):
            substate_types.append( EntityStateType.HUE )
            substate_types.append( EntityStateType.SATURATION )
        if 'color_temp' in supported:
            substate_types.append( EntityStateType.COLOR_TEMPERATURE )
        return substate_types

    @classmethod
    def _extract_substate_value(
            cls,
            hass_state         : HassState,
            entity_state_type  : EntityStateType,
    ) -> Optional[ str ]:
        """Pull the value for a single color sub-state out of a HA
        light's attributes. Returns ``None`` when the attribute the
        sub-state needs is absent — HA omits color attributes when
        the light is off, and only the attribute matching the
        current ``color_mode`` is authoritative; the other modes'
        attributes may or may not be reported. Callers skip
        ``None``-valued sub-states rather than emitting a stale
        response."""
        attrs = hass_state.attributes

        if entity_state_type == EntityStateType.HUE:
            hs = attrs.get( 'hs_color' )
            if isinstance( hs, list ) and len( hs ) >= 1:
                try:
                    return str( round( float( hs[ 0 ] ) ) )
                except ( TypeError, ValueError ):
                    return None
            return None

        if entity_state_type == EntityStateType.SATURATION:
            hs = attrs.get( 'hs_color' )
            if isinstance( hs, list ) and len( hs ) >= 2:
                try:
                    return str( round( float( hs[ 1 ] ) ) )
                except ( TypeError, ValueError ):
                    return None
            return None

        if entity_state_type == EntityStateType.COLOR_TEMPERATURE:
            kelvin = attrs.get( 'color_temp_kelvin' )
            if kelvin is not None:
                try:
                    return str( int( float( kelvin ) ) )
                except ( TypeError, ValueError ):
                    return None
            return None

        return None

    @classmethod
    def _substate_integration_key(
            cls,
            hass_state         : HassState,
            entity_state_type  : EntityStateType,
    ) -> IntegrationKey:
        """Build the suffix-extended IntegrationKey for a color
        sub-state. The suffix lets the controller dispatch (and
        sensor-update routing) tell which dimension a given key
        targets without parsing supported_color_modes again."""
        suffix = cls._HASS_SUBSTATE_SUFFIXES[ entity_state_type ]
        # ``~`` separator chosen over ``:`` because the latter has
        # special meaning in CSS selectors (pseudo-classes) and
        # in URLs; ``~`` is web-safe in every position and never
        # appears in real HA entity_ids (they're ``[a-z0-9_]+``).
        return IntegrationKey(
            integration_id = HassMetaData.integration_id,
            integration_name = f'{hass_state.entity_id}~{suffix}',
        )

    @classmethod
    def _has_brightness_capability( cls, hass_state: HassState ) -> bool:
        """Check if a light has brightness/dimming capability."""
        if hass_state.domain != HassApi.LIGHT_DOMAIN:
            return False

        attributes = hass_state.attributes
        if 'brightness' in attributes or 'brightness_pct' in attributes:
            return True

        # The brightness attribute is omitted in HA's off-state
        # output even for known-dimmable lights; consult the
        # capability declaration in ``supported_color_modes`` so
        # the dimmer path keeps firing across on/off transitions.
        supported_color_modes = attributes.get('supported_color_modes')
        if isinstance(supported_color_modes, list):
            for mode in supported_color_modes:
                if mode in cls._BRIGHTNESS_SUPPORTING_COLOR_MODES:
                    return True
        return False

    @classmethod
    def _is_controllable_domain_and_type( cls, domain: str, entity_state_type: EntityStateType ) -> bool:
        """Check if this domain+type combination is controllable"""
        return (domain, entity_state_type) in cls.CONTROL_SERVICE_MAPPING

    @classmethod  
    def _create_controller_from_entity_state_type(
            cls,
            entity_state_type : EntityStateType, 
            entity            : Entity,
            integration_key   : IntegrationKey, 
            name              : str,
            domain_payload    : dict ):
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
        else:
            # Fallback - shouldn't happen for controllable types
            logger.warning( f'Unknown controllable EntityStateType: {entity_state_type}' )
            controller = HiModelHelper.create_on_off_controller(
                entity = entity,
                integration_key = integration_key,
                name = name,
            )
        
        # Store domain payload
        controller.integration_payload = domain_payload
        controller.save()
        return controller

    @classmethod  
    def _create_sensor_from_entity_state_type( cls,
                                               entity_state_type : EntityStateType, 
                                               entity            : Entity,
                                               integration_key   : IntegrationKey, 
                                               name              : str,
                                               domain_payload    : dict ):
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
        elif entity_state_type == EntityStateType.MULTIVALUED:
            sensor = HiModelHelper.create_multivalued_sensor(
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
        
        # Store domain payload for sensors too
        sensor.integration_payload = domain_payload
        sensor.save()
        return sensor
    
    @classmethod
    def _create_sensor_from_entity_state_type_with_params( cls,
                                                           entity_state_type : EntityStateType, 
                                                           entity            : Entity,
                                                           integration_key   : IntegrationKey, 
                                                           name              : str,
                                                           domain_payload   : dict,
                                                           hass_state        : HassState,
                                                           add_alarm_events  : bool ):
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
        elif entity_state_type == EntityStateType.MULTIVALUED:
            sensor = HiModelHelper.create_multivalued_sensor(
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
        
        # Store domain payload for sensors
        sensor.integration_payload = domain_payload
        sensor.save()
        return sensor
    
    @classmethod
    def _create_service_payload( cls, hass_state: HassState, entity_state_type: EntityStateType, is_controllable: bool ) -> dict:
        """Create payload with service routing information for controllers"""
        
        # Base payload for all entities
        payload = {
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
                payload.update(service_mapping)
            
            # Add special capabilities
            if entity_state_type == EntityStateType.LIGHT_DIMMER:
                payload['supports_brightness'] = True
                has_brightness = cls._has_brightness_capability( hass_state )
                payload['has_brightness'] = has_brightness
            else:
                payload['supports_brightness'] = False
                payload['has_brightness'] = False
        
        return payload

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
        
    # Word-boundary patterns matched against the device's display
    # name to upgrade a switch-domain device's EntityType at import
    # time when the name reveals what the switch is wired to. Word
    # boundaries guard against substring collisions (e.g.
    # "Lighthouse", "Lightning" don't match the bare "light"
    # keyword). Each regex is paired with the EntityType it implies
    # in ``_NAME_INFERENCE_RULES`` below.
    _OUTLET_NAME_PATTERN = re.compile(
        r'\b(plug|plugs|outlet|outlets|receptacle|receptacles)\b',
        re.IGNORECASE,
    )
    _FAN_NAME_PATTERN = re.compile(
        r'\b(fan|fans)\b',
        re.IGNORECASE,
    )
    _LIGHT_NAME_PATTERN = re.compile(
        r'\b(light|lights|lighting'
        r'|lamp|lamps|bulb|bulbs|led|sconce|chandelier'
        r'|pendant|spotlight|floodlight|lantern)\b',
        re.IGNORECASE,
    )

    @classmethod
    def _device_name_to_inferred_type(
            cls, hass_device : HassDevice ) -> Optional[EntityType]:
        """Heuristic mapping for a switch-domain device whose name
        reveals what it's connected to. Order encodes precedence:
        outlet/plug keywords are most specific (a "Smart Plug" is
        almost always wanted as ELECTRICAL_OUTLET), fan next, light
        last. Returns None when no rule matches; the caller falls
        through to the generic ON_OFF_SWITCH for switch-domain
        devices. False positives cost one manual edit which now
        sticks across refreshes."""
        name = cls.hass_device_to_entity_name( hass_device )
        if not name:
            return None
        if cls._OUTLET_NAME_PATTERN.search( name ):
            return EntityType.ELECTRICAL_OUTLET
        if cls._FAN_NAME_PATTERN.search( name ):
            return EntityType.CEILING_FAN
        if cls._LIGHT_NAME_PATTERN.search( name ):
            return EntityType.LIGHT
        return None

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
        # Outlet device class wins over the switch-domain branch
        # below — an HA switch.x with device_class=outlet is
        # specifically an electrical outlet, not a wall switch.
        if HassApi.OUTLET_DEVICE_CLASS in device_class_set:
            return EntityType.ELECTRICAL_OUTLET
        # For a generic switch.x device, the name often reveals
        # what the switch is wired to (Kitchen Light, Smart Plug,
        # Ceiling Fan); the heuristic upgrades the type at import
        # time when a clear match is present, falling through to
        # the catch-all ON_OFF_SWITCH otherwise.
        if HassApi.SWITCH_DOMAIN in domain_set:
            inferred = cls._device_name_to_inferred_type( hass_device )
            if inferred is not None:
                return inferred
            return EntityType.ON_OFF_SWITCH
        if HassApi.LOCK_DOMAIN in domain_set:
            return EntityType.DOOR_LOCK
        # HA covers are doors / windows / garage doors / blinds /
        # awnings / etc. Without a device-class refinement that maps
        # cleanly to HI's specific types, OPEN_CLOSE_SENSOR is the
        # least-wrong default; the operator can change it post-import
        # to DOOR / WINDOW / GARAGE_DOOR if appropriate.
        if HassApi.COVER_DOMAIN in domain_set:
            return EntityType.OPEN_CLOSE_SENSOR
        # Fan domain has no HA-side device class to distinguish
        # ceiling vs exhaust; CEILING_FAN is the more common case.
        if HassApi.FAN_DOMAIN in domain_set:
            return EntityType.CEILING_FAN
        # Climate domain is the controllable HVAC entity; the
        # temperature device-class check below catches passive
        # temperature sensors that aren't climate entities.
        if HassApi.CLIMATE_DOMAIN in domain_set:
            return EntityType.THERMOSTAT
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
    def hass_state_to_sensor_value_map(
            cls, hass_state : HassState ) -> Dict[ IntegrationKey, str ]:
        """All HI sensor values produced by a single HA state,
        keyed by the integration_key of the HI EntityState the
        value targets. A simple HA state contributes a single
        entry; a color-capable light decomposes into brightness
        plus hue, saturation, and color temperature entries.
        Domain-specific value extraction lives in the per-domain
        helpers this method dispatches to."""
        domain = hass_state.domain
        if domain == HassApi.LIGHT_DOMAIN:
            return cls._light_to_sensor_value_map( hass_state )
        if domain == HassApi.BINARY_SENSOR_DOMAIN:
            return cls._binary_sensor_to_sensor_value_map( hass_state )
        return cls._passthrough_to_sensor_value_map( hass_state )

    @classmethod
    def _light_to_sensor_value_map(
            cls, hass_state : HassState ) -> Dict[ IntegrationKey, str ]:
        if cls._has_brightness_capability( hass_state ):
            return cls._dimmer_light_to_sensor_value_map( hass_state )
        return cls._on_off_light_to_sensor_value_map( hass_state )

    @classmethod
    def _dimmer_light_to_sensor_value_map(
            cls, hass_state : HassState ) -> Dict[ IntegrationKey, str ]:
        """Brightness percentage plus any color sub-state values
        (hue, saturation, color temperature) implied by the HA
        light's ``supported_color_modes``. Each value targets a
        distinct HI EntityState."""
        result : Dict[ IntegrationKey, str ] = {}
        brightness_value = cls._dimmer_brightness_value( hass_state )
        if brightness_value:
            result[ cls.hass_state_to_integration_key( hass_state ) ] = brightness_value
        for substate_type in cls._substate_types_for_hass_state( hass_state ):
            value = cls._extract_substate_value( hass_state, substate_type )
            if value is None:
                continue
            substate_key = cls._substate_integration_key(
                hass_state = hass_state,
                entity_state_type = substate_type,
            )
            result[ substate_key ] = value
            continue
        return result

    @classmethod
    def _dimmer_brightness_value( cls, hass_state : HassState ) -> Optional[ str ]:
        """0-100 percentage for the LIGHT_DIMMER state. HA reports
        ``brightness`` as 1-255 when on, and omits the attribute
        when the light is off (state='off' carries the level)."""
        sv = hass_state.state_value.lower()
        if sv == HassStateValue.OFF:
            return "0"
        if sv == HassStateValue.ON:
            brightness = hass_state.attributes.get( 'brightness' )
            if brightness is None:
                return "100"
            try:
                return str( round( ( float( brightness ) / 255.0 ) * 100 ) )
            except ( ValueError, TypeError ):
                return "100"
        return hass_state.state_value

    @classmethod
    def _on_off_light_to_sensor_value_map(
            cls, hass_state : HassState ) -> Dict[ IntegrationKey, str ]:
        sv = hass_state.state_value.lower()
        if sv == HassStateValue.ON:
            value = str( EntityStateValue.ON )
        elif sv == HassStateValue.OFF:
            value = str( EntityStateValue.OFF )
        else:
            value = hass_state.state_value
        if not value:
            return {}
        return { cls.hass_state_to_integration_key( hass_state ) : value }

    @classmethod
    def _binary_sensor_to_sensor_value_map(
            cls, hass_state : HassState ) -> Dict[ IntegrationKey, str ]:
        value = cls._binary_sensor_value( hass_state )
        if value is None:
            return {}
        return { cls.hass_state_to_integration_key( hass_state ) : value }

    @classmethod
    def _binary_sensor_value( cls, hass_state : HassState ) -> Optional[ str ]:
        """Translate HA binary state (on/off) plus device_class to
        the matching HI EntityStateValue: ACTIVE/IDLE for motion,
        OPEN/CLOSED for doors and peers, CONNECTED/DISCONNECTED
        for connectivity, LOW/HIGH for battery."""
        sv = hass_state.state_value.lower()
        dc = hass_state.device_class
        if sv == HassStateValue.ON:
            if dc == HassApi.MOTION_DEVICE_CLASS:
                return str( EntityStateValue.ACTIVE )
            if dc == HassApi.BATTERY_DEVICE_CLASS:
                return str( EntityStateValue.LOW )
            if dc in HassApi.OPEN_CLOSE_DEVICE_CLASS_SET:
                return str( EntityStateValue.OPEN )
            if dc == HassApi.CONNECTIVITY_DEVICE_CLASS:
                return str( EntityStateValue.CONNECTED )
            return str( EntityStateValue.ON )
        if sv == HassStateValue.OFF:
            if dc == HassApi.MOTION_DEVICE_CLASS:
                return str( EntityStateValue.IDLE )
            if dc == HassApi.BATTERY_DEVICE_CLASS:
                return str( EntityStateValue.HIGH )
            if dc in HassApi.OPEN_CLOSE_DEVICE_CLASS_SET:
                return str( EntityStateValue.CLOSED )
            if dc == HassApi.CONNECTIVITY_DEVICE_CLASS:
                return str( EntityStateValue.DISCONNECTED )
            return str( EntityStateValue.OFF )
        logger.warning( f'Unknown HAss binary state value "{hass_state.state_value}".' )
        return None

    @classmethod
    def _passthrough_to_sensor_value_map(
            cls, hass_state : HassState ) -> Dict[ IntegrationKey, str ]:
        """Domains and device classes whose HA state value passes
        through unchanged: sun, weather, sensor temperature /
        humidity / timestamp / enum, and any unrecognized HA
        state shape."""
        value = hass_state.state_value
        if value is None:
            return {}
        return { cls.hass_state_to_integration_key( hass_state ) : value }

    @classmethod
    def hass_entity_id_to_state_value_str( cls,
                                           hass_entity_id  : str,
                                           hi_control_value        : str) -> str:
        if hi_control_value is None:
            return HassStateValue.OFF
        if hi_control_value.lower() in [ str(EntityStateValue.OPEN), str(EntityStateValue.ON) ]:
            return HassStateValue.ON
        if hi_control_value.lower() in [ str(EntityStateValue.CLOSED), str(EntityStateValue.OFF) ]:
            return HassStateValue.OFF
        return hi_control_value

    # ------------------------------------------------------------------
    # HI control value -> HA service call composition
    #
    # Inverse direction of ``hass_state_to_sensor_value_map``: given a
    # HI control value targeting one HA substate, produce the HA
    # service call to invoke. Bridge methods here parse HI values
    # and orchestrate; pure HA-side composition lives in
    # ``HassServiceComposer``.
    # ------------------------------------------------------------------

    @classmethod
    def to_ha_numeric_parameter_value( cls, hi_control_value : str ) -> float:
        """Identity-valued boundary marker: parses an HI numeric
        control value into the float HA expects. Today the value
        passes through unchanged; the named conversion documents
        the namespace transition and gives a single point to
        introduce real conversion if HI's units later diverge from
        HA's."""
        return float( hi_control_value )

    @classmethod
    def to_ha_on_off_intent( cls, hi_control_value : str ) -> str:
        """Normalize an HI on/off-style control value to a
        canonical HA-side intent: ``'on'`` / ``'off'`` /
        ``'open'`` / ``'close'``. ``HassServiceComposer`` maps the
        intent + domain to the right HA service name."""
        lower = hi_control_value.lower()
        if lower in ( 'on', 'true', '1' ):
            return 'on'
        if lower in ( 'off', 'false', '0' ):
            return 'off'
        if lower == 'open':
            return 'open'
        if lower == 'close':
            return 'close'
        raise ValueError( f'Unknown control value: {hi_control_value}' )

    @classmethod
    def hi_value_to_hass_service_call(
            cls,
            hass_substate_id : str,
            hi_control_value : str,
            domain_payload   : dict,
    ) -> HassServiceCall:
        """Compose the HA service call for a HI control value
        targeting one HA substate. Raises ValueError when the
        inputs cannot be resolved to a valid call."""
        if domain_payload and domain_payload.get( 'substate' ):
            return cls._substate_service_call(
                hi_control_value = hi_control_value,
                domain_payload = domain_payload,
            )

        domain = domain_payload.get( 'domain' ) if domain_payload else None
        if not domain:
            if '.' not in hass_substate_id:
                raise ValueError( f'Invalid entity_id format: {hass_substate_id}' )
            domain = hass_substate_id.split( '.', 1 )[ 0 ]
            logger.warning( f'Missing domain payload for {hass_substate_id},'
                            f' using parsed domain: {domain}' )

        if domain_payload:
            return cls._payload_driven_service_call(
                domain = domain,
                hass_substate_id = hass_substate_id,
                hi_control_value = hi_control_value,
                domain_payload = domain_payload,
            )
        return cls._best_effort_service_call(
            domain = domain,
            hass_substate_id = hass_substate_id,
            hi_control_value = hi_control_value,
        )

    @classmethod
    def _substate_service_call(
            cls,
            hi_control_value : str,
            domain_payload   : dict,
    ) -> HassServiceCall:
        substate = domain_payload[ 'substate' ]
        parent_entity_id = domain_payload[ 'parent_entity_id' ]
        domain = domain_payload[ 'domain' ]

        if substate == 'color_temp':
            try:
                kelvin = int( round( cls.to_ha_numeric_parameter_value( hi_control_value ) ) )
            except ( ValueError, TypeError ):
                raise ValueError(
                    f'Invalid color_temp value: {hi_control_value}'
                )
            return HassServiceComposer.for_color_temp(
                domain = domain,
                parent_entity_id = parent_entity_id,
                kelvin = kelvin,
            )

        if substate in ( 'hue', 'saturation' ):
            try:
                changed_value = cls.to_ha_numeric_parameter_value( hi_control_value )
            except ( ValueError, TypeError ):
                raise ValueError(
                    f'Invalid {substate} value: {hi_control_value}'
                )
            partner_substate = 'saturation' if substate == 'hue' else 'hue'
            partner_int_key = IntegrationKey(
                integration_id = HassMetaData.integration_id,
                integration_name = f'{parent_entity_id}~{partner_substate}',
            )
            partner_value_str = cls.get_latest_state_values(
                integration_keys = [ partner_int_key ],
            ).get( partner_int_key )
            try:
                partner_value = (
                    float( partner_value_str ) if partner_value_str is not None else None
                )
            except ( ValueError, TypeError ):
                partner_value = None
            # Defaults when the partner has no cached value yet (e.g.,
            # before the first poll cycle): saturation=100 keeps the
            # color visible while hue is being chosen; hue=0 is an
            # arbitrary fallback whose effect is irrelevant when
            # saturation=0 and small when saturation is being set
            # for the first time.
            if substate == 'hue':
                hue = changed_value
                sat = partner_value if partner_value is not None else 100.0
            else:
                hue = partner_value if partner_value is not None else 0.0
                sat = changed_value
            return HassServiceComposer.for_hs_color(
                domain = domain,
                parent_entity_id = parent_entity_id,
                hue = hue,
                saturation = sat,
            )

        raise ValueError( f'Unknown substate: {substate}' )

    @classmethod
    def _payload_driven_service_call(
            cls,
            domain           : str,
            hass_substate_id : str,
            hi_control_value : str,
            domain_payload   : dict,
    ) -> HassServiceCall:
        if not domain_payload.get( 'is_controllable', False ):
            return cls._best_effort_service_call(
                domain = domain,
                hass_substate_id = hass_substate_id,
                hi_control_value = hi_control_value,
            )

        if cls._is_numeric_control( hi_control_value, domain_payload ):
            numeric_value = cls.to_ha_numeric_parameter_value( hi_control_value )
            return HassServiceComposer.for_numeric_parameter(
                domain = domain,
                hass_substate_id = hass_substate_id,
                numeric_value = numeric_value,
                domain_payload = domain_payload,
            )

        intent = cls.to_ha_on_off_intent( hi_control_value )
        result = HassServiceComposer.for_payload_intent(
            domain = domain,
            hass_substate_id = hass_substate_id,
            intent = intent,
            domain_payload = domain_payload,
        )
        if result is None:
            return cls._best_effort_service_call(
                domain = domain,
                hass_substate_id = hass_substate_id,
                hi_control_value = hi_control_value,
            )
        return result

    @classmethod
    def _best_effort_service_call(
            cls,
            domain           : str,
            hass_substate_id : str,
            hi_control_value : str,
    ) -> HassServiceCall:
        if cls._is_numeric_value( hi_control_value ):
            numeric_value = cls.to_ha_numeric_parameter_value( hi_control_value )
            return HassServiceComposer.for_numeric_best_effort(
                domain = domain,
                hass_substate_id = hass_substate_id,
                numeric_value = numeric_value,
            )
        intent = cls.to_ha_on_off_intent( hi_control_value )
        return HassServiceComposer.for_on_off_best_effort(
            domain = domain,
            hass_substate_id = hass_substate_id,
            intent = intent,
        )

    @classmethod
    def _is_numeric_value( cls, hi_control_value : str ) -> bool:
        try:
            float( hi_control_value )
            return True
        except ( ValueError, TypeError ):
            return False

    @classmethod
    def _is_numeric_control( cls, hi_control_value : str, domain_payload : dict ) -> bool:
        if not cls._is_numeric_value( hi_control_value ):
            return False
        return ( domain_payload.get( 'supports_brightness', False )
                 or domain_payload.get( 'set_service' ) is not None )
