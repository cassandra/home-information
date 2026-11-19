from dataclasses import dataclass, field
from typing import Dict, Mapping, Optional

from .enums import DeviceCapability


@dataclass( frozen = True )
class DeviceCapabilities:
    """
    The capabilities of the requesting device. Only explicit declarations
    are stored; any capability not declared is present, so a device that
    never declared anything behaves exactly as before capabilities existed.
    """

    declared : Mapping[ DeviceCapability, bool ] = field( default_factory = dict )

    def is_available( self, capability : DeviceCapability ) -> bool:
        return self.declared.get( capability, True )

    @property
    def is_default( self ) -> bool:
        return not self.declared

    def with_declarations(
            self,
            declarations : Mapping[ DeviceCapability, Optional[ bool ] ] ) -> 'DeviceCapabilities':
        """ A None declaration clears the capability back to its default. """
        declared = dict( self.declared )
        for capability, is_available in declarations.items():
            if is_available is None:
                declared.pop( capability, None )
            else:
                declared[ capability ] = is_available
            continue
        return DeviceCapabilities( declared = declared )


class DeviceCapabilitiesCodec:
    """
    The external vocabulary for capabilities, shared by URL query
    parameters, the persisted cookie and the JavaScript client. All
    conversions go through these explicit tables.
    """

    CAPABILITY_TO_NAME = {
        DeviceCapability.KEYBOARD     : 'keyboard',
        DeviceCapability.BROWSER_NAV  : 'browser_nav',
        DeviceCapability.LOCAL_FILES  : 'local_files',
    }
    NAME_TO_CAPABILITY = { name: capability for capability, name in CAPABILITY_TO_NAME.items() }

    # None means "clear back to default".
    VALUE_TO_AVAILABILITY = {
        'none'     : False,
        'present'  : True,
        'default'  : None,
    }
    AVAILABILITY_TO_VALUE = {
        False : 'none',
        True  : 'present',
    }

    COOKIE_ENTRY_SEPARATOR = '|'
    COOKIE_PAIR_SEPARATOR = ':'

    @classmethod
    def declarations_from_query_params(
            cls,
            query_params : Mapping[ str, str ] ) -> Dict[ DeviceCapability, Optional[ bool ] ]:
        """ Unrecognized names and values are ignored. """
        declarations = dict()
        for name, capability in cls.NAME_TO_CAPABILITY.items():
            value = query_params.get( name )
            if value in cls.VALUE_TO_AVAILABILITY:
                declarations[ capability ] = cls.VALUE_TO_AVAILABILITY[ value ]
            continue
        return declarations

    @classmethod
    def from_cookie_value( cls, cookie_value : Optional[ str ] ) -> DeviceCapabilities:
        """ Malformed or unrecognized entries are ignored. """
        declared = dict()
        if cookie_value:
            for entry in cookie_value.split( cls.COOKIE_ENTRY_SEPARATOR ):
                name, _, value = entry.partition( cls.COOKIE_PAIR_SEPARATOR )
                capability = cls.NAME_TO_CAPABILITY.get( name )
                if capability and ( value in cls.AVAILABILITY_TO_VALUE.values() ):
                    declared[ capability ] = cls.VALUE_TO_AVAILABILITY[ value ]
                continue
        return DeviceCapabilities( declared = declared )

    @classmethod
    def to_cookie_value( cls, device_capabilities : DeviceCapabilities ) -> str:
        return cls.COOKIE_ENTRY_SEPARATOR.join([
            f'{cls.CAPABILITY_TO_NAME[ capability ]}'
            f'{cls.COOKIE_PAIR_SEPARATOR}'
            f'{cls.AVAILABILITY_TO_VALUE[ is_available ]}'
            for capability, is_available in device_capabilities.declared.items()
        ])

    @classmethod
    def to_client_dict( cls, device_capabilities : DeviceCapabilities ) -> Dict[ str, bool ]:
        """ Every capability by external name, for the JavaScript client. """
        return {
            name: device_capabilities.is_available( capability )
            for capability, name in cls.CAPABILITY_TO_NAME.items()
        }
