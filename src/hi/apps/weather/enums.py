from hi.apps.common.enums import LabeledEnum


class DataSource( LabeledEnum ):

    NWS                  = ( 'National Weather Service', '' )
    OPEN_METEO           = ( 'Open Meteo', '' )

    
class SkyCondition( LabeledEnum ):

    CLEAR          = ( 'Clear'         , ''       , 'Sunny',
                       'img/weather/sky-clear.svg'  , 'img/weather/sky-sunny.svg' )
    MOSTLY_CLEAR   = ( 'Mostly Clear'  , '' , 'Mostly Sunny',
                       'img/weather/sky-partly-cloudy.svg'  , 'img/weather/sky-partly-sunny.svg' )
    PARTLY_CLOUDY  = ( 'Partly Cloudy' , '' , 'Partly Sunny',
                       'img/weather/sky-partly-cloudy.svg'  , 'img/weather/sky-partly-sunny.svg' )
    MOSTLY_CLOUDY  = ( 'Mostly Cloudy' , '' , 'Mostly Cloudy',
                       'img/weather/sky-mostly-cloudy.svg'  , 'img/weather/sky-mostly-cloudy.svg' )
    CLOUDY         = ( 'Cloudy'        , '' , 'Cloudy',
                       'img/weather/sky-cloudy.svg'  , 'img/weather/sky-cloudy.svg' )

    @classmethod
    def from_cloud_cover( cls, cloud_cover_percent : float ):
        if cloud_cover_percent <= 12.5:
            return cls.CLEAR
        if cloud_cover_percent <= 37.5:
            return cls.MOSTLY_CLEAR
        if cloud_cover_percent <= 62.5:
            return cls.PARTLY_CLOUDY
        if cloud_cover_percent <= 87.5:
            return cls.MOSTLY_CLOUDY
        return cls.CLOUDY

    def __init__( self,
                  label              : str,
                  description        : str,
                  day_label          : str,
                  icon_filename      : str,
                  day_icon_filename  : str ):
        super().__init__( label, description )
        self.day_label = day_label
        self.icon_filename = icon_filename
        self.day_icon_filename = day_icon_filename
        return

    
class MoonPhase( LabeledEnum ):

    NEW_MOON         = ( 'New Moon'        , '' , 'img/weather/moon-new.svg' )
    WAXING_CRESCENT  = ( 'Waxing Crescent' , '' , 'img/weather/moon-waxing-crescent.svg' )
    FIRST_QUARTER    = ( 'First Quarter'   , '' , 'img/weather/moon-first-quarter.svg' )
    WAXING_GIBBOUS   = ( 'Waxing Gibbous'  , '' , 'img/weather/moon-waxing-gibbous.svg' )
    FULL_MOON        = ( 'Full Moon'       , '' , 'img/weather/moon-full.svg' )
    WANING_GIBBOUS   = ( 'Waning Gibbous'  , '' , 'img/weather/moon-waning-gibbous.svg' )
    LAST_QUARTER     = ( 'Last Quarter'    , '' , 'img/weather/moon-last-quarter.svg' )
    WANING_CRESCENT  = ( 'Waning Crescent' , '' , 'img/weather/moon-waning-crescent.svg' )

    @classmethod
    def from_illumination( cls, illumination_percent : float, is_waxing : bool ):
        if is_waxing:
            if illumination_percent <= 1:
                return cls.NEW_MOON
            if illumination_percent <= 49:
                return cls.WAXING_CRESCENT
            if illumination_percent <= 51:
                return cls.FIRST_QUARTER
            if illumination_percent <= 99:
                return cls.WAXING_GIBBOUS
            return cls.FULL_MOON
        else:
            if illumination_percent <= 1:
                return cls.NEW_MOON
            if illumination_percent <= 49:
                return cls.WANING_CRESCENT
            if illumination_percent <= 51:
                return cls.LAST_QUARTER
            if illumination_percent <= 99:
                return cls.WANING_GIBBOUS
            return cls.FULL_MOON

    def __init__( self,
                  label          : str,
                  description    : str,
                  icon_filename  : str ):
        super().__init__( label, description )
        self.icon_filename = icon_filename
        return
            
            
class WeatherCodeEnum( LabeledEnum ):
    """ Base class for various weather code enums. """

    def __init__( self,
                  label        : str,
                  description  : str,
                  nws_code     : str ):
        super().__init__( label, description )
        self.nws_code = nws_code
        return


class AlertCategory( WeatherCodeEnum ):
    METEOROLOGICAL  = ( 'Meteorological' , 'e.g., hurricanes, tornadoes, blizzards'  , 'Met' )
    GEOPHYSICAL     = ( 'Geophysical'    , 'e.g., earthquakes, tsunamis'             , 'Geo' )
    PUBLIC_SAFETY   = ( 'Public Safety'  , 'e.g., child abduction alerts'            , 'Safety' )
    SECURITY        = ( 'Security'       , 'e.g., terrorist threats'                 , 'Security' )
    RESCUE          = ( 'Rescue'         , 'e.g., search and rescue'                 , 'Rescue' )
    FIRE            = ( 'Fire'           , 'e.g., wildfire warnings'                 , 'Fire' )
    HEALTH          = ( 'Health'         , 'e.g., air quality alerts'                , 'Health' )
    ENVIRONMENTAL   = ( 'Environmental'  , 'e.g., pollution warnings'                , 'Env' )
    TRANSPORTATION  = ( 'Transportation' , 'e.g., road closures, marine warnings'    , 'Transport' )
    INFRASTRUCTURE  = ( 'Infrastructure' , 'e.g., power outages'                     , 'Infra' )
    OTHER           = ( 'Other'          , 'Alerts not fitting in other categories.' , 'Other' )
    

class AlertSeverity( WeatherCodeEnum ):
    EXTREME      = ( 'Extreme'    , ''  , 'Extreme' )
    SEVERE       = ( 'Severe'     , ''  , 'Severe' )
    MODERATE     = ( 'Moderate'   , ''  , 'Moderate' )
    MINOR        = ( 'Minor'      , ''  , 'Minor' )


class AlertUrgency( WeatherCodeEnum ):
    IMMEDIATE    = ( 'Immediate'  , ''  , 'Immediate' )
    EXPECTED     = ( 'Expected'   , ''  , 'Expected' )
    FUTURE       = ( 'Future'     , ''  , 'Future' )
    UNKNOWN      = ( 'Unknown'    , ''  , 'Unknown' )

    
class AlertCertainty( WeatherCodeEnum ):
    OBSERVED     = ( 'Observed'   , ''  , 'Observed' )
    LIKELY       = ( 'Likely'     , ''  , 'Likely' )
    POSSIBLE     = ( 'Possible'   , ''  , 'Possible' )
    UNLIKELY     = ( 'Unlikely'   , ''  , 'Unlikely' )

    
class AlertStatus( WeatherCodeEnum ):
    ACTUAL    = ( 'Actual'    , ' A real-time alert currently in effect. '                 , 'Actual' )
    EXERCISE  = ( 'Exercise'  , 'A test or drill alert (not an actual event).'             , 'Exercise' )
    SYSTEM    = ( 'System'    , 'Internal system message (not a public alert).'            , 'System' )
    TEST      = ( 'Test'      , 'A test message (e.g., weekly NOAA Weather Radio tests).'  , 'Test' )
    DRAFT     = ( 'Draft'     , 'An alert being prepared but not yet issued.'              , 'Draft' )


