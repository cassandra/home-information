from hi.apps.common.enums import LabeledEnum


class SensorType(LabeledEnum):

    DEFAULT              = ( 'Default', '' )  # EntityState will define behavior

    
class SensorValue(LabeledEnum):

    MOVEMENT_ACTIVE    = ( 'Active', '' )
    MOVEMENT_IDLE      = ( 'Idle', '' )
