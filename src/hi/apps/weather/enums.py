from hi.apps.common.enums import LabeledEnum


class WeatherSource( LabeledEnum ):

    NWS                  = ( 'National Weather Service', '' )
    OPEN_METEO           = ( 'Open Meteo', '' )


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


