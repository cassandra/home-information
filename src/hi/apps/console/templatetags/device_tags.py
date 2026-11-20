from django import template

from hi.apps.console import device_markup
from hi.apps.console.device_capabilities import DeviceCapabilitiesCodec

register = template.Library()


@register.simple_tag
def external_link_attrs():
    return device_markup.external_link_attrs()


@register.simple_tag
def device_requires_attrs( *capability_names, handlers = '' ):
    """
    Usage: {% device_requires_attrs 'keyboard' handlers='on-screen-keyboard' %}

    Names are the external vocabulary of DeviceCapabilitiesCodec;
    ``handlers`` is space-separated, matching the attribute it renders.
    Unknown names fail the render, since a misspelled declaration would
    otherwise silently gate nothing.
    """
    return device_markup.device_requires_attrs(
        capabilities = [ DeviceCapabilitiesCodec.capability_for_name( name )
                         for name in capability_names ],
        handlers = [ DeviceCapabilitiesCodec.handler_for_name( name )
                     for name in handlers.split() ],
    )


@register.simple_tag( takes_context = True )
def device_capability_available( context, capability_name ):
    """
    Usage: {% device_capability_available 'keyboard' as device_has_keyboard %}

    For gating markup or assets on what the device has. The name is the
    external vocabulary of DeviceCapabilitiesCodec; unknown names fail.
    """
    capability = DeviceCapabilitiesCodec.capability_for_name( capability_name )
    return context[ 'device_capabilities' ].is_available( capability )
