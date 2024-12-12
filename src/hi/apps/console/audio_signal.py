from hi.apps.alert.enums import AlarmLevel
from hi.apps.common.enums import LabeledEnum
from hi.apps.console.settings import ConsoleSetting


class AudioSignal(LabeledEnum):

    INFO      = ( 'Info'     , '', ConsoleSetting.CONSOLE_INFO_AUDIO_FILE )
    WARNING   = ( 'Warning'  , '', ConsoleSetting.CONSOLE_WARNING_AUDIO_FILE)
    CRITICAL  = ( 'Critical' , '', ConsoleSetting.CONSOLE_CRITICAL_AUDIO_FILE )
    
    def __init__( self,
                  label             : str,
                  description       : str,
                  console_setting   : ConsoleSetting ):
        super().__init__( label, description )
        self.console_setting = console_setting
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
    
