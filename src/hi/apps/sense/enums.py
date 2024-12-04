from hi.apps.common.enums import LabeledEnum


class SensorType(LabeledEnum):

    DEFAULT              = ( 'Default', '' )  # EntityState will define behavior

    
class SensorValue(LabeledEnum):

    ACTIVE         = ( 'Active', '' )
    IDLE           = ( 'Idle', '' )

    ON             = ( 'On', '' )
    OFF            = ( 'Off', '' )
    
    OPEN           = ( 'Open', '' )
    CLOSED         = ( 'Closed', '' )

    CONNECTED      = ( 'Connected', '' )
    DISCONNECTED   = ( 'Disconnected', '' )

    HIGH           = ( 'High', '' )
    LOW            = ( 'Low', '' )
