import json
import logging
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

from django.db import transaction

from hi.apps.attribute.enums import (
    AttributeType,
    AttributeValueType,
)
from hi.apps.entity.enums import (
    EntityStateRole,
    EntityStateType,
    EntityType,
    EntityStateValue,
    HumidityUnit,
)
from hi.apps.entity.models import Entity, EntityAttribute, EntityState
from hi.apps.model_helper import HiModelHelper

from hi.integrations.integration_converter_helper import IntegrationConverterHelper
from hi.integrations.transient_models import IntegrationKey
from hi.units import CANONICAL_TEMPERATURE_UNIT

from .enums import HassStateValue
from .hass_metadata import HassMetaData
from .hass_models import HassApi, HassServiceCall, HassState, HassDevice
from .hass_service_composer import ControlIntent, HassServiceComposer

logger = logging.getLogger(__name__)


class HassConverter:
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
        HassApi.ILLUMINANCE_ID_SUFFIX,
        HassApi.LIGHT_ID_SUFFIX,
        HassApi.MOISTURE_ID_SUFFIX,
        HassApi.MOTION_ID_SUFFIX,
        HassApi.OCCUPANCY_ID_SUFFIX,
        HassApi.PRESSURE_ID_SUFFIX,
        HassApi.STATE_ID_SUFFIX,
        HassApi.STATUS_ID_SUFFIX,
        HassApi.TEMPERATURE_ID_SUFFIX,
        HassApi.WIND_SPEED_ID_SUFFIX,

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
    
    # Domains for sensor-only devices (read-only). The camera domain
    # is intentionally NOT here despite its primary state being
    # read-only: its ``motion_detection`` substate is controllable, so
    # the domain as a whole is not purely sensor-only.
    #
    SENSOR_ONLY_DOMAINS = {
        HassApi.BINARY_SENSOR_DOMAIN,
        HassApi.SENSOR_DOMAIN,
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
        
        # Cover Domain (blinds, curtains, garage doors). Covers
        # that report ``current_position`` are routed to
        # OPEN_CLOSE_POSITION (continuous slider) by the lookup
        # logic, not via this table — these entries cover only
        # the discrete open/close case.
        (HassApi.COVER_DOMAIN, HassApi.DOOR_DEVICE_CLASS, None): EntityStateType.OPEN_CLOSE,
        (HassApi.COVER_DOMAIN, HassApi.GARAGE_DEVICE_CLASS, None): EntityStateType.OPEN_CLOSE,
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
        (HassApi.BINARY_SENSOR_DOMAIN, HassApi.OCCUPANCY_DEVICE_CLASS, None): EntityStateType.MOVEMENT,
        (HassApi.BINARY_SENSOR_DOMAIN, HassApi.PRESENCE_DEVICE_CLASS, None): EntityStateType.PRESENCE,
        (HassApi.BINARY_SENSOR_DOMAIN, HassApi.CONNECTIVITY_DEVICE_CLASS, None): EntityStateType.CONNECTIVITY,
        (HassApi.BINARY_SENSOR_DOMAIN, HassApi.BATTERY_DEVICE_CLASS, None): EntityStateType.HIGH_LOW,
        (HassApi.BINARY_SENSOR_DOMAIN, HassApi.DOOR_DEVICE_CLASS, None): EntityStateType.OPEN_CLOSE,
        (HassApi.BINARY_SENSOR_DOMAIN, HassApi.GARAGE_DOOR_DEVICE_CLASS, None): EntityStateType.OPEN_CLOSE,
        (HassApi.BINARY_SENSOR_DOMAIN, HassApi.OPENING_DEVICE_CLASS, None): EntityStateType.OPEN_CLOSE,
        (HassApi.BINARY_SENSOR_DOMAIN, HassApi.WINDOW_DEVICE_CLASS, None): EntityStateType.OPEN_CLOSE,
        (HassApi.BINARY_SENSOR_DOMAIN, HassApi.SMOKE_DEVICE_CLASS, None): EntityStateType.SMOKE,
        (HassApi.BINARY_SENSOR_DOMAIN, HassApi.MOISTURE_DEVICE_CLASS, None): EntityStateType.MOISTURE,
        (HassApi.BINARY_SENSOR_DOMAIN, HassApi.CARBON_MONOXIDE_DEVICE_CLASS, None): EntityStateType.CO,
        (HassApi.BINARY_SENSOR_DOMAIN, HassApi.GAS_DEVICE_CLASS, None): EntityStateType.GAS,
        (HassApi.BINARY_SENSOR_DOMAIN, None, None): EntityStateType.ON_OFF,  # Generic binary sensor
        
        # Sensor Domain (read-only sensors)
        (HassApi.SENSOR_DOMAIN, HassApi.TEMPERATURE_DEVICE_CLASS, None): EntityStateType.TEMPERATURE,
        (HassApi.SENSOR_DOMAIN, HassApi.HUMIDITY_DEVICE_CLASS, None): EntityStateType.HUMIDITY,
        (HassApi.SENSOR_DOMAIN, HassApi.BATTERY_DEVICE_CLASS, None): EntityStateType.BATTERY_LEVEL,
        (HassApi.SENSOR_DOMAIN, HassApi.ILLUMINANCE_DEVICE_CLASS, None): EntityStateType.LIGHT_LEVEL,
        (HassApi.SENSOR_DOMAIN, HassApi.POWER_DEVICE_CLASS, None): EntityStateType.ELECTRIC_USAGE,
        (HassApi.SENSOR_DOMAIN, HassApi.PRESSURE_DEVICE_CLASS, None): EntityStateType.AIR_PRESSURE,
        (HassApi.SENSOR_DOMAIN, HassApi.WIND_SPEED_DEVICE_CLASS, None): EntityStateType.WIND_SPEED,
        (HassApi.SENSOR_DOMAIN, HassApi.TIMESTAMP_DEVICE_CLASS, None): EntityStateType.DATETIME,
        (HassApi.SENSOR_DOMAIN, HassApi.ENUM_DEVICE_CLASS, None): EntityStateType.DISCRETE,
        (HassApi.SENSOR_DOMAIN, None, None): EntityStateType.BLOB,  # Generic sensor
        
        # Other domains (read-only)
        # Note: CAMERA_DOMAIN entities expose video_snapshot capability
        # via has_video_snapshot (set during _create_or_reconnect_entity),
        # not via an EntityStateType here. They have no native video
        # stream so has_event_video_clip stays False.
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
                HassApi.BRIGHTNESS_PCT_PARAM: 'percentage',  # 0-100
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
                HassApi.POSITION_PARAM: 'percentage',  # 0-100
            },
        },
        (HassApi.COVER_DOMAIN, EntityStateType.OPEN_CLOSE_POSITION): {
            'on_service': HassApi.OPEN_COVER_SERVICE,
            'off_service': HassApi.CLOSE_COVER_SERVICE,
            'set_service': HassApi.SET_COVER_POSITION_SERVICE,
            'parameters': {
                HassApi.POSITION_PARAM: 'percentage',  # 0-100
            },
        },
        
        # Fan Domain Services
        (HassApi.FAN_DOMAIN, EntityStateType.ON_OFF): {
            'on_service': HassApi.TURN_ON_SERVICE,
            'off_service': HassApi.TURN_OFF_SERVICE,
            'set_service': HassApi.SET_PERCENTAGE_SERVICE,
            'parameters': {
                HassApi.PERCENTAGE_ATTR: 'percentage',  # 0-100
            },
        },
        (HassApi.FAN_DOMAIN, EntityStateType.POWER_LEVEL): {
            'on_service': HassApi.TURN_ON_SERVICE,
            'off_service': HassApi.TURN_OFF_SERVICE,
            'set_service': HassApi.SET_PERCENTAGE_SERVICE,
            'parameters': {
                HassApi.PERCENTAGE_ATTR: 'percentage',  # 0-100
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
                HassApi.VOLUME_LEVEL_PARAM: 'percentage_decimal',  # 0.0-1.0
            },
        },

        # Camera Domain Services — the camera's own primary state is
        # read-only (no entry in HASS_STATE_TO_ENTITY_STATE_TYPE_MAPPING
        # for the CAMERA_DOMAIN); the only controllable surface is the
        # ``motion_detection`` substate, dispatched via the ``substate``
        # branch in ``_substate_service_call`` rather than the
        # bare-key on/off path. The mapping below populates the
        # substate controller's payload so the dispatch finds the
        # right enable/disable services.
        (HassApi.CAMERA_DOMAIN, EntityStateType.ON_OFF): {
            'on_service': HassApi.ENABLE_MOTION_DETECTION_SERVICE,
            'off_service': HassApi.DISABLE_MOTION_DETECTION_SERVICE,
            'parameters': {},
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
            is_camera = HassApi.CAMERA_DOMAIN in hass_device.domain_set
            entity.integration_key = entity_integration_key
            entity.can_user_delete = HassMetaData.allow_entity_deletion
            entity.has_video_snapshot = is_camera
            entity.video_snapshot_stream_fps = 1.0 if is_camera else None
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
        in HI's UI on HASS entities (``allow_internal_attributes``
        defaults to True), so they're treated as user-owned after
        creation: this method does not touch them on update. The
        operator's choice of name and type sticks across refreshes.
        Symmetric to the create-vs-reconnect distinction in
        ``create_models_for_hass_device``, which already preserves
        ``name`` on the reconnect path.
        """

        messages = list()
        with transaction.atomic():

            # Re-derive integration-owned capability flags from the
            # current upstream device shape. Self-healing if HA's
            # domain composition changes (e.g., a paired motion sensor
            # added or removed).
            is_camera = HassApi.CAMERA_DOMAIN in hass_device.domain_set
            expected_fps = 1.0 if is_camera else None
            update_fields = []
            if entity.has_video_snapshot != is_camera:
                entity.has_video_snapshot = is_camera
                update_fields.append( 'has_video_snapshot' )
            if entity.video_snapshot_stream_fps != expected_fps:
                entity.video_snapshot_stream_fps = expected_fps
                update_fields.append( 'video_snapshot_stream_fps' )
            if update_fields:
                entity.save( update_fields = update_fields )

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
                any_existing_substate = False
                for state_spec in cls._state_specs_for_hass_state( hass_state ):
                    sub_key = cls._substate_integration_key(
                        hass_state = hass_state,
                        suffix = state_spec.suffix,
                    )
                    seen_state_integration_keys.add( sub_key )
                    sub_controller = entiity_controllers.get( sub_key )
                    sub_sensor = entiity_sensors.get( sub_key )
                    if sub_controller or sub_sensor:
                        any_existing_substate = True
                    if sub_controller:
                        sub_payload = cls._substate_integration_payload(
                            hass_state = hass_state,
                            spec = state_spec,
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

                # For multi-substate lights, no model lives at
                # the bare key — match on existing substates so
                # we don't fall through to the "missing" branch
                # and re-create what's already there.
                if sensor or controller or any_existing_substate:
                    if sensor or controller:
                        # Refresh the parent (bare-key) payload —
                        # only relevant for single-state HA entities;
                        # multi-substate lights have no parent model.
                        model_with_entity_state = controller if controller else sensor
                        existing_entity_state_type = model_with_entity_state.entity_state.entity_state_type
                        is_controllable = cls._is_controllable_domain_and_type(
                            hass_state.domain,
                            existing_entity_state_type,
                        )
                        new_payload = cls._create_service_payload(
                            hass_state,
                            existing_entity_state_type,
                            is_controllable,
                        )
                        for model, model_type in [(sensor, 'sensor'), (controller, 'controller')]:
                            if model:
                                changed_fields = model.update_integration_payload(new_payload)
                                if changed_fields:
                                    messages.append(f'Updated payload for {model_type} {model}: {", ".join(changed_fields)}')

                    # Create any newly-implied substate models
                    # (e.g., a bulb that gained color modes since
                    # it was first imported).
                    created = cls._create_substate_models(
                        entity = entity,
                        hass_state = hass_state,
                        existing_controllers = entiity_controllers,
                        existing_sensors = entiity_sensors,
                    )
                    for new_model in created:
                        messages.append( f'Added substate model {new_model}' )
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

            state_specs = cls._state_specs_for_hass_state( hass_state )
            if state_specs:
                # Multi-substate decomposition: ALL EntityStates
                # are created as peer substates (no asymmetric
                # bare-key parent). The Entity itself is still
                # identified by the bare HA entity_id; only the
                # EntityStates use suffixed integration_keys.
                cls._create_substate_models(
                    entity = entity,
                    hass_state = hass_state,
                )
            else:
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
    def _create_substate_models(
            cls,
            entity                : Entity,
            hass_state            : HassState,
            existing_controllers  : Optional[ Dict ] = None,
            existing_sensors      : Optional[ Dict ] = None,
    ) -> List:
        """Idempotent: creates a Controller (for controllable
        substates) or a Sensor (for read-only ones) for each
        substate implied by ``hass_state`` that doesn't already
        exist. Pass the entity's existing
        ``Controller``/``Sensor`` maps so re-sync avoids
        re-creation. Returns the list of newly-created models."""
        specs = cls._state_specs_for_hass_state( hass_state )
        if not specs:
            return []
        if existing_controllers is None:
            existing_controllers = {}
        if existing_sensors is None:
            existing_sensors = {}
        base_name = hass_state.friendly_name or entity.name
        created = []
        for spec in specs:
            substate_integration_key = cls._substate_integration_key(
                hass_state = hass_state,
                suffix = spec.suffix,
            )
            existing_for_kind = (
                existing_controllers if spec.is_controllable else existing_sensors
            )
            if substate_integration_key in existing_for_kind:
                continue
            record_name = f'{base_name} {spec.display_label}'
            value_range_str = (
                json.dumps( spec.value_range ) if spec.value_range else ''
            )
            if spec.is_controllable:
                controller = HiModelHelper.create_controller(
                    entity = entity,
                    entity_state_type = spec.entity_state_type,
                    name = record_name,
                    integration_key = substate_integration_key,
                    value_range_str = value_range_str,
                    units = spec.units,
                    entity_state_role = spec.role,
                )
                controller.integration_payload = cls._substate_integration_payload(
                    hass_state = hass_state,
                    spec = spec,
                )
                controller.save()
                created.append( controller )
            else:
                sensor = HiModelHelper.create_sensor(
                    entity = entity,
                    entity_state_type = spec.entity_state_type,
                    name = record_name,
                    integration_key = substate_integration_key,
                    value_range_str = value_range_str,
                    units = spec.units,
                    entity_state_role = spec.role,
                )
                created.append( sensor )
            continue
        return created

    @classmethod
    def _substate_integration_payload(
            cls,
            hass_state : HassState,
            spec       : '_StateSpec',
    ) -> dict:
        payload = {
            'domain': hass_state.domain,
            'is_controllable': spec.is_controllable,
            'substate': spec.suffix,
            'parent_entity_id': hass_state.entity_id,
        }
        # Climate temperature substates carry HA's currently reported
        # native unit so dispatch can convert from the EntityState's
        # stored unit without fetching the live HA state on every
        # service call. The HI-side unit is read from the
        # IntegrationMetadataCache (keyed by IntegrationKey) instead of
        # being duplicated in the payload.
        if (
            hass_state.domain == HassApi.CLIMATE_DOMAIN
            and spec.entity_state_type == EntityStateType.TEMPERATURE
        ):
            payload[ 'native_temperature_unit' ] = (
                hass_state.attributes.get( HassApi.TEMPERATURE_UNIT_ATTR )
            )
        return payload

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

        # Position-aware override for covers: a cover that
        # reports ``current_position`` is structurally a
        # continuous slider (closed at 0, open above) — like a
        # dimmer, not a binary toggle. Skip the discrete
        # open/close mapping and use the continuous type.
        if domain == HassApi.COVER_DOMAIN and cls._has_position_capability( hass_state ):
            return EntityStateType.OPEN_CLOSE_POSITION

        # Speed-aware override for fans: a fan that reports
        # ``percentage`` (and only ``percentage`` — not the
        # multi-feature attributes that trigger substate
        # decomposition) is a single continuous slider.
        if ( domain == HassApi.FAN_DOMAIN
             and cls._has_percentage_capability( hass_state )
             and not cls._fan_has_multi_features( hass_state ) ):
            return EntityStateType.POWER_LEVEL

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
        HassApi.COLOR_MODE_BRIGHTNESS,
        HassApi.COLOR_MODE_COLOR_TEMP,
        HassApi.COLOR_MODE_HS,
        HassApi.COLOR_MODE_RGB,
        HassApi.COLOR_MODE_RGBW,
        HassApi.COLOR_MODE_RGBWW,
        HassApi.COLOR_MODE_WHITE,
        HassApi.COLOR_MODE_XY,
    }

    # Modes whose presence in ``supported_color_modes`` means the
    # light can produce chromatic color (hue/saturation pair, with
    # rgb/xy as alternate representations of the same chromaticity).
    # ``color_temp`` is excluded — it's white-light Kelvin, a
    # separate axis with its own EntityStateType.
    _CHROMATIC_COLOR_MODES = {
        HassApi.COLOR_MODE_HS,
        HassApi.COLOR_MODE_RGB,
        HassApi.COLOR_MODE_RGBW,
        HassApi.COLOR_MODE_RGBWW,
        HassApi.COLOR_MODE_XY,
    }

    # Per-substate metadata. The suffix is appended to the parent
    # HA entity_id to form the substate's integration_key (parent
    # keeps the bare entity_id; each substate gets its own
    # suffix). ``entity_state_type`` selects the HI controller
    # affordance. ``is_controllable`` selects Sensor-only vs
    # Sensor+Controller creation. ``value_range`` is stored on
    # the EntityState's value_range_str so client widgets and
    # any server-side validation share one source of truth;
    # ``None`` for substates whose value space comes from their
    # EntityStateType's enum choices instead (e.g., COLOR_MODE).
    # ``label`` overrides ``entity_state_type.label`` when the
    # generic type label is too generic for the per-domain
    # context (e.g., "Speed" for a fan POWER_LEVEL substate
    # rather than the generic "Power Level").
    @dataclass(frozen=True)
    class _StateSpec:
        suffix             : str
        entity_state_type  : EntityStateType
        is_controllable    : bool
        value_range        : Optional[Dict] = None
        label              : Optional[str]  = None
        units              : Optional[str]  = None
        # Refined EntityStateRole; ``None`` falls back to the
        # EntityStateType's default role at creation time. Set when
        # the spec carries domain semantics beyond the bare type
        # (e.g., distinguishing current vs. target temperature on a
        # thermostat where both are EntityStateType.TEMPERATURE).
        role               : Optional[EntityStateRole] = None

        @property
        def display_label(self) -> str:
            return self.label if self.label else self.entity_state_type.label

    # Setpoint slider bounds for thermostat substates, expressed in
    # ``hi.units.CANONICAL_TEMPERATURE_UNIT``. Climate-specific UX
    # choices (slightly wider than typical HVAC comfort ranges so
    # the operator can push edge cases). If the HI-wide canonical
    # changes, these bounds must also be updated to the equivalent
    # values in the new unit.
    _SETPOINT_MIN_CANONICAL  = 5
    _SETPOINT_MAX_CANONICAL  = 35

    # Translation of HA's color_mode attribute values to HI's
    # COLOR_MODE EntityStateValues. HA's ``null`` and explicit
    # ``'unknown'`` both map to UNKNOWN — HA's docs distinguish
    # them but don't ascribe different semantics, and off-state
    # behavior varies per-integration.
    _HASS_COLOR_MODE_TO_HI_VALUE = {
        None: EntityStateValue.COLOR_MODE_UNKNOWN,
        HassApi.COLOR_MODE_UNKNOWN: EntityStateValue.COLOR_MODE_UNKNOWN,
        HassApi.COLOR_MODE_ONOFF: EntityStateValue.COLOR_MODE_ONOFF,
        HassApi.COLOR_MODE_BRIGHTNESS: EntityStateValue.COLOR_MODE_BRIGHTNESS,
        HassApi.COLOR_MODE_COLOR_TEMP: EntityStateValue.COLOR_MODE_COLOR_TEMP,
        HassApi.COLOR_MODE_HS: EntityStateValue.COLOR_MODE_HS,
        HassApi.COLOR_MODE_RGB: EntityStateValue.COLOR_MODE_RGB,
        HassApi.COLOR_MODE_RGBW: EntityStateValue.COLOR_MODE_RGBW,
        HassApi.COLOR_MODE_RGBWW: EntityStateValue.COLOR_MODE_RGBWW,
        HassApi.COLOR_MODE_XY: EntityStateValue.COLOR_MODE_XY,
        HassApi.COLOR_MODE_WHITE: EntityStateValue.COLOR_MODE_WHITE,
    }

    @classmethod
    def _state_specs_for_hass_state(
            cls, hass_state: HassState ) -> List[ '_StateSpec' ]:
        """Return the substate specs for a HA state that decomposes
        into multiple HI EntityStates, or an empty list when the
        state maps to a single bare-key EntityState. Each domain
        owns its own decomposition rules — what substates exist,
        which are controllable, what their value ranges are — and
        composes specs per-instance based on what the live
        ``hass_state`` actually reports.
        """
        if hass_state.domain == HassApi.LIGHT_DOMAIN:
            return cls._light_state_specs( hass_state )
        if hass_state.domain == HassApi.FAN_DOMAIN:
            return cls._fan_state_specs( hass_state )
        if hass_state.domain == HassApi.CLIMATE_DOMAIN:
            return cls._climate_state_specs( hass_state )
        if hass_state.domain == HassApi.CAMERA_DOMAIN:
            return cls._camera_state_specs( hass_state )
        return []

    @classmethod
    def _light_state_specs(
            cls, hass_state: HassState ) -> List[ '_StateSpec' ]:
        """Color-related substates implied by a HA ``light.x`` state's
        ``supported_color_modes`` declaration. A bulb supporting HS
        (or RGB / XY, alternate representations of HS chromaticity)
        contributes hue and saturation; one supporting ``color_temp``
        contributes color temperature. Both can be present
        simultaneously when the bulb supports both modes — HA's
        ``color_mode`` attribute selects which is currently
        authoritative, but HI presents both controls. When any color
        axis is present, brightness becomes a peer substate too;
        brightness-only bulbs keep the bare-key single-state model."""
        supported = hass_state.attributes.get( HassApi.SUPPORTED_COLOR_MODES_ATTR )
        if not isinstance( supported, list ):
            return []

        chromatic_present = any( m in cls._CHROMATIC_COLOR_MODES for m in supported )
        color_temp_present = HassApi.COLOR_MODE_COLOR_TEMP in supported

        specs = []
        if chromatic_present or color_temp_present:
            specs.append( cls._StateSpec(
                suffix = HassApi.BRIGHTNESS_ATTR,
                entity_state_type = EntityStateType.LIGHT_DIMMER,
                is_controllable = True,
                value_range = { 'min': 0, 'max': 100 },
                role = EntityStateRole.LIGHT_BRIGHTNESS,
            ))
        if chromatic_present:
            specs.append( cls._StateSpec(
                suffix = 'hue',
                entity_state_type = EntityStateType.HUE,
                is_controllable = True,
                value_range = { 'min': 0, 'max': 360 },
                role = EntityStateRole.LIGHT_HUE,
            ))
            specs.append( cls._StateSpec(
                suffix = 'saturation',
                entity_state_type = EntityStateType.SATURATION,
                is_controllable = True,
                value_range = { 'min': 0, 'max': 100 },
                role = EntityStateRole.LIGHT_SATURATION,
            ))
        if color_temp_present:
            # Real bulbs have device-specific Kelvin ranges (e.g.,
            # 2700-5000K for warm-white LEDs, 2000-6500K for
            # color-capable bulbs). HA declares the device's
            # actual bounds in ``min_color_temp_kelvin`` /
            # ``max_color_temp_kelvin`` when known; the broad
            # fallback covers integrations that don't report.
            min_k = hass_state.attributes.get(
                HassApi.MIN_COLOR_TEMP_KELVIN_ATTR, 2000,
            )
            max_k = hass_state.attributes.get(
                HassApi.MAX_COLOR_TEMP_KELVIN_ATTR, 6500,
            )
            specs.append( cls._StateSpec(
                suffix = HassApi.COLOR_MODE_COLOR_TEMP,
                entity_state_type = EntityStateType.COLOR_TEMPERATURE,
                is_controllable = True,
                value_range = { 'min': min_k, 'max': max_k },
                role = EntityStateRole.LIGHT_COLOR_TEMPERATURE,
            ))
        # COLOR_MODE only adds information when there's actual
        # mode-switching to track. A bulb with a single supported
        # mode has a constant value; skip it.
        if len( supported ) > 1:
            specs.append( cls._StateSpec(
                suffix = HassApi.COLOR_MODE_ATTR,
                entity_state_type = EntityStateType.COLOR_MODE,
                is_controllable = False,
                role = EntityStateRole.LIGHT_COLOR_MODE,
            ))
        return specs

    @classmethod
    def _fan_state_specs(
            cls, hass_state: HassState ) -> List[ '_StateSpec' ]:
        """Substates implied by a HA ``fan.x`` state when it reports
        any of the multi-axis features (oscillating / direction /
        preset_modes). Speed becomes a peer ``~speed`` POWER_LEVEL
        substate alongside the others; speed-only fans keep the
        bare-key single-state model. Per-fan ``preset_modes`` list
        becomes the value range of the preset substate."""
        if not cls._fan_has_multi_features( hass_state ):
            return []
        attrs = hass_state.attributes
        specs = []
        if cls._has_percentage_capability( hass_state ):
            specs.append( cls._StateSpec(
                suffix = 'speed',
                entity_state_type = EntityStateType.POWER_LEVEL,
                is_controllable = True,
                value_range = { 'min': 0, 'max': 100 },
                label = 'Speed',
                role = EntityStateRole.FAN_SPEED,
            ))
        if HassApi.OSCILLATING_ATTR in attrs:
            specs.append( cls._StateSpec(
                suffix = HassApi.OSCILLATING_ATTR,
                entity_state_type = EntityStateType.ON_OFF,
                is_controllable = True,
                label = 'Oscillation',
                role = EntityStateRole.FAN_OSCILLATION,
            ))
        if HassApi.DIRECTION_ATTR in attrs:
            specs.append( cls._StateSpec(
                suffix = HassApi.DIRECTION_ATTR,
                entity_state_type = EntityStateType.DISCRETE,
                is_controllable = True,
                value_range = {
                    HassApi.FAN_DIRECTION_FORWARD: 'Forward',
                    HassApi.FAN_DIRECTION_REVERSE: 'Reverse',
                },
                label = 'Direction',
                role = EntityStateRole.FAN_DIRECTION,
            ))
        preset_modes = attrs.get( HassApi.PRESET_MODES_ATTR )
        if isinstance( preset_modes, list ) and preset_modes:
            specs.append( cls._StateSpec(
                suffix = HassApi.PRESET_MODE_ATTR,
                entity_state_type = EntityStateType.DISCRETE,
                is_controllable = True,
                value_range = { mode: mode for mode in preset_modes },
                label = 'Preset',
                role = EntityStateRole.FAN_PRESET_MODE,
            ))
        return specs

    # HA's well-known set of HVAC action values (what the system
    # is currently doing). Used as the value range of the
    # ``hvac_action`` substate so the controller widget displays
    # human-friendly labels even though the substate is
    # sensor-only (read from HA, not operator-set).
    _HVAC_ACTION_CHOICES = {
        'heating'     : 'Heating',
        'cooling'     : 'Cooling',
        'drying'      : 'Drying',
        'fan'         : 'Fan',
        'idle'        : 'Idle',
        'off'         : 'Off',
        'preheating'  : 'Preheating',
        'defrosting'  : 'Defrosting',
    }

    @classmethod
    def _climate_state_specs(
            cls, hass_state: HassState ) -> List[ '_StateSpec' ]:
        """Substates implied by a HA ``climate.x`` state. A climate
        entity that declares ``hvac_modes`` always decomposes:
        current_temperature (sensor), hvac_mode (controller from
        the declared modes list), hvac_action (sensor), plus a
        setpoint substate set chosen from the supported modes —
        single ``target_temperature`` for any single-mode
        operation (heat/cool/off/etc.), low+high pair for
        ``heat_cool`` mode. Climate entities lacking
        ``hvac_modes`` fall through to the bare-key TEMPERATURE
        mapping for backward compatibility."""
        attrs = hass_state.attributes
        hvac_modes = attrs.get( HassApi.HVAC_MODES_ATTR )
        if not isinstance( hvac_modes, list ) or not hvac_modes:
            return []

        canonical_unit = CANONICAL_TEMPERATURE_UNIT
        specs = [
            cls._StateSpec(
                suffix = HassApi.CURRENT_TEMPERATURE_ATTR,
                entity_state_type = EntityStateType.TEMPERATURE,
                is_controllable = False,
                label = 'Current Temperature',
                units = canonical_unit,
                role = EntityStateRole.THERMOSTAT_CURRENT_TEMPERATURE,
            ),
            cls._StateSpec(
                suffix = HassApi.HVAC_MODE_ATTR,
                entity_state_type = EntityStateType.DISCRETE,
                is_controllable = True,
                value_range = { mode: mode for mode in hvac_modes },
                label = 'HVAC Mode',
                role = EntityStateRole.HVAC_MODE,
            ),
            cls._StateSpec(
                suffix = HassApi.HVAC_ACTION_ATTR,
                entity_state_type = EntityStateType.DISCRETE,
                is_controllable = False,
                value_range = dict( cls._HVAC_ACTION_CHOICES ),
                label = 'HVAC Action',
                role = EntityStateRole.HVAC_ACTION,
            ),
        ]

        # Setpoint substates: any non-heat_cool mode (heat / cool /
        # off / dry / fan_only / auto) implies single-setpoint
        # operation; ``heat_cool`` implies a low/high pair. A
        # thermostat that supports both creates all three —
        # which one carries a value at runtime depends on the
        # active hvac_mode. Bounds are in HI's canonical unit;
        # display-layer unit conversion happens at render time
        # against the user's preferred unit.
        setpoint_range = cls._setpoint_value_range()
        has_single_mode = any( m != HassApi.HVAC_MODE_HEAT_COOL for m in hvac_modes )
        has_dual_mode = HassApi.HVAC_MODE_HEAT_COOL in hvac_modes
        if has_single_mode:
            specs.append( cls._StateSpec(
                suffix = 'target_temperature',
                entity_state_type = EntityStateType.TEMPERATURE,
                is_controllable = True,
                value_range = setpoint_range,
                label = 'Setpoint',
                units = canonical_unit,
                role = EntityStateRole.THERMOSTAT_TARGET_TEMPERATURE,
            ))
        if has_dual_mode:
            specs.append( cls._StateSpec(
                suffix = HassApi.TARGET_TEMP_LOW_ATTR,
                entity_state_type = EntityStateType.TEMPERATURE,
                is_controllable = True,
                value_range = setpoint_range,
                label = 'Setpoint Low',
                units = canonical_unit,
                role = EntityStateRole.THERMOSTAT_TARGET_TEMPERATURE_LOW,
            ))
            specs.append( cls._StateSpec(
                suffix = HassApi.TARGET_TEMP_HIGH_ATTR,
                entity_state_type = EntityStateType.TEMPERATURE,
                is_controllable = True,
                value_range = setpoint_range,
                label = 'Setpoint High',
                units = canonical_unit,
                role = EntityStateRole.THERMOSTAT_TARGET_TEMPERATURE_HIGH,
            ))

        # Optional axes that real thermostats commonly expose.
        # Surfaced only when the live state declares them so HI
        # doesn't display a "Fan Mode" control on a thermostat
        # that doesn't have one.
        fan_modes = attrs.get( HassApi.FAN_MODES_ATTR )
        if isinstance( fan_modes, list ) and fan_modes:
            specs.append( cls._StateSpec(
                suffix = HassApi.FAN_MODE_ATTR,
                entity_state_type = EntityStateType.DISCRETE,
                is_controllable = True,
                value_range = { mode: mode for mode in fan_modes },
                label = 'Fan Mode',
                role = EntityStateRole.FAN_MODE,
            ))
        preset_modes = attrs.get( HassApi.PRESET_MODES_ATTR )
        if isinstance( preset_modes, list ) and preset_modes:
            specs.append( cls._StateSpec(
                suffix = HassApi.PRESET_MODE_ATTR,
                entity_state_type = EntityStateType.DISCRETE,
                is_controllable = True,
                value_range = { mode: mode for mode in preset_modes },
                label = 'Preset',
                role = EntityStateRole.PRESET_MODE,
            ))
        if HassApi.CURRENT_HUMIDITY_ATTR in attrs:
            specs.append( cls._StateSpec(
                suffix = HassApi.CURRENT_HUMIDITY_ATTR,
                entity_state_type = EntityStateType.HUMIDITY,
                is_controllable = False,
                label = 'Current Humidity',
                units = str(HumidityUnit.PERCENT),
            ))
        return specs

    # HA's fixed set of camera state values. Listed here (rather than
    # read from an attribute) because HA's camera spec declares the
    # set itself, not the entity — same shape as ``_HVAC_ACTION_CHOICES``.
    _CAMERA_STATE_VALUES = (
        HassApi.CAMERA_STATE_IDLE,
        HassApi.CAMERA_STATE_STREAMING,
        HassApi.CAMERA_STATE_RECORDING,
    )

    @classmethod
    def _camera_state_specs(
            cls, hass_state : HassState ) -> List[ '_StateSpec' ]:
        """Substates for a ``camera.x`` entity. A read-only ``state``
        substate carries the primary mode (idle / streaming /
        recording); when the entity reports ``motion_detection`` in
        its attributes a controllable ON_OFF substate is exposed for
        the HA enable/disable services."""
        specs = [
            cls._StateSpec(
                suffix = HassApi.STATE_FIELD,
                entity_state_type = EntityStateType.DISCRETE,
                is_controllable = False,
                value_range = { v: v for v in cls._CAMERA_STATE_VALUES },
                label = 'Mode',
            ),
        ]
        if HassApi.MOTION_DETECTION_ATTR in hass_state.attributes:
            specs.append( cls._StateSpec(
                suffix = HassApi.MOTION_DETECTION_ATTR,
                entity_state_type = EntityStateType.ON_OFF,
                is_controllable = True,
                label = 'Motion Detection',
            ))
        return specs

    @classmethod
    def _setpoint_value_range( cls ) -> Dict[ str, float ]:
        """Slider bounds for thermostat setpoints, in HI's canonical
        temperature unit. Slightly wider than typical HVAC comfort
        ranges so the operator can push edge cases. Display layer
        converts to the user's preferred unit."""
        return {
            'min': cls._SETPOINT_MIN_CANONICAL,
            'max': cls._SETPOINT_MAX_CANONICAL,
        }

    @classmethod
    def _extract_substate_value(
            cls,
            hass_state : HassState,
            spec       : '_StateSpec',
    ) -> Optional[ str ]:
        """Pull the value for a single substate out of a HA state,
        dispatching per-domain. Returns ``None`` when the relevant
        attribute is absent — callers skip ``None``-valued substates
        from the response map. The full ``spec`` is passed (rather
        than just the suffix) so per-domain handlers can read
        metadata such as the spec's canonical ``units`` when
        normalizing values at the boundary."""
        if hass_state.domain == HassApi.LIGHT_DOMAIN:
            return cls._light_substate_value( hass_state, spec.suffix )
        if hass_state.domain == HassApi.FAN_DOMAIN:
            return cls._fan_substate_value( hass_state, spec.suffix )
        if hass_state.domain == HassApi.CLIMATE_DOMAIN:
            return cls._climate_substate_value( hass_state, spec )
        if hass_state.domain == HassApi.CAMERA_DOMAIN:
            return cls._camera_substate_value( hass_state, spec.suffix )
        return None

    @classmethod
    def _light_substate_value(
            cls, hass_state : HassState, suffix : str ) -> Optional[ str ]:
        """Light-domain substate values. Returns whatever HA
        reports; we don't filter by ``color_mode``. HA may
        continue to report ``hs_color`` while in color_temp mode
        (or vice versa); that value is still the bulb's
        last-known chromaticity and relaying it as the
        hue/saturation HI state is correct."""
        attrs = hass_state.attributes
        if suffix == HassApi.BRIGHTNESS_ATTR:
            return cls._dimmer_brightness_value( hass_state )
        if suffix == 'hue':
            hs = attrs.get( HassApi.HS_COLOR_ATTR )
            if isinstance( hs, list ) and len( hs ) >= 1:
                try:
                    return str( round( float( hs[ 0 ] ) ) )
                except ( TypeError, ValueError ):
                    return None
            return None
        if suffix == 'saturation':
            hs = attrs.get( HassApi.HS_COLOR_ATTR )
            if isinstance( hs, list ) and len( hs ) >= 2:
                try:
                    return str( round( float( hs[ 1 ] ) ) )
                except ( TypeError, ValueError ):
                    return None
            return None
        if suffix == HassApi.COLOR_MODE_COLOR_TEMP:
            kelvin = attrs.get( HassApi.COLOR_TEMP_KELVIN_ATTR )
            if kelvin is not None:
                try:
                    return str( int( float( kelvin ) ) )
                except ( TypeError, ValueError ):
                    return None
            return None
        if suffix == HassApi.COLOR_MODE_ATTR:
            if HassApi.COLOR_MODE_ATTR not in attrs:
                return None
            ha_value = attrs[ HassApi.COLOR_MODE_ATTR ]
            hi_value = cls._HASS_COLOR_MODE_TO_HI_VALUE.get(
                ha_value, EntityStateValue.COLOR_MODE_UNKNOWN,
            )
            return str( hi_value )
        return None

    @classmethod
    def _fan_substate_value(
            cls, hass_state : HassState, suffix : str ) -> Optional[ str ]:
        """Fan-domain substate values."""
        attrs = hass_state.attributes
        if suffix == 'speed':
            raw = attrs.get( HassApi.PERCENTAGE_ATTR )
            if raw is None:
                return None
            try:
                return str( int( float( raw ) ) )
            except ( TypeError, ValueError ):
                return None
        if suffix == HassApi.OSCILLATING_ATTR:
            osc = attrs.get( HassApi.OSCILLATING_ATTR )
            if osc is None:
                return None
            return str( EntityStateValue.ON ) if osc else str( EntityStateValue.OFF )
        if suffix == HassApi.DIRECTION_ATTR:
            return attrs.get( HassApi.DIRECTION_ATTR )
        if suffix == HassApi.PRESET_MODE_ATTR:
            return attrs.get( HassApi.PRESET_MODE_ATTR )
        return None

    @classmethod
    def _camera_substate_value(
            cls, hass_state : HassState, suffix : str ) -> Optional[ str ]:
        """Camera-domain substate values. The ``state`` substate
        passes HA's primary state field through (idle / streaming /
        recording); ``motion_detection`` arrives as a JSON bool on the
        camera entity's attributes (HA folds the enable-motion-detection
        flag into its attributes rather than exposing it as a separate
        entity)."""
        if suffix == HassApi.STATE_FIELD:
            return hass_state.state_value
        if suffix == HassApi.MOTION_DETECTION_ATTR:
            value = hass_state.attributes.get( HassApi.MOTION_DETECTION_ATTR )
            if value is None:
                return None
            return str( EntityStateValue.ON ) if value else str( EntityStateValue.OFF )
        return None

    @classmethod
    def _climate_substate_value(
            cls, hass_state : HassState, spec : '_StateSpec' ) -> Optional[ str ]:
        """Climate-domain substate values. Temperature substates emit
        floats as strings, converted from HA's reported
        ``temperature_unit`` to the EntityState's stored unit (looked
        up via the IntegrationMetadataCache) so cached values stay
        unit-coherent with the EntityState. Mode/action substates
        emit HA's wire enum strings unchanged. The hvac_mode's value
        lives on the entity-level ``state`` field (not in attributes),
        per HA's climate platform contract. Setpoint substates only
        emit a value when the matching attribute is present in the
        live state — HA's setpoint shape varies by mode (single
        ``temperature`` vs ``target_temp_low`` + ``target_temp_high``)
        and unused setpoints simply aren't reported."""
        attrs = hass_state.attributes
        suffix = spec.suffix
        if suffix == HassApi.HVAC_MODE_ATTR:
            return hass_state.state_value
        if suffix == HassApi.HVAC_ACTION_ATTR:
            return attrs.get( HassApi.HVAC_ACTION_ATTR )
        if suffix == HassApi.FAN_MODE_ATTR:
            return attrs.get( HassApi.FAN_MODE_ATTR )
        if suffix == HassApi.PRESET_MODE_ATTR:
            return attrs.get( HassApi.PRESET_MODE_ATTR )
        if suffix == HassApi.CURRENT_HUMIDITY_ATTR:
            return cls._numeric_attr_as_str( attrs, HassApi.CURRENT_HUMIDITY_ATTR )
        # Temperature-bearing substates: convert from HA's reported
        # unit to the EntityState's stored unit at the boundary.
        attr_key_for_suffix = {
            HassApi.CURRENT_TEMPERATURE_ATTR : HassApi.CURRENT_TEMPERATURE_ATTR,
            'target_temperature'             : HassApi.TARGET_TEMPERATURE_ATTR,
            HassApi.TARGET_TEMP_LOW_ATTR     : HassApi.TARGET_TEMP_LOW_ATTR,
            HassApi.TARGET_TEMP_HIGH_ATTR    : HassApi.TARGET_TEMP_HIGH_ATTR,
        }
        attr_key = attr_key_for_suffix.get( suffix )
        if attr_key is None:
            return None
        raw = attrs.get( attr_key )
        if raw is None:
            return None
        try:
            external_value = float( raw )
        except ( TypeError, ValueError ):
            return None
        substate_integration_key = cls._substate_integration_key(
            hass_state = hass_state,
            suffix = suffix,
        )
        entity_state_value = IntegrationConverterHelper.to_entity_state_value(
            external_value = external_value,
            external_unit = attrs.get( HassApi.TEMPERATURE_UNIT_ATTR ),
            integration_key = substate_integration_key,
        )
        return str( entity_state_value )

    @staticmethod
    def _numeric_attr_as_str(
            attrs : Dict, key : str ) -> Optional[ str ]:
        raw = attrs.get( key )
        if raw is None:
            return None
        try:
            return str( float( raw ) )
        except ( TypeError, ValueError ):
            return None

    @classmethod
    def _substate_integration_key(
            cls,
            hass_state : HassState,
            suffix     : str,
    ) -> IntegrationKey:
        """Build the suffix-extended IntegrationKey for a substate.
        The suffix lets the controller dispatch (and sensor-update
        routing) tell which dimension a given key targets without
        re-parsing the parent state's capability declaration."""
        return cls._substate_integration_key_for_suffix(
            parent_entity_id = hass_state.entity_id,
            suffix = suffix,
        )

    @classmethod
    def _substate_integration_key_for_suffix(
            cls,
            parent_entity_id : str,
            suffix           : str,
    ) -> IntegrationKey:
        # ``~`` separator chosen over ``:`` because the latter has
        # special meaning in CSS selectors (pseudo-classes) and
        # in URLs; ``~`` is web-safe in every position and never
        # appears in real HA entity_ids (they're ``[a-z0-9_]+``).
        return IntegrationKey(
            integration_id = HassMetaData.integration_id,
            integration_name = f'{parent_entity_id}~{suffix}',
        )

    @classmethod
    def _has_brightness_capability( cls, hass_state: HassState ) -> bool:
        """Check if a light has brightness/dimming capability."""
        if hass_state.domain != HassApi.LIGHT_DOMAIN:
            return False

        attributes = hass_state.attributes
        if HassApi.BRIGHTNESS_ATTR in attributes or HassApi.BRIGHTNESS_PCT_PARAM in attributes:
            return True

        # The brightness attribute is omitted in HA's off-state
        # output even for known-dimmable lights; consult the
        # capability declaration in ``supported_color_modes`` so
        # the dimmer path keeps firing across on/off transitions.
        supported_color_modes = attributes.get( HassApi.SUPPORTED_COLOR_MODES_ATTR )
        if isinstance(supported_color_modes, list):
            for mode in supported_color_modes:
                if mode in cls._BRIGHTNESS_SUPPORTING_COLOR_MODES:
                    return True
        return False

    @classmethod
    def _has_position_capability( cls, hass_state: HassState ) -> bool:
        """True when an HA cover state reports ``current_position``,
        meaning the cover is a continuous-position device (blind,
        slider shade) rather than a binary open/close (garage,
        door)."""
        return hass_state.attributes.get( HassApi.CURRENT_POSITION_ATTR ) is not None

    @classmethod
    def _has_percentage_capability( cls, hass_state: HassState ) -> bool:
        """True when an HA fan state reports ``percentage``, meaning
        the fan exposes a continuous speed dimension."""
        return hass_state.attributes.get( HassApi.PERCENTAGE_ATTR ) is not None

    @classmethod
    def _fan_has_multi_features( cls, hass_state: HassState ) -> bool:
        """True when an HA fan state reports any of the multi-axis
        capabilities that trigger substate decomposition
        (oscillating, direction, preset_modes). Detection is by
        attribute presence; HA reports these only when the fan
        actually supports them."""
        attrs = hass_state.attributes
        return (
            HassApi.OSCILLATING_ATTR in attrs
            or HassApi.DIRECTION_ATTR in attrs
            or HassApi.PRESET_MODES_ATTR in attrs
        )

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
        elif entity_state_type == EntityStateType.OPEN_CLOSE:
            controller = HiModelHelper.create_open_close_controller(
                entity = entity,
                integration_key = integration_key,
                name = name,
            )
        elif entity_state_type == EntityStateType.OPEN_CLOSE_POSITION:
            controller = HiModelHelper.create_open_close_position_controller(
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
        elif entity_state_type == EntityStateType.POWER_LEVEL:
            # Caller decides per-domain label by passing ``name``;
            # for a fan, it lands as e.g. "Zoo Fan Speed".
            controller = HiModelHelper.create_power_level_controller(
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
        elif entity_state_type == EntityStateType.SMOKE:
            sensor = HiModelHelper.create_smoke_sensor(
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
            # HA → HI boundary: HI stores temperatures in the canonical
            # unit; the inbound state translator converts HA's reported
            # value at every poll. The EntityState.units is the source
            # of truth (consulted via IntegrationMetadataCache); HA's
            # native unit lives in the integration_payload for
            # outbound dispatch convenience.
            sensor = HiModelHelper.create_sensor(
                entity = entity,
                entity_state_type = EntityStateType.TEMPERATURE,
                name = name,
                integration_key = integration_key,
                units = CANONICAL_TEMPERATURE_UNIT,
            )
            domain_payload = {
                **( domain_payload or {} ),
                'native_temperature_unit': hass_state.unit_of_measurement,
            }
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
        elif entity_state_type == EntityStateType.BATTERY_LEVEL:
            # HA's battery sensor reports a 0-100 percentage with
            # ``unit_of_measurement='%'``. Store the unit verbatim so
            # the display path renders ``"85%"`` rather than the bare
            # magnitude. With ``add_default_alarm`` the factory also
            # wires the canonical low-battery threshold alarm
            # (EventClauseOperator.LT at the default threshold).
            sensor = HiModelHelper.create_battery_level_sensor(
                entity = entity,
                integration_key = integration_key,
                name = name,
                units = hass_state.unit_of_measurement or '%',
                add_default_alarm = add_alarm_events,
            )
        elif entity_state_type == EntityStateType.LIGHT_LEVEL:
            # HA's illuminance sensor reports lux ("lx") as the
            # standard unit; some integrations omit the attribute,
            # in which case we fall back to lux.
            sensor = HiModelHelper.create_sensor(
                entity = entity,
                entity_state_type = EntityStateType.LIGHT_LEVEL,
                name = name,
                integration_key = integration_key,
                units = hass_state.unit_of_measurement or 'lx',
            )
        elif entity_state_type in (
                EntityStateType.ELECTRIC_USAGE,
                EntityStateType.AIR_PRESSURE,
                EntityStateType.WIND_SPEED,
        ):
            # Generic numeric sensor with a unit pulled verbatim
            # from HA. Used for power (W/kW), pressure (hPa/mbar),
            # wind speed (km/h, mph). No unit conversion at the HI
            # boundary — the user's display-unit preference applies
            # at template-render time via the canonical Pint path.
            sensor = HiModelHelper.create_sensor(
                entity = entity,
                entity_state_type = entity_state_type,
                name = name,
                integration_key = integration_key,
                units = hass_state.unit_of_measurement or '',
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
                add_default_alarm = add_alarm_events,
            )
        elif entity_state_type == EntityStateType.OPEN_CLOSE:
            sensor = HiModelHelper.create_open_close_sensor(
                entity = entity,
                integration_key = integration_key,
                name = name,
                add_default_alarm = add_alarm_events,
            )
        elif entity_state_type == EntityStateType.MOVEMENT:
            sensor = HiModelHelper.create_movement_sensor(
                entity = entity,
                integration_key = integration_key,
                name = name,
                add_default_alarm = add_alarm_events,
            )
        elif entity_state_type == EntityStateType.PRESENCE:
            # PRESENCE shares the [ACTIVE, IDLE] EntityStateValue
            # vocabulary with MOVEMENT but renders under its own
            # state-type label and styling decay (see
            # ``EntityStateDisplayData._get_presence_status_style``).
            sensor = HiModelHelper.create_presence_sensor(
                entity = entity,
                integration_key = integration_key,
                name = name,
                add_default_alarm = add_alarm_events,
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
        elif entity_state_type == EntityStateType.SMOKE:
            sensor = HiModelHelper.create_smoke_sensor(
                entity = entity,
                integration_key = integration_key,
                name = name,
                add_default_alarm = add_alarm_events,
            )
        elif entity_state_type == EntityStateType.MOISTURE:
            sensor = HiModelHelper.create_moisture_sensor(
                entity = entity,
                integration_key = integration_key,
                name = name,
                add_default_alarm = add_alarm_events,
            )
        elif entity_state_type == EntityStateType.CO:
            sensor = HiModelHelper.create_co_sensor(
                entity = entity,
                integration_key = integration_key,
                name = name,
                add_default_alarm = add_alarm_events,
            )
        elif entity_state_type == EntityStateType.GAS:
            sensor = HiModelHelper.create_gas_sensor(
                entity = entity,
                integration_key = integration_key,
                name = name,
                add_default_alarm = add_alarm_events,
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
            return cls._strip_state_suffix_from_friendly_name(
                hass_state = shortest_id_state,
                friendly_name = friendly_name,
            )
        return hass_device.device_id

    @staticmethod
    def _strip_state_suffix_from_friendly_name(
            hass_state    : HassState,
            friendly_name : str ) -> str:
        """For a combo-device state grouped via entity_id suffix
        stripping (e.g., ``sensor.kitchen_humidity`` →
        device_id ``kitchen``), the picked friendly_name often
        still carries the title-cased suffix word
        (``'Kitchen Humidity'``). Strip it so the HI Entity name
        is the device-level name (``'Kitchen'``).
        Conservative: only strips when the friendly_name's tail
        is the direct title-case of the entity_id's removed
        underscore suffix — a user-renamed friendly_name that
        doesn't follow that pattern passes through unchanged."""
        full = hass_state.entity_name_sans_prefix
        short = hass_state.entity_name_sans_suffix
        if full == short:
            return friendly_name
        suffix = full[ len(short): ]
        suffix_words = ' '.join(
            part.capitalize() for part in suffix.split('_') if part
        )
        tail = ' ' + suffix_words
        if friendly_name.endswith( tail ):
            return friendly_name[ : -len(tail) ]
        return friendly_name
        
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
        if device_class_set.intersection({
                HassApi.MOTION_DEVICE_CLASS,
                HassApi.OCCUPANCY_DEVICE_CLASS,
        }):
            return EntityType.MOTION_SENSOR
        if HassApi.PRESENCE_DEVICE_CLASS in device_class_set:
            return EntityType.PRESENCE_SENSOR
        if HassApi.SMOKE_DEVICE_CLASS in device_class_set:
            return EntityType.SMOKE_DETECTOR
        if HassApi.MOISTURE_DEVICE_CLASS in device_class_set:
            return EntityType.LEAK_SENSOR
        if HassApi.CARBON_MONOXIDE_DEVICE_CLASS in device_class_set:
            return EntityType.CARBON_MONOXIDE_DETECTOR
        if HassApi.GAS_DEVICE_CLASS in device_class_set:
            return EntityType.GAS_DETECTOR
        # Multi-quantity outdoor sensors (Netatmo etc.) report
        # pressure and/or wind_speed alongside other readings.
        # Either signal is rare in indoor devices.
        if device_class_set.intersection({
                HassApi.PRESSURE_DEVICE_CLASS,
                HassApi.WIND_SPEED_DEVICE_CLASS,
        }):
            return EntityType.WEATHER_STATION
        if ( HassApi.SENSOR_DOMAIN in domain_set
             and HassApi.POWER_DEVICE_CLASS in device_class_set ):
            return EntityType.ELECTRICITY_METER
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
        # HA covers are the *control mechanism* (motor / opener)
        # for doors / windows / garage doors / blinds / awnings /
        # gates / etc. The thing being controlled (the door, the
        # window) is a separate floor-plan element; what HA
        # exposes here is the actuator. ``GARAGE_DOOR_OPENER``
        # already specializes the most common case;
        # ``OPEN_CLOSE_ACTUATOR`` is the generic fall-through for
        # every other cover device class.
        if HassApi.COVER_DOMAIN in domain_set:
            if HassApi.GARAGE_DEVICE_CLASS in device_class_set:
                return EntityType.GARAGE_DOOR_OPENER
            return EntityType.OPEN_CLOSE_ACTUATOR
        # Fan domain has no HA-side device class to distinguish
        # ceiling vs exhaust; CEILING_FAN is the more common case.
        if HassApi.FAN_DOMAIN in domain_set:
            return EntityType.CEILING_FAN
        # Climate domain is the controllable HVAC entity; the
        # temperature / humidity device-class checks below catch
        # passive sensors that aren't climate entities. Combo
        # temp+humidity devices hit the temperature branch first
        # and resolve to THERMOMETER, which reads naturally for
        # the dual-quantity case.
        if HassApi.CLIMATE_DOMAIN in domain_set:
            return EntityType.THERMOSTAT
        if HassApi.TEMPERATURE_DEVICE_CLASS in device_class_set:
            return EntityType.THERMOMETER
        if HassApi.HUMIDITY_DEVICE_CLASS in device_class_set:
            return EntityType.HYGROMETER
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
        # HA emits ``state='unknown'`` before the first report
        # and ``state='unavailable'`` when the entity is offline.
        # Treat both as "no value" so sensor history doesn't
        # accrue placeholder records that would surface as
        # labeled text in the polling refresh.
        if hass_state.state_value in HassStateValue.NO_VALUE_STATES:
            return {}
        domain = hass_state.domain
        if domain == HassApi.LIGHT_DOMAIN:
            return cls._light_to_sensor_value_map( hass_state )
        if domain == HassApi.BINARY_SENSOR_DOMAIN:
            return cls._binary_sensor_to_sensor_value_map( hass_state )
        if domain == HassApi.LOCK_DOMAIN:
            return cls._lock_to_sensor_value_map( hass_state )
        if domain == HassApi.COVER_DOMAIN:
            return cls._cover_to_sensor_value_map( hass_state )
        if domain == HassApi.FAN_DOMAIN:
            return cls._fan_to_sensor_value_map( hass_state )
        if domain == HassApi.CLIMATE_DOMAIN:
            return cls._climate_to_sensor_value_map( hass_state )
        if domain == HassApi.CAMERA_DOMAIN:
            return cls._camera_to_sensor_value_map( hass_state )
        if domain == HassApi.SENSOR_DOMAIN:
            return cls._sensor_domain_to_sensor_value_map( hass_state )
        return cls._passthrough_to_sensor_value_map( hass_state )

    @classmethod
    def _sensor_domain_to_sensor_value_map(
            cls, hass_state : HassState ) -> Dict[ IntegrationKey, str ]:
        """HA ``sensor.x`` entities. Temperature-class sensors are
        normalized at this boundary into the EntityState's stored
        unit (looked up via IntegrationMetadataCache) so cached values
        stay coherent with the EntityState's units field. Other
        sensor device classes pass through unchanged."""
        if hass_state.device_class != HassApi.TEMPERATURE_DEVICE_CLASS:
            return cls._passthrough_to_sensor_value_map( hass_state )
        try:
            external_value = float( hass_state.state_value )
        except ( TypeError, ValueError ):
            return {}
        integration_key = cls.hass_state_to_integration_key( hass_state )
        entity_state_value = IntegrationConverterHelper.to_entity_state_value(
            external_value = external_value,
            external_unit = hass_state.unit_of_measurement,
            integration_key = integration_key,
        )
        return { integration_key : str( entity_state_value ) }

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
        (hue, saturation, color temperature, color mode) implied
        by the HA light's ``supported_color_modes``. Each value
        targets a distinct HI EntityState. For multi-substate
        lights brightness is itself a peer substate (suffixed
        key); for single-state lights it goes at the bare key."""
        result : Dict[ IntegrationKey, str ] = {}
        state_specs = cls._state_specs_for_hass_state( hass_state )
        if not state_specs:
            brightness_value = cls._dimmer_brightness_value( hass_state )
            if brightness_value:
                result[ cls.hass_state_to_integration_key( hass_state ) ] = brightness_value
            return result
        for spec in state_specs:
            value = cls._extract_substate_value( hass_state, spec )
            if value is None:
                continue
            substate_key = cls._substate_integration_key(
                hass_state = hass_state,
                suffix = spec.suffix,
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
            brightness = hass_state.attributes.get( HassApi.BRIGHTNESS_ATTR )
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
        OPEN/CLOSED for doors and peers, SMOKE_DETECTED/SMOKE_CLEAR
        for smoke, CONNECTED/DISCONNECTED for connectivity,
        LOW/HIGH for battery."""
        sv = hass_state.state_value.lower()
        dc = hass_state.device_class
        if sv == HassStateValue.ON:
            if dc in HassApi.MOTION_LIKE_DEVICE_CLASS_SET:
                return str( EntityStateValue.ACTIVE )
            if dc == HassApi.BATTERY_DEVICE_CLASS:
                return str( EntityStateValue.LOW )
            if dc in HassApi.OPEN_CLOSE_DEVICE_CLASS_SET:
                return str( EntityStateValue.OPEN )
            if dc == HassApi.SMOKE_DEVICE_CLASS:
                return str( EntityStateValue.SMOKE_DETECTED )
            if dc == HassApi.MOISTURE_DEVICE_CLASS:
                return str( EntityStateValue.MOISTURE_DETECTED )
            if dc == HassApi.CARBON_MONOXIDE_DEVICE_CLASS:
                return str( EntityStateValue.CO_DETECTED )
            if dc == HassApi.GAS_DEVICE_CLASS:
                return str( EntityStateValue.GAS_DETECTED )
            if dc == HassApi.CONNECTIVITY_DEVICE_CLASS:
                return str( EntityStateValue.CONNECTED )
            return str( EntityStateValue.ON )
        if sv == HassStateValue.OFF:
            if dc in HassApi.MOTION_LIKE_DEVICE_CLASS_SET:
                return str( EntityStateValue.IDLE )
            if dc == HassApi.BATTERY_DEVICE_CLASS:
                return str( EntityStateValue.HIGH )
            if dc in HassApi.OPEN_CLOSE_DEVICE_CLASS_SET:
                return str( EntityStateValue.CLOSED )
            if dc == HassApi.SMOKE_DEVICE_CLASS:
                return str( EntityStateValue.SMOKE_CLEAR )
            if dc == HassApi.MOISTURE_DEVICE_CLASS:
                return str( EntityStateValue.MOISTURE_CLEAR )
            if dc == HassApi.CARBON_MONOXIDE_DEVICE_CLASS:
                return str( EntityStateValue.CO_CLEAR )
            if dc == HassApi.GAS_DEVICE_CLASS:
                return str( EntityStateValue.GAS_CLEAR )
            if dc == HassApi.CONNECTIVITY_DEVICE_CLASS:
                return str( EntityStateValue.DISCONNECTED )
            return str( EntityStateValue.OFF )
        logger.warning( f'Unknown HAss binary state value "{hass_state.state_value}".' )
        return None

    @classmethod
    def _lock_to_sensor_value_map(
            cls, hass_state : HassState ) -> Dict[ IntegrationKey, str ]:
        """Translate HA lock domain's domain-specific state strings
        to HI's canonical ON_OFF values. HA reports ``'locked'`` /
        ``'unlocked'`` as the entity state; HI's ON_OFF EntityState
        keys off ``EntityStateValue.ON`` / ``OFF`` for display and
        widget coercion. Without this, HI's checkbox would always
        render as ``Off`` regardless of the lock's real state."""
        sv = hass_state.state_value.lower()
        if sv == HassStateValue.LOCKED:
            value = str( EntityStateValue.ON )
        elif sv == HassStateValue.UNLOCKED:
            value = str( EntityStateValue.OFF )
        else:
            value = hass_state.state_value
        if not value:
            return {}
        return { cls.hass_state_to_integration_key( hass_state ) : value }

    @classmethod
    def _cover_to_sensor_value_map(
            cls, hass_state : HassState ) -> Dict[ IntegrationKey, str ]:
        """Cover domain: when ``current_position`` is reported,
        the EntityState is OPEN_CLOSE_POSITION (continuous slider)
        and the numeric position is the canonical value. Without
        position, the EntityState is OPEN_CLOSE (binary toggle)
        and HA's discrete state string passes through unchanged.
        Transitional ``'opening'`` / ``'closing'`` states pass
        through as well; downstream display logic falls back to
        the closed style for unrecognized values."""
        if cls._has_position_capability( hass_state ):
            try:
                position = int( float( hass_state.attributes[ HassApi.CURRENT_POSITION_ATTR ] ) )
            except ( TypeError, ValueError ):
                return {}
            return { cls.hass_state_to_integration_key( hass_state ) : str( position ) }
        return cls._passthrough_to_sensor_value_map( hass_state )

    @classmethod
    def _fan_to_sensor_value_map(
            cls, hass_state : HassState ) -> Dict[ IntegrationKey, str ]:
        """Fan domain: multi-feature fans decompose into substates
        (speed/oscillating/direction/preset) — each substate's
        value lands at its suffix-keyed integration_key. Speed-only
        fans get a single bare-key POWER_LEVEL value with the
        numeric percentage. Fans without percentage stay ON_OFF
        and pass HA's discrete ``'on'``/``'off'`` state through."""
        state_specs = cls._state_specs_for_hass_state( hass_state )
        if state_specs:
            result : Dict[ IntegrationKey, str ] = {}
            for spec in state_specs:
                value = cls._extract_substate_value( hass_state, spec )
                if value is None:
                    continue
                substate_key = cls._substate_integration_key(
                    hass_state = hass_state,
                    suffix = spec.suffix,
                )
                result[ substate_key ] = value
                continue
            return result
        raw_percentage = hass_state.attributes.get( HassApi.PERCENTAGE_ATTR )
        if raw_percentage is None:
            return cls._passthrough_to_sensor_value_map( hass_state )
        try:
            percentage = int( float( raw_percentage ) )
        except ( TypeError, ValueError ):
            return {}
        return { cls.hass_state_to_integration_key( hass_state ) : str( percentage ) }

    @classmethod
    def _camera_to_sensor_value_map(
            cls, hass_state : HassState ) -> Dict[ IntegrationKey, str ]:
        """Camera domain: pure substate decomposition. The primary
        ``state`` substate carries idle / streaming / recording; the
        ``motion_detection`` substate carries the toggle when HA
        reports the attribute."""
        result : Dict[ IntegrationKey, str ] = {}
        for spec in cls._state_specs_for_hass_state( hass_state ):
            value = cls._extract_substate_value( hass_state, spec )
            if value is None:
                continue
            substate_key = cls._substate_integration_key(
                hass_state = hass_state,
                suffix = spec.suffix,
            )
            result[ substate_key ] = value
            continue
        return result

    @classmethod
    def _climate_to_sensor_value_map(
            cls, hass_state : HassState ) -> Dict[ IntegrationKey, str ]:
        """Climate domain: a thermostat that declares
        ``hvac_modes`` decomposes into substates (current
        temperature, mode, action, setpoint(s)) — each value
        lands at its suffix-keyed integration_key. Climate
        entities lacking ``hvac_modes`` (rare but allowed by
        HA's contract) fall through to passthrough behavior."""
        state_specs = cls._state_specs_for_hass_state( hass_state )
        if not state_specs:
            return cls._passthrough_to_sensor_value_map( hass_state )
        result : Dict[ IntegrationKey, str ] = {}
        for spec in state_specs:
            value = cls._extract_substate_value( hass_state, spec )
            if value is None:
                continue
            substate_key = cls._substate_integration_key(
                hass_state = hass_state,
                suffix = spec.suffix,
            )
            result[ substate_key ] = value
            continue
        return result

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
        canonical ``ControlIntent``. ``HassServiceComposer`` maps
        the intent + domain to the right HA service name."""
        lower = hi_control_value.lower()
        if lower == str( EntityStateValue.ON ) or lower in ( 'true', '1' ):
            return ControlIntent.ON
        if lower == str( EntityStateValue.OFF ) or lower in ( 'false', '0' ):
            return ControlIntent.OFF
        if lower == str( EntityStateValue.OPEN ):
            return ControlIntent.OPEN
        if lower == str( EntityStateValue.CLOSED ) or lower == 'close':
            return ControlIntent.CLOSE
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

        if substate == HassApi.BRIGHTNESS_ATTR:
            try:
                numeric_value = cls.to_ha_numeric_parameter_value( hi_control_value )
            except ( ValueError, TypeError ):
                raise ValueError(
                    f'Invalid brightness value: {hi_control_value}'
                )
            return HassServiceComposer.for_numeric_best_effort(
                domain = domain,
                hass_substate_id = parent_entity_id,
                numeric_value = numeric_value,
            )

        if substate == HassApi.COLOR_MODE_COLOR_TEMP:
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
            partner_int_key = cls._substate_integration_key_for_suffix(
                parent_entity_id = parent_entity_id,
                suffix = partner_substate,
            )
            partner_value_str = IntegrationConverterHelper.get_latest_state_values(
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

        if substate == 'speed':
            try:
                numeric_value = cls.to_ha_numeric_parameter_value( hi_control_value )
            except ( ValueError, TypeError ):
                raise ValueError(
                    f'Invalid fan speed value: {hi_control_value}'
                )
            return HassServiceComposer.for_percentage(
                domain = domain,
                hass_substate_id = parent_entity_id,
                percentage = numeric_value,
                domain_payload = { 'set_service': HassApi.SET_PERCENTAGE_SERVICE },
            )

        if substate == HassApi.OSCILLATING_ATTR:
            return HassServiceComposer.for_oscillating(
                domain = domain,
                hass_substate_id = parent_entity_id,
                oscillating = cls.to_ha_on_off_intent( hi_control_value ) == ControlIntent.ON,
            )

        if substate == HassApi.DIRECTION_ATTR:
            return HassServiceComposer.for_direction(
                domain = domain,
                hass_substate_id = parent_entity_id,
                direction = hi_control_value,
            )

        if substate == HassApi.PRESET_MODE_ATTR:
            return HassServiceComposer.for_preset_mode(
                domain = domain,
                hass_substate_id = parent_entity_id,
                preset_mode = hi_control_value,
            )

        if substate == 'target_temperature':
            try:
                entity_state_temperature = cls.to_ha_numeric_parameter_value(
                    hi_control_value,
                )
            except ( ValueError, TypeError ):
                raise ValueError(
                    f'Invalid temperature value: {hi_control_value}'
                )
            substate_integration_key = cls._substate_integration_key_for_suffix(
                parent_entity_id = parent_entity_id,
                suffix = substate,
            )
            temperature = IntegrationConverterHelper.from_entity_state_value(
                entity_state_value = entity_state_temperature,
                external_unit = domain_payload.get( 'native_temperature_unit' ),
                integration_key = substate_integration_key,
            )
            return HassServiceComposer.for_temperature(
                domain = domain,
                hass_substate_id = parent_entity_id,
                temperature = temperature,
                domain_payload = { 'set_service': HassApi.SET_TEMPERATURE_SERVICE },
            )

        if substate in ( HassApi.TARGET_TEMP_LOW_ATTR, HassApi.TARGET_TEMP_HIGH_ATTR ):
            try:
                changed_value = cls.to_ha_numeric_parameter_value( hi_control_value )
            except ( ValueError, TypeError ):
                raise ValueError(
                    f'Invalid {substate} value: {hi_control_value}'
                )
            partner_substate = (
                HassApi.TARGET_TEMP_HIGH_ATTR if substate == HassApi.TARGET_TEMP_LOW_ATTR
                else HassApi.TARGET_TEMP_LOW_ATTR
            )
            partner_int_key = cls._substate_integration_key_for_suffix(
                parent_entity_id = parent_entity_id,
                suffix = partner_substate,
            )
            partner_value_str = IntegrationConverterHelper.get_latest_state_values(
                integration_keys = [ partner_int_key ],
            ).get( partner_int_key )
            try:
                partner_value = (
                    float( partner_value_str ) if partner_value_str is not None else None
                )
            except ( ValueError, TypeError ):
                partner_value = None
            # Defaults when the partner has no cached value yet
            # (e.g., before the first poll cycle): pick a sensible
            # ordering around the changed value so HA's call doesn't
            # reject low > high. Both values are in HI's stored unit
            # (cached values came through the same boundary-converted
            # translation path); we convert both to external together.
            if substate == HassApi.TARGET_TEMP_LOW_ATTR:
                entity_state_low = changed_value
                entity_state_high = (
                    partner_value
                    if partner_value is not None and partner_value >= entity_state_low
                    else entity_state_low
                )
            else:
                entity_state_high = changed_value
                entity_state_low = (
                    partner_value
                    if partner_value is not None and partner_value <= entity_state_high
                    else entity_state_high
                )
            external_unit = domain_payload.get( 'native_temperature_unit' )
            substate_integration_key = cls._substate_integration_key_for_suffix(
                parent_entity_id = parent_entity_id,
                suffix = substate,
            )
            low = IntegrationConverterHelper.from_entity_state_value(
                entity_state_value = entity_state_low,
                external_unit = external_unit,
                integration_key = substate_integration_key,
            )
            high = IntegrationConverterHelper.from_entity_state_value(
                entity_state_value = entity_state_high,
                external_unit = external_unit,
                integration_key = substate_integration_key,
            )
            return HassServiceComposer.for_temperature_range(
                domain = domain,
                hass_substate_id = parent_entity_id,
                low = low,
                high = high,
            )

        if substate == HassApi.HVAC_MODE_ATTR:
            return HassServiceComposer.for_hvac_mode(
                domain = domain,
                hass_substate_id = parent_entity_id,
                hvac_mode = hi_control_value,
            )

        if substate == HassApi.FAN_MODE_ATTR:
            return HassServiceComposer.for_fan_mode(
                domain = domain,
                hass_substate_id = parent_entity_id,
                fan_mode = hi_control_value,
            )

        if substate == HassApi.MOTION_DETECTION_ATTR:
            return HassServiceComposer.for_motion_detection(
                domain = domain,
                hass_substate_id = parent_entity_id,
                enabled = ( cls.to_ha_on_off_intent( hi_control_value )
                            == ControlIntent.ON ),
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

        if cls._payload_supports_numeric_control( domain_payload ):
            try:
                numeric_value = cls.to_ha_numeric_parameter_value( hi_control_value )
            except ( ValueError, TypeError ):
                numeric_value = None
            if numeric_value is not None:
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
        try:
            numeric_value = cls.to_ha_numeric_parameter_value( hi_control_value )
        except ( ValueError, TypeError ):
            intent = cls.to_ha_on_off_intent( hi_control_value )
            return HassServiceComposer.for_on_off_best_effort(
                domain = domain,
                hass_substate_id = hass_substate_id,
                intent = intent,
            )
        return HassServiceComposer.for_numeric_best_effort(
            domain = domain,
            hass_substate_id = hass_substate_id,
            numeric_value = numeric_value,
        )

    @classmethod
    def _payload_supports_numeric_control( cls, domain_payload : dict ) -> bool:
        return ( domain_payload.get( 'supports_brightness', False )
                 or domain_payload.get( 'set_service' ) is not None )
