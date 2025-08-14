from hi.apps.common.enums import LabeledEnum
from hi.apps.common.utils import get_absolute_static_path


class AudioFile(LabeledEnum):
    # Predefined sounds in statically served files.

    BICYCLE_BELL       = ( 'Bicycle Bell'      , '' , 'bicycle-bell.wav' )
    BOING_SPRING       = ( 'Boing Spring'      , '' , 'boing-spring.wav' )
    BUZZER             = ( 'Buzzer'            , '' , 'buzzer.wav' )
    CHIME              = ( 'Chime'             , '' , 'chime.wav' )
    CRITICAL           = ( 'Critical'          , '' , 'critical.wav' )
    FINAL_REVEAL_BELL  = ( 'Final Reveal Bell' , '' , 'final-reveal-bell.wav' )
    INDUSTRIAL_ALARM   = ( 'Industrial Alarm'  , '' , 'industrial-alarm.wav' )
    INFO               = ( 'Info'              , '' , 'info.wav' )
    STORE_DOOR_CHIME   = ( 'Store Door Chime'  , '' , 'store-door-chime.wav' )
    TORNADO_SIREN      = ( 'Tornado Siren'     , '' , 'tornado-siren.wav' )
    WARNING            = ( 'Warning'           , '' , 'warning.wav' )
    WEATHER_ALERT      = ( 'Weather Alert'     , '' , 'weather-alert.wav' )

    @property
    def url(self):
        return get_absolute_static_path( f'audio/{self.base_filename}' )
    
    def __init__( self,
                  label             : str,
                  description       : str,
                  base_filename     : str ):
        super().__init__( label, description )
        self.base_filename = base_filename
        return