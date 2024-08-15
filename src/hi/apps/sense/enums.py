from hi.apps.common.enums import LabeledEnum


class SensorType(LabeledEnum):

    DISCRETE_VALUE       = ( 'Discrete Value', '' )  # Generic for devices
    CONTINUOUS_VALUE     = ( 'Continuous Value', '' )  # Generic for device controls
    BLOB                 = ( 'Blob', '' )  # For custom or large chunks of text


    # ??? !!! Are the below not needed as just specilizations for each device type?

    
    BANDWIDTH_USAGE      = ( 'Bandwidth Usage', '' )
    ELECTRIC_USAGE       = ( 'Electric Usage', '' )
    WATER_FLOW           = ( 'Water Flow', '' )
    
    # Area Sensors
    VISUAL_DYNAMIC       = ( 'Visual Dynamic', '' )  # For video stream
    VISUAL_STATIC        = ( 'Visual Static', '' )  # For static images
    MOTION               = ( 'Motion', '' )
    CONTACT              = ( 'Contact', '' )  # For open/close or for connectivity check
    TEMPERATURE          = ( 'Thermometer', '' )
    HUMIDITY             = ( 'Humidity', '' )
    AIR_PRESSURE         = ( 'Air Pressure', '' )
    LIGHT_LEVEL          = ( 'Light Level', '' )
    PRESENCE             = ( 'Presence', '' )
    NOISE_LEVEL          = ( 'Noise Level', '' )

    
class SensedAreaType(LabeledEnum):

    VISIBLE       = ( 'Visible', '' )
    MOTION        = ( 'Motion', '' )
    PRESENCE      = ( 'Presence', '' )
    TEMPERATURE   = ( 'Temperature', '' )
    HUMIDITY      = ( 'Humidity', '' )
    AIR_PRESSURE  = ( 'Air Pressure', '' )

    @property
    def svg_path_style(self):
        raise NotImplementedError()
    
