from hi.apps.common.enums import LabeledEnum

    
class SkyCondition( LabeledEnum ):
    """ Two visual representations: one for daytime and one for nighttime """
    
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
        """ Thresholds are balanced for people's perceptions, not technicla deifnitions. """
        if is_waxing:
            if illumination_percent <= 3:
                return cls.NEW_MOON
            if illumination_percent < 47:
                return cls.WAXING_CRESCENT
            if illumination_percent <= 53:
                return cls.FIRST_QUARTER
            if illumination_percent < 97:
                return cls.WAXING_GIBBOUS
            return cls.FULL_MOON
        else:
            if illumination_percent <= 3:
                return cls.NEW_MOON
            if illumination_percent < 47:
                return cls.WANING_CRESCENT
            if illumination_percent <= 53:
                return cls.LAST_QUARTER
            if illumination_percent < 97:
                return cls.WANING_GIBBOUS
            return cls.FULL_MOON

    def __init__( self,
                  label          : str,
                  description    : str,
                  icon_filename  : str ):
        super().__init__( label, description )
        self.icon_filename = icon_filename
        return
            
            
class AlertCategory( LabeledEnum ):
    METEOROLOGICAL  = ( 'Meteorological' , 'e.g., hurricanes, tornadoes, blizzards' )
    GEOPHYSICAL     = ( 'Geophysical'    , 'e.g., earthquakes, tsunamis' )
    PUBLIC_SAFETY   = ( 'Public Safety'  , 'e.g., child abduction alerts' )
    SECURITY        = ( 'Security'       , 'e.g., terrorist threats' )
    RESCUE          = ( 'Rescue'         , 'e.g., search and rescue' )
    FIRE            = ( 'Fire'           , 'e.g., wildfire warnings' )
    HEALTH          = ( 'Health'         , 'e.g., air quality alerts' )
    ENVIRONMENTAL   = ( 'Environmental'  , 'e.g., pollution warnings' )
    TRANSPORTATION  = ( 'Transportation' , 'e.g., road closures, marine warnings' )
    INFRASTRUCTURE  = ( 'Infrastructure' , 'e.g., power outages' )
    OTHER           = ( 'Other'          , 'Alerts not fitting in other categories.' )
    

class AlertSeverity( LabeledEnum ):
    EXTREME      = ( 'Extreme'    , '' )
    SEVERE       = ( 'Severe'     , '' )
    MODERATE     = ( 'Moderate'   , '' )
    MINOR        = ( 'Minor'      , '' )


class AlertUrgency( LabeledEnum ):
    IMMEDIATE    = ( 'Immediate'  , '' )
    EXPECTED     = ( 'Expected'   , '' )
    FUTURE       = ( 'Future'     , '' )
    UNKNOWN      = ( 'Unknown'    , '' )

    
class AlertCertainty( LabeledEnum ):
    OBSERVED     = ( 'Observed'   , '' )
    LIKELY       = ( 'Likely'     , '' )
    POSSIBLE     = ( 'Possible'   , '' )
    UNLIKELY     = ( 'Unlikely'   , '' )

    
class AlertStatus( LabeledEnum ):
    ACTUAL    = ( 'Actual'    , ' A real-time alert currently in effect.' )
    EXERCISE  = ( 'Exercise'  , 'A test or drill alert (not an actual event).' )
    SYSTEM    = ( 'System'    , 'Internal system message (not a public alert).' )
    TEST      = ( 'Test'      , 'A test message (e.g., weekly NOAA Weather Radio tests).' )
    DRAFT     = ( 'Draft'     , 'An alert being prepared but not yet issued.' )


