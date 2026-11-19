from hi.apps.common.enums import LabeledEnum


class Theme(LabeledEnum):

    DEFAULT  = ( 'Default', '' )


class DisplayUnits(LabeledEnum):

    IMPERIAL  = ( 'Imperial', '' )
    METRIC    = ( 'Metric', '' )


class DeviceCapability(LabeledEnum):
    """
    Independent capabilities of the client device. Each describes the
    device; none instructs the server. The description is the
    user-facing reason shown when an action needs a missing capability.
    """

    KEYBOARD     = ( 'Keyboard',
                     'This device has no keyboard for typing.' )
    BROWSER_NAV  = ( 'Browser Navigation',
                     'This device cannot open or return from other browser pages or tabs.' )
    LOCAL_FILES  = ( 'Local Files',
                     'This device has no user files to choose from or save to.' )


class VideoDispatchType(LabeledEnum):
    """
    Enum for video dispatch navigation types.
    Used to determine which view to route to when navigating between cameras.
    """
    
    LIVE_STREAM = ('Live Stream', 'Display current live video stream')
    HISTORY_DEFAULT = ('History Default', 'Display most recent history events')
    HISTORY_EARLIER = ('History Earlier', 'Display earlier history events from timestamp')
    HISTORY_LATER = ('History Later', 'Display later history events from timestamp')
