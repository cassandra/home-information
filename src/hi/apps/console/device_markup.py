from django.utils.html import format_html
from django.utils.safestring import SafeString

from hi.constants import DIVID

from .device_capabilities import DeviceCapabilitiesCodec
from .enums import DeviceCapability


def external_link_attrs() -> SafeString:
    """
    Anchor attributes for a link that leaves the app. It opens in a new
    tab, which needs browser navigation; on a device without it, the
    click is blocked with an explanation instead (see device.js).
    """
    return format_html(
        'target="_blank" rel="noopener noreferrer" {}="{}"',
        DIVID['DEVICE_REQUIRES_ATTR'],
        DeviceCapabilitiesCodec.CAPABILITY_TO_NAME[ DeviceCapability.BROWSER_NAV ],
    )
