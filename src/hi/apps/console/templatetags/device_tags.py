from typing import Dict, List, TypeVar

from django import template

from hi.apps.console import device_markup
from hi.apps.console.device_capabilities import DeviceCapabilitiesCodec

register = template.Library()

T = TypeVar( 'T' )


@register.simple_tag
def external_link_attrs():
    return device_markup.external_link_attrs()


@register.simple_tag
def device_requires_attrs( *capability_names, handlers = '' ):
    """
    Usage: {% device_requires_attrs 'keyboard' handlers='on-screen-keyboard' %}

    Names are the external vocabulary of DeviceCapabilitiesCodec;
    ``handlers`` is space-separated. Unknown names fail the render, since
    a misspelled declaration would otherwise silently gate nothing.
    """
    if not capability_names:
        raise ValueError( 'device_requires_attrs needs at least one capability name' )
    return device_markup.device_requires_attrs(
        capabilities = _resolve_names( capability_names, DeviceCapabilitiesCodec.NAME_TO_CAPABILITY ),
        handlers = _resolve_names( handlers.split(), DeviceCapabilitiesCodec.NAME_TO_HANDLER ),
    )


def _resolve_names( names : List[ str ], name_to_value : Dict[ str, T ] ) -> List[ T ]:
    unknown_names = [ name for name in names if name not in name_to_value ]
    if unknown_names:
        raise ValueError( f'Unknown device requirement names: {unknown_names}' )
    return [ name_to_value[ name ] for name in names ]
