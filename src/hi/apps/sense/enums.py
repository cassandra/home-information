from hi.apps.common.enums import LabeledEnum


class SensorType(LabeledEnum):

    DEFAULT              = ( 'Default', '' )  # EntityState will define behavior

    
class SensorValue(LabeledEnum):

    MOVEMENT_ACTIVE    = ( 'Active', '' )
    MOVEMENT_IDLE      = ( 'Idle', '' )

    ON                 = ( 'On', '' )
    OFF                = ( 'Off', '' )
    
    OPEN               = ( 'Open', '' )
    CLOSED             = ( 'Closed', '' )

    CONNECTED          = ( 'Connected', '' )
    DISCONNECTED       = ( 'Disconnected', '' )

    HIGH               = ( 'High', '' )
    LOW                = ( 'Low', '' )

    PRESENCE_ACTIVE    = ( 'Active', '' )
    PRESENCE_IDLE      = ( 'Idle', '' )
