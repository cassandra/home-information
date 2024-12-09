from hi.apps.alert.enums import AlarmLevel
from hi.apps.common.enums import LabeledEnum
from hi.apps.config.enums import SubsystemAttributeType


class AudioSignal(LabeledEnum):

    INFO      = ( 'Info'     , '', SubsystemAttributeType.INFO_AUDIO_FILE )
    WARNING   = ( 'Warning'  , '', SubsystemAttributeType.WARNING_AUDIO_FILE)
    CRITICAL  = ( 'Critical' , '', SubsystemAttributeType.CRITICAL_AUDIO_FILE )
    
    def __init__( self,
                  label                     : str,
                  description               : str,
                  subsystem_attribute_type  : str ):
        super().__init__( label, description )
        self.subsystem_attribute_type = subsystem_attribute_type
        return

    @classmethod
    def from_alarm_level( cls, alarm_level : AlarmLevel ) -> 'AudioSignal':
        if alarm_level == AlarmLevel.INFO:
            return cls.INFO
        if alarm_level == AlarmLevel.WARNING:
            return cls.WARNING
        if alarm_level == AlarmLevel.CRITICAL:
            return cls.CRITICAL
        return None
    
