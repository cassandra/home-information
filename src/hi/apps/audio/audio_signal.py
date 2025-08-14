from hi.apps.alert.enums import AlarmLevel, AlarmSource
from hi.apps.common.enums import LabeledEnum
from hi.apps.weather.enums import WeatherEventType
from .settings import AudioSetting


class AudioSignal(LabeledEnum):
    """
    Enhanced audio signal system that differentiates between weather and system alerts.
    
    This replaces the console AudioSignal to support weather-specific audio configuration
    while maintaining compatibility with existing alarm level-based audio.
    """
    
    # Event Alert Signals
    EVENT_INFO      = ( 'EventInfo'     , '', AudioSetting.EVENT_INFO_AUDIO_FILE )
    EVENT_WARNING   = ( 'EventWarning'  , '', AudioSetting.EVENT_WARNING_AUDIO_FILE )
    EVENT_CRITICAL  = ( 'EventCritical' , '', AudioSetting.EVENT_CRITICAL_AUDIO_FILE )
    
    # Weather Alert Signals
    WEATHER_INFO     = ( 'WeatherInfo'    , '', AudioSetting.WEATHER_INFO_AUDIO_FILE )
    WEATHER_WARNING  = ( 'WeatherWarning' , '', AudioSetting.WEATHER_WARNING_AUDIO_FILE )
    WEATHER_CRITICAL = ( 'WeatherCritical', '', AudioSetting.WEATHER_CRITICAL_AUDIO_FILE )
    
    # Special Weather Event Signals
    WEATHER_TORNADO  = ( 'TornadoAlert'   , '', AudioSetting.WEATHER_TORNADO_AUDIO_FILE )
    
    # Console System Status Signals
    CONSOLE_WARNING  = ( 'ConsoleWarning' , '', AudioSetting.CONSOLE_WARNING_AUDIO_FILE )
    CONSOLE_INFO     = ( 'ConsoleInfo'    , '', AudioSetting.CONSOLE_INFO_AUDIO_FILE )
    
    def __init__( self,
                  label             : str,
                  description       : str,
                  audio_setting     : AudioSetting ):
        super().__init__( label, description )
        self.audio_setting = audio_setting
        return

    @classmethod
    def from_alarm_attributes( cls, alarm_level : AlarmLevel, alarm_source : AlarmSource, alarm_type : str ) -> 'AudioSignal':
        """
        Map alarm attributes to appropriate audio signal.
        
        Args:
            alarm_level: The alarm level (INFO, WARNING, CRITICAL)
            alarm_source: The alarm source (determines weather vs event)
            alarm_type: The specific alarm type (e.g., WeatherEventType.TORNADO.name for special handling)
            
        Returns:
            Appropriate AudioSignal enum value or None
        """
        # Special handling for specific weather event types
        if alarm_source == AlarmSource.WEATHER and alarm_type:
            # Tornado gets special treatment regardless of level
            if alarm_type == WeatherEventType.TORNADO.name:
                return cls.WEATHER_TORNADO
        
        # Weather alerts get weather-specific signals
        if alarm_source == AlarmSource.WEATHER:
            if alarm_level == AlarmLevel.INFO:
                return cls.WEATHER_INFO
            elif alarm_level == AlarmLevel.WARNING:
                return cls.WEATHER_WARNING
            elif alarm_level == AlarmLevel.CRITICAL:
                return cls.WEATHER_CRITICAL
        
        # All other alerts get event signals
        else:
            if alarm_level == AlarmLevel.INFO:
                return cls.EVENT_INFO
            elif alarm_level == AlarmLevel.WARNING:
                return cls.EVENT_WARNING
            elif alarm_level == AlarmLevel.CRITICAL:
                return cls.EVENT_CRITICAL
        
        return None