class CloudCoverageType( LabeledEnum ):
    """ Note that an "okta" is 1/8 of the sky covered as reported by automated weather stations """
    
    SKY_CLEAR = (
        'Clear',
        'Clear skies reported by human observer.',
        SkyCondition.CLEAR,
        'SKC',
        0,
        0
    )
    CLEAR = (
        'Clear',
        'Clear skies reported by automated weather station.',
        SkyCondition.CLEAR,
        'CLR',
        0,
        5
    )
    FEW = (
        'Few',
        'Few clouds (1–2 oktas).',
        SkyCondition.MOSTLY_CLEAR,
        'FEW',
        5,
        25
    )
    SCATTERED = (
        'Scattered',
        'Scattered clouds (3–4 oktas).',
        SkyCondition.PARTLY_CLOUDY,
        'SCT',
        25,
        50
    )
    BROKEN = (
        'Broken',
        'Broken clouds (5–7 oktas).',
        SkyCondition.MOSTLY_CLOUDY,
        'BKN',
        50,
        87.5
    )
    OVERCAST = (
        'Overcast',
        'Overcast (8 oktas).',
        SkyCondition.CLOUDY,
        'OVC',
        87.5,
        100
    )
    VERTICAL_VISIBILITY = (
        'Vertical Visibility',
        'Obscured sky (e.g., fog, smoke, volcanic ash, heavy rain).',
        SkyCondition.CLOUDY,
        'VV',
        100,
        100
    )

    def __init__( self,
                  label                  : str,
                  description            : str,
                  sky_condition          : SkyCondition,
                  metar_code             : str,
                  coverage_percent_low   : float,
                  coverage_percent_high  : float ):
        super().__init__( label, description )
        self.sky_condition = sky_condition
        self.metar_code = metar_code
        self.coverage_percent_low = coverage_percent_low
        self.coverage_percent_high = coverage_percent_high
        return

    def __lt__( self, other ):
        ORDER = [ 'SKC', 'CLR', 'FEW', 'SCT', 'BKN', 'OVC', 'VV' ]
        if isinstance( other, CloudCoverageType ):
            return ORDER.index( self.metar_code ) < ORDER.index( other.metar_code )
        return False

    def __eq__( self, other ):
        if isinstance( other, CloudCoverageType ):
            return self.metar_code == other.metar_code
        return False

    def __hash__(self):
        return hash(self.metar_code)

    @property
    def cloud_cover_percent(self):
        return self.coverage_percent_high
    
    @property
    def is_eligible_as_cloud_ceiling(self):
        """
        International Civil Aviation Organization (ICAO) defines ceiling as "The
        height above the ground or water of the base of the lowest layer of
        cloud below 6,000 meters (20,000 feet) covering more than half the
        sky."
        """
        return self in { CloudCoverageType.BROKEN,
                         CloudCoverageType.OVERCAST,
                         CloudCoverageType.VERTICAL_VISIBILITY }

    
class WeatherPhenomenon( LabeledEnum ):
    DRIZZLE                  = ( 'Drizzle'                    , ''  , 'DZ' )
    DUSTSTORM                = ( 'Duststorm'                  , ''  , 'DS' )
    DUST_SAND_WHIRLS         = ( 'Dust/Sand Whirls'           , ''  , 'PO' )
    FOG                      = ( 'Fog'                        , ''  , 'FG' ) 
    FOG_MIST                 = ( 'Fog/Mist'                   , ''  , 'BR' ) 
    FUNNEL_CLOUD             = ( 'Funnel Cloud'               , ''  , 'FC' )
    HAIL                     = ( 'Hail'                       , ''  , 'GR' )
    HAZE                     = ( 'Haze'                       , ''  , 'HZ' )
    ICE_CRYSTALS             = ( 'Ice Crystals'               , ''  , 'IC' )
    ICE_PELLETS              = ( 'Ice Pellets'                , ''  , 'PL' )
    MIST                     = ( 'Mist'                       , ''  , 'BR' ) 
    RAIN                     = ( 'Rain'                       , ''  , 'RA' )
    SAND                     = ( 'Sand'                       , ''  , 'SA' )
    SANDSTORM                = ( 'Sandstorm'                  , ''  , 'SS' )
    SMALL_HAIL_SNOW_PELLETS  = ( 'Small Hail or Snow Pellets' , ''  , 'GS' )
    SMOKE                    = ( 'Smoke'                      , ''  , 'FU' )
    SNOW                     = ( 'Snow'                       , ''  , 'SN' )
    SNOW_GRAINS              = ( 'Snow Grains'                , ''  , 'SG' )
    SPRAY                    = ( 'Spray'                      , ''  , 'PY' )
    SQUALLS                  = ( 'Squalls'                    , ''  , 'SQ' )
    THUNDERSTORMS            = ( 'Thunderstorms'              , ''  , 'TS' )
    UNKNOWN                  = ( 'Unknown'                    , ''  , 'UP' )
    VOLCANIC_ASH             = ( 'Volcanic Ash'               , ''  , 'VA' )
    WIDESPREAD_DUST          = ( 'Widespread Dust'            , ''  , 'DU' )

    def __init__( self,
                  label         : str,
                  description   : str,
                  metar_code    : str ):
        super().__init__( label, description )
        self.metar_code = metar_code  # METAR = Meteorological Aerodrome Report (used in aviation)
        return
    
    
