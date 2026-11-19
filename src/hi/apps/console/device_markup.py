from typing import Sequence

from django.utils.html import format_html
from django.utils.safestring import SafeString

from hi.constants import DIVID

from .device_capabilities import DeviceCapabilitiesCodec
from .enums import DeviceCapability, DeviceRequirementHandler


def device_requires_attrs(
        capabilities : Sequence[ DeviceCapability ],
        handlers     : Sequence[ DeviceRequirementHandler ] = () ) -> SafeString:
    """
    Element attributes declaring the capabilities it needs from the
    device and, optionally, the in-app handlers that can stand in for a
    missing one. A missing capability without a loaded handler blocks
    the action with an explanation instead (see device.js).
    """
    requires_attr = format_html(
        '{}="{}"',
        DIVID['DEVICE_REQUIRES_ATTR'],
        ' '.join( DeviceCapabilitiesCodec.CAPABILITY_TO_NAME[ capability ]
                  for capability in capabilities ),
    )
    if not handlers:
        return requires_attr
    return format_html(
        '{} {}="{}"',
        requires_attr,
        DIVID['DEVICE_REQUIRES_HANDLER_ATTR'],
        ' '.join( DeviceCapabilitiesCodec.HANDLER_TO_NAME[ handler ]
                  for handler in handlers ),
    )


def external_link_attrs() -> SafeString:
    """
    Anchor attributes for a link that leaves the app. It opens in a new
    tab, which needs browser navigation.
    """
    return format_html(
        'target="_blank" rel="noopener noreferrer" {}',
        device_requires_attrs( [ DeviceCapability.BROWSER_NAV ] ),
    )
