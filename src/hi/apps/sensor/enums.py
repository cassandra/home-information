from hi.apps.common.enums import LabeledEnum


class SensorType(LabeledEnum):

    CONTINUOUS  = ( 'Continuous', '' )
    DISCRETE    = ( 'Dicrete', '' )

    
class SensedAreaType(LabeledEnum):

    VISIBLE       = ( 'Visible', '' )
    MOTION        = ( 'Motion', '' )
    PRESENCE      = ( 'Presence', '' )
    TEMPERATURE   = ( 'Temperature', '' )
    HUMIDITY      = ( 'Humidity', '' )
    AIR_PRESSURE  = ( 'Air Pressure', '' )
