import logging
import re
from typing import Dict

from .hass_models import HassState, HassDevice

logger = logging.getLogger(__name__)


class HassFilter:
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
        'weather',
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
