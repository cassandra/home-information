from hi.apps.common.enums import LabeledEnum


class ControllerType(LabeledEnum):

    SETTING              = ( 'Setting', '' )  # Generic, discrete value control (incl. on/off)
    SLIDER               = ( 'Slider', '' )  # Continuous value control
    BLOB                 = ( 'Blob', '' )  # For custom or large chunks of text


    
    # ???? !!!! There's another concept / division in here (general v. specific)
    # ControllerState ControllerAction?


    
    HEATER               = ( 'Heater', '' )  # Controls area
    AIR_CONDITIONER      = ( 'Air_Conditioner', '' )  # Controls area
    HUMIDIFIER           = ( 'Humidifier', '' )  # Controls area
    SPINKLER_VALVE       = ( 'Spinkler Valve', '' )  # Controls sprinkler heads
    DOOR_LOCK            = ( 'Door Lock', '' )  # Controls doors
    AUDIO_AMPLIFIER      = ( 'Audio Amplifier', '' )  # Controls SPeaker

    
class ControlledAreaType(LabeledEnum):

    LIGHT        = ( 'Light', '' )
    SOUND        = ( 'Sound', '' )
    TEMPERATURE  = ( 'Temperature', '' )
    HUMIDITY     = ( 'Humidity', '' )
    IRRIGATION   = ( 'Irrigation', '' )

    @property
    def svg_path_style(self):
        raise NotImplementedError()