class WeatherPhenomenonModifier( LabeledEnum ):
    PATCHES       = ( 'Patches'       , '' , 'BC' )
    BLOWING       = ( 'Blowing'       , '' , 'BL' )
    LOW_DRIFTING  = ( 'Low Drifting'  , '' , 'DR' )
    FREEZING      = ( 'Freezing'      , '' , 'FZ' )
    SHALLOW       = ( 'Shallow'       , '' , 'MI' )
    PARTIAL       = ( 'Partial'       , '' , 'PR' )
    SHOWERS       = ( 'Showers'       , '' , 'SH' )
    THUNDERSTORMS = ( 'Thunderstorms' , '' , 'TS' )
    NONE          = ( 'None'          , '' , '' )
    
    def __init__( self,
                  label         : str,
                  description   : str,
                  metar_code    : str ):
        super().__init__( label, description )
        self.metar_code = metar_code  # METAR = Meteorological Aerodrome Report (used in aviation)
        return

    
class WeatherPhenomenonIntensity( LabeledEnum ):
    LIGHT     = ( 'Light'     , '' , '-' )
    MODERATE  = ( 'Moderate'  , '' , '' )
    HEAVY     = ( 'Heavy'     , '' , '+' )
    
    def __init__( self,
                  label           : str,
                  description     : str,
                  metar_modifier  : str ):
        super().__init__( label, description )
        self.metar_modifier = metar_modifier  # No prefix implies "MODERATE"
        return


class WindDirection( LabeledEnum ):
    NORTH            = ( 'N'   , '', 0.0   , [ 'n' ] )
    NORTH_NORTHEAST  = ( 'NNE' , '', 22.5  , [ 'nne' ] )
    NORTHEAST        = ( 'NE'  , '', 45.0  , [ 'ne' ] )
    EAST_NORTHEAST   = ( 'ENE' , '', 67.5  , [ 'ene' ] )
    EAST             = ( 'E'   , '', 90.0  , [ 'e' ] )
    EAST_SOUTHEAST   = ( 'ESE' , '', 112.5 , [ 'ese' ])
    SOUTHEAST        = ( 'SE'  , '', 135.0 , [ 'se' ] )
    SOUTH_SOUTHEAST  = ( 'SSE' , '', 157.5 , [ 'sse' ] )
    SOUTH            = ( 'S'   , '', 180.0 , [ 's' ] )
    SOUTH_SOUTHWEST  = ( 'SSW' , '', 202.5 , [ 'ssw' ] )
    SOUTHWEST        = ( 'SW'  , '', 225.0 , [ 'sw' ] )
    WEST_SOUTHWEST   = ( 'WSW' , '', 247.5 , [ 'wsw' ] )
    WEST             = ( 'W'   , '', 270.0 , [ 'w' ] )
    WEST_NORTHWEST   = ( 'WNW' , '', 292.5 , [ 'wnw' ] )
    NORTHWEST        = ( 'NW'  , '', 315.0 , [ 'nw' ] )
    NORTH_NORTHWEST  = ( 'NNW' , '', 337.5 , [ 'nnw' ] )
    
    def __init__( self,
                  label           : str,
                  description     : str,
                  angle_degrees   : float,
                  mnemonic_list   : str ):
        super().__init__( label, description )
        self.angle_degrees = angle_degrees
        self.mnemonic_list = mnemonic_list
        return

    @classmethod
    def from_menomic( cls, mnemonic_str : str ):
        if not mnemonic_str:
            raise ValueError( 'Blank wind speed mnemonic.' )
        for mnemonic_enum in cls:
            if mnemonic_str.strip().lower() in mnemonic_enum.mnemonic_list:
                return mnemonic_enum
            continue
        raise ValueError( f'Unknown wind speed mnemonic "{mnemonic_str}".' )
    
