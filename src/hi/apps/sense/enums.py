from hi.apps.common.enums import LabeledEnum


class SensorType(LabeledEnum):

    DISCRETE_VALUE       = ( 'Discrete Value', '' )  # Generic for devices
    CONTINUOUS_VALUE     = ( 'Continuous Value', '' )  # Generic for device controls
    BLOB                 = ( 'Blob', '' )  # For custom, large chunks of text, video streams


    # ??? !!! Are the below not needed as just specilizations for each device type?
    # Is there value in having predefined ones for convenience?

    
    BANDWIDTH_USAGE      = ( 'Bandwidth Usage', '' )
    ELECTRIC_USAGE       = ( 'Electric Usage', '' )
    WATER_FLOW           = ( 'Water Flow', '' )
    
    # Area Sensors
    VISUAL_DYNAMIC       = ( 'Visual Dynamic', '' )  # For video stream
    VISUAL_STATIC        = ( 'Visual Static', '' )  # For static images
    MOTION               = ( 'Motion', '' )
    CONTACT              = ( 'Contact', '' )  # For open/close or for connectivity check

    
class SensedAreaType(LabeledEnum):

    VISIBLE_CONTINUOUS  = ( 'Visible', '' )  # Video stream
    VISIBLE_DISCRETE    = ( 'Visible Discrete', '' )  # Pictures/Snapshots

    MOVEMENT            = ( 'Movement', '' )
    PRESENCE            = ( 'Presence', '' )
    TEMPERATURE         = ( 'Temperature', '' )
    HUMIDITY            = ( 'Humidity', '' )
    AIR_PRESSURE        = ( 'Air Pressure', '' )
    LIGHT_LEVEL         = ( 'Light Level', '' )
    NOISE_LEVEL         = ( 'Noise Level', '' )

    @property
    def svg_path_style(self):
        raise NotImplementedError()
    
