from hi.apps.common.enums import LabeledEnum


class SensorType(LabeledEnum):

    DEFAULT              = ( 'Default', '' )  # EntityState will define behavior

    
class SensorValue(LabeledEnum):

    MOVEMENT_ACTIVE    = ( 'Active', '' )
    MOVEMENT_IDLE      = ( 'Idle', '' )

    BINARY_ON          = ( 'On', '' )
    BINARY_OFF         = ( 'Off', '' )
    
    OPEN               = ( 'Open', '' )
    CLOSE              = ( 'Close', '' )
