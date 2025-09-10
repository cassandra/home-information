from hi.apps.common.enums import LabeledEnum


class Theme(LabeledEnum):

    DEFAULT  = ( 'Default', '' )


class DisplayUnits(LabeledEnum):

    IMPERIAL  = ( 'Imperial', '' )
    METRIC    = ( 'Metric', '' )


class VideoDispatchType(LabeledEnum):
    """
    Enum for video dispatch navigation types.
    Used to determine which view to route to when navigating between cameras.
    """
    
    LIVE_STREAM = ('Live Stream', 'Display current live video stream')
    HISTORY_DEFAULT = ('History Default', 'Display most recent history events')
    HISTORY_EARLIER = ('History Earlier', 'Display earlier history events from timestamp')
    HISTORY_LATER = ('History Later', 'Display later history events from timestamp')
