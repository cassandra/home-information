from hi.apps.weather.enums import (
    AlertCategory,
    AlertSeverity,
    AlertUrgency,
    AlertCertainty,
    AlertStatus,
    CloudCoverageType,
    WeatherEventType,
    WeatherPhenomenon,
    WeatherPhenomenonIntensity,
    WeatherPhenomenonModifier,
)


class NwsConverters:

    NwsAlertCategoryMap = {
        'met' : AlertCategory.METEOROLOGICAL,
        'geo' : AlertCategory.GEOPHYSICAL,
        'safety' : AlertCategory.PUBLIC_SAFETY,
        'security' : AlertCategory.SECURITY,
        'rescue' : AlertCategory.RESCUE,
        'fire' : AlertCategory.FIRE,
        'health' : AlertCategory.HEALTH,
        'env' : AlertCategory.ENVIRONMENTAL,
        'transport' : AlertCategory.TRANSPORTATION,
        'infra' : AlertCategory.INFRASTRUCTURE,
        'other' : AlertCategory.OTHER,
    }
    NwsAlertSeverityMap = {
        'extreme' : AlertSeverity.EXTREME,
        'severe' : AlertSeverity.SEVERE,
        'moderate' : AlertSeverity.MODERATE,
        'minor' : AlertSeverity.MINOR,
    }
    NwsAlertUrgencyMp = {
        'immediate' : AlertUrgency.IMMEDIATE,
        'expected' : AlertUrgency.EXPECTED,
        'future' : AlertUrgency.FUTURE,
        'unknown' : AlertUrgency.UNKNOWN,
    }
    NwsAlertCertaintyMap = {
        'observed' : AlertCertainty.OBSERVED,
        'likely' : AlertCertainty.LIKELY,
        'possible' : AlertCertainty.POSSIBLE,
        'unlikely' : AlertCertainty.UNLIKELY,
    }
    NwsAlertStatusMap = {
        'actual' : AlertStatus.ACTUAL,
        'exercise' : AlertStatus.EXERCISE,
        'system' : AlertStatus.SYSTEM,
        'test' : AlertStatus.TEST,
        'draft' : AlertStatus.DRAFT,
    }
    NwsAlertCodeMap = {
        "ADR": "Administrative Message",
        "AFW": "Ashfall Warning",
        "AVA": "Avalanche Watch",
        "AVW": "Avalanche Warning",
        "BHW": "Beach Hazards Statement",
        "BLU": "Blue Alert",
        "BZW": "Blizzard Warning",
        "CAE": "Child Abduction Emergency (AMBER Alert)",
        "CDW": "Civil Danger Warning",
        "CEM": "Civil Emergency Message",
        "CFA": "Coastal Flood Watch",
        "CFW": "Coastal Flood Warning",
        "DSW": "Dust Storm Warning",
        "EQW": "Earthquake Warning",
        "EVI": "Evacuation Immediate",
        "EWW": "Extreme Wind Warning",
        "FFA": "Flash Flood Watch",
        "FFS": "Flash Flood Statement",
        "FFW": "Flash Flood Warning",
        "FLA": "Flood Watch",
        "FLS": "Flood Statement",
        "FLW": "Flood Warning",
        "FRW": "Fire Warning",
        "GFA": "Gale Watch",
        "GFW": "Gale Warning",
        "HMW": "Hazardous Materials Warning",
        "HUA": "Hurricane Watch",
        "HUW": "Hurricane Warning",
        "HWA": "High Wind Watch",
        "HWW": "High Wind Warning",
        "LAE": "Local Area Emergency",
        "LEW": "Law Enforcement Warning",
        "LSA": "Lakeshore Flood Watch",
        "LSW": "Lakeshore Flood Warning",
        "MWS": "Marine Weather Statement",
        "RFW": "Red Flag Warning",
        "RHW": "Radiological Hazard Warning",
        "RWT": "Required Weekly Test",
        "SCA": "Small Craft Advisory",
        "SEW": "Hazardous Seas Warning",
        "SMW": "Special Marine Warning",
        "SPS": "Special Weather Statement",
        "SSA": "Storm Surge Watch",
        "SSW": "Storm Surge Warning",
        "SVA": "Severe Thunderstorm Watch",
        "SVR": "Severe Thunderstorm Warning",
        "SVS": "Severe Weather Statement",
        "TOA": "Tornado Watch",
        "TOE": "911 Telephone Outage Emergency",
        "TOR": "Tornado Warning",
        "TRA": "Tropical Storm Watch",
        "TRW": "Tropical Storm Warning",
        "TSA": "Tsunami Watch",
        "TSW": "Tsunami Warning",
        "TST": "Test Message",
        "VOW": "Volcano Warning",
        "WSA": "Winter Storm Watch",
        "WSW": "Winter Storm Warning",
    }
    
    # NWS alert codes to canonical weather event types
    NwsCodeToWeatherEventTypeMap = {
        # Severe Weather
        'TOR': WeatherEventType.TORNADO,
        'SVR': WeatherEventType.SEVERE_THUNDERSTORM,
        'SVA': WeatherEventType.SEVERE_THUNDERSTORM,  # Severe Thunderstorm Watch
        'TOA': WeatherEventType.TORNADO,              # Tornado Watch
        'EWW': WeatherEventType.EXTREME_WIND,
        'HWW': WeatherEventType.EXTREME_WIND,         # High Wind Warning
        'HWA': WeatherEventType.EXTREME_WIND,         # High Wind Watch
        
        # Flooding
        'FFW': WeatherEventType.FLASH_FLOOD,
        'FFA': WeatherEventType.FLASH_FLOOD,          # Flash Flood Watch
        'FFS': WeatherEventType.FLASH_FLOOD,          # Flash Flood Statement
        'FLW': WeatherEventType.FLOOD,
        'FLA': WeatherEventType.FLOOD,                # Flood Watch
        'FLS': WeatherEventType.FLOOD,                # Flood Statement
        'CFW': WeatherEventType.COASTAL_FLOOD,
        'CFA': WeatherEventType.COASTAL_FLOOD,        # Coastal Flood Watch
        'LSW': WeatherEventType.LAKESHORE_FLOOD,
        'LSA': WeatherEventType.LAKESHORE_FLOOD,      # Lakeshore Flood Watch
        
        # Winter Weather
        'BZW': WeatherEventType.BLIZZARD,
        'WSW': WeatherEventType.WINTER_STORM,
        'WSA': WeatherEventType.WINTER_STORM,         # Winter Storm Watch
        'ICY': WeatherEventType.ICE_STORM,
        'ZFP': WeatherEventType.FREEZING_RAIN,
        
        # Tropical Weather
        'HUW': WeatherEventType.HURRICANE,
        'HUA': WeatherEventType.HURRICANE,            # Hurricane Watch
        'TRW': WeatherEventType.TROPICAL_STORM,
        'TRA': WeatherEventType.TROPICAL_STORM,       # Tropical Storm Watch
        'SSW': WeatherEventType.STORM_SURGE,
        'SSA': WeatherEventType.STORM_SURGE,          # Storm Surge Watch
        
        # Temperature Extremes
        'EHW': WeatherEventType.EXTREME_HEAT,
        'EHA': WeatherEventType.EXTREME_HEAT,         # Extreme Heat Watch
        'ECW': WeatherEventType.EXTREME_COLD,
        'ECA': WeatherEventType.EXTREME_COLD,         # Extreme Cold Watch
        'WCW': WeatherEventType.WIND_CHILL,
        'WCA': WeatherEventType.WIND_CHILL,           # Wind Chill Watch
        
        # Geophysical
        'EQW': WeatherEventType.EARTHQUAKE,
        'TSW': WeatherEventType.TSUNAMI,
        'TSA': WeatherEventType.TSUNAMI,              # Tsunami Watch
        'VOW': WeatherEventType.VOLCANIC_ACTIVITY,
        'AFW': WeatherEventType.ASHFALL,
        'AVW': WeatherEventType.AVALANCHE,
        'AVA': WeatherEventType.AVALANCHE,            # Avalanche Watch
        
        # Fire and Atmospheric
        'FRW': WeatherEventType.WILDFIRE,
        'RFW': WeatherEventType.RED_FLAG_CONDITIONS,
        'DSW': WeatherEventType.DUST_STORM,
        'AQA': WeatherEventType.AIR_QUALITY,
        
        # Marine
        'BHW': WeatherEventType.HIGH_SURF,
        'SCA': WeatherEventType.MARINE_WEATHER,       # Small Craft Advisory
        'GFW': WeatherEventType.GALE,
        'GFA': WeatherEventType.GALE,                 # Gale Watch
        'SEW': WeatherEventType.MARINE_WEATHER,       # Hazardous Seas Warning
        'SMW': WeatherEventType.MARINE_WEATHER,       # Special Marine Warning
        'MWS': WeatherEventType.MARINE_WEATHER,       # Marine Weather Statement
        'LWY': WeatherEventType.MARINE_WEATHER,       # Lake Wind Advisory
        
        # Public Safety
        'CDW': WeatherEventType.CIVIL_DANGER,
        'CEM': WeatherEventType.CIVIL_DANGER,         # Civil Emergency Message
        'EVI': WeatherEventType.EVACUATION,
        'HMW': WeatherEventType.HAZARDOUS_MATERIALS,
        'RHW': WeatherEventType.RADIOLOGICAL_HAZARD,
        'LAE': WeatherEventType.CIVIL_DANGER,         # Local Area Emergency
        'LEW': WeatherEventType.LAW_ENFORCEMENT,
        
        # Security/Emergency
        'CAE': WeatherEventType.AMBER_ALERT,
        'BLU': WeatherEventType.BLUE_ALERT,
        
        # Communication/Infrastructure
        'TOE': WeatherEventType.TELEPHONE_OUTAGE,
        
        # Test and Administrative
        'TST': WeatherEventType.TEST_MESSAGE,
        'RWT': WeatherEventType.TEST_MESSAGE,         # Required Weekly Test
        'ADR': WeatherEventType.ADMINISTRATIVE,
        
        # Special Weather
        'SPS': WeatherEventType.SPECIAL_WEATHER,      # Special Weather Statement
        'SVS': WeatherEventType.SPECIAL_WEATHER,      # Severe Weather Statement
    }
    
    NwsCloudCoverageTypeMap = {
        # METAR codes
        'skc' : CloudCoverageType.SKY_CLEAR,
        'clr' : CloudCoverageType.CLEAR,
        'few' : CloudCoverageType.FEW,
        'sct' : CloudCoverageType.SCATTERED,
        'bkn' : CloudCoverageType.BROKEN,
        'ovc' : CloudCoverageType.OVERCAST,
        'vv' : CloudCoverageType.VERTICAL_VISIBILITY,
    }
    NwsWeatherPhenomenonMap = {
        'drizzle' : WeatherPhenomenon.DRIZZLE,
        'dust' : WeatherPhenomenon.DUSTSTORM,
        'dust_storm' : WeatherPhenomenon.DUSTSTORM,
        'dust storm' : WeatherPhenomenon.DUSTSTORM,
        'dust_swirls' : WeatherPhenomenon.DUST_SAND_WHIRLS,
        'dust swirls' : WeatherPhenomenon.DUST_SAND_WHIRLS,
        'fog' : WeatherPhenomenon.FOG,
        'fog_mist' : WeatherPhenomenon.FOG_MIST,
        'fog mist' : WeatherPhenomenon.FOG_MIST,
        'funnel_cloud' : WeatherPhenomenon.FUNNEL_CLOUD,
        'funnel cloud' : WeatherPhenomenon.FUNNEL_CLOUD,
        'hail' : WeatherPhenomenon.HAIL,
        'haze' : WeatherPhenomenon.HAZE,
        'ice_crystals' : WeatherPhenomenon.ICE_CRYSTALS,
        'ice crystals' : WeatherPhenomenon.ICE_CRYSTALS,
        'ice_pellets' : WeatherPhenomenon.ICE_PELLETS,
        'ice pellets' : WeatherPhenomenon.ICE_PELLETS,
        'mist' : WeatherPhenomenon.MIST,
        'rain' : WeatherPhenomenon.RAIN,
        'sand' : WeatherPhenomenon.SAND,
        'sand_storm' : WeatherPhenomenon.SANDSTORM,
        'sand storm' : WeatherPhenomenon.SANDSTORM,
        'snow_pellets' : WeatherPhenomenon.SMALL_HAIL_SNOW_PELLETS,
        'snow pellets' : WeatherPhenomenon.SMALL_HAIL_SNOW_PELLETS,
        'smoke' : WeatherPhenomenon.SMOKE,
        'snow' : WeatherPhenomenon.SNOW,
        'snow_grains' : WeatherPhenomenon.SNOW_GRAINS,
        'snow grains' : WeatherPhenomenon.SNOW_GRAINS,
        'spray' : WeatherPhenomenon.SPRAY,
        'squalls' : WeatherPhenomenon.SQUALLS,
        'thunderstorms' : WeatherPhenomenon.THUNDERSTORMS,
        'unknown' : WeatherPhenomenon.UNKNOWN,
        'volcanic_ash' : WeatherPhenomenon.VOLCANIC_ASH,
        'volcanic ash' : WeatherPhenomenon.VOLCANIC_ASH,
    }
    NwsWeatherPhenomenonIntensityMap = {
        'light' : WeatherPhenomenonIntensity.LIGHT,
        'moderate' : WeatherPhenomenonIntensity.MODERATE,
        'heavy' : WeatherPhenomenonIntensity.HEAVY,
        'none' : WeatherPhenomenonIntensity.MODERATE,
    }
    NwsWeatherPhenomenonModifierMap = {
        'patches' : WeatherPhenomenonModifier.PATCHES,
        'blowing' : WeatherPhenomenonModifier.BLOWING,
        'low_drifting' : WeatherPhenomenonModifier.LOW_DRIFTING,
        'low drifting' : WeatherPhenomenonModifier.LOW_DRIFTING,
        'freezing' : WeatherPhenomenonModifier.FREEZING,
        'shallow' : WeatherPhenomenonModifier.SHALLOW,
        'partial' : WeatherPhenomenonModifier.PARTIAL,
        'showers' : WeatherPhenomenonModifier.SHOWERS,
        'thunderstorm' : WeatherPhenomenonModifier.THUNDERSTORMS,
        'none' : WeatherPhenomenonModifier.NONE,
    }

    @classmethod
    def to_alert_category( cls, nws_string : str ) -> AlertCategory:
        return cls.NwsAlertCategoryMap.get( nws_string.strip().lower() )

    @classmethod
    def to_alerts_severity( cls, nws_string : str ) -> AlertSeverity:
        return cls.NwsAlertSeverityMap.get( nws_string.strip().lower() )
        
    @classmethod
    def to_alert_urgency( cls, nws_string : str ) -> AlertUrgency:
        return cls.NwsAlertUrgencyMp.get( nws_string.strip().lower() )
        
    @classmethod
    def to_alert_certainty( cls, nws_string : str ) -> AlertCertainty:
        return cls.NwsAlertCertaintyMap.get( nws_string.strip().lower() )
        
    @classmethod
    def to_alert_status( cls, nws_string : str ) -> AlertStatus:
        return cls.NwsAlertStatusMap.get( nws_string.strip().lower() )
        
    @classmethod
    def to_weather_event_type( cls, nws_code : str ) -> WeatherEventType:
        """
        Convert NWS alert code to canonical weather event type.
        
        Args:
            nws_code: NWS alert code (e.g., 'TOR', 'FFW', 'SVR', 'LWY')
            
        Returns:
            Corresponding WeatherEventType or WeatherEventType.OTHER if not found
        """
        if not nws_code:
            return WeatherEventType.OTHER
            
        # NWS codes are typically 3 characters, case-insensitive
        code_upper = nws_code.strip().upper()
        return cls.NwsCodeToWeatherEventTypeMap.get(code_upper, WeatherEventType.OTHER)
    
    @classmethod
    def to_weather_event_type_from_event_name( cls, event_name : str ) -> WeatherEventType:
        """
        Convert NWS event name to canonical weather event type (fallback method).
        
        This is used when the eventCode field is not available in the API response.
        
        Args:
            event_name: NWS event name (e.g., 'Tornado Warning', 'Lake Wind Advisory')
            
        Returns:
            Corresponding WeatherEventType or WeatherEventType.OTHER if not found
        """
        if not event_name:
            return WeatherEventType.OTHER
            
        # Normalize the event name for comparison
        event_upper = event_name.strip().upper()
        
        # Map common NWS event names to canonical types (key patterns)
        if 'TORNADO' in event_upper:
            return WeatherEventType.TORNADO
        elif 'SEVERE THUNDERSTORM' in event_upper:
            return WeatherEventType.SEVERE_THUNDERSTORM
        elif 'FLASH FLOOD' in event_upper:
            return WeatherEventType.FLASH_FLOOD
        elif 'FLOOD' in event_upper and 'COASTAL' in event_upper:
            return WeatherEventType.COASTAL_FLOOD
        elif 'FLOOD' in event_upper:
            return WeatherEventType.FLOOD
        elif 'HURRICANE' in event_upper:
            return WeatherEventType.HURRICANE
        elif 'TROPICAL STORM' in event_upper:
            return WeatherEventType.TROPICAL_STORM
        elif 'BLIZZARD' in event_upper:
            return WeatherEventType.BLIZZARD
        elif 'WINTER STORM' in event_upper:
            return WeatherEventType.WINTER_STORM
        elif 'HIGH WIND' in event_upper or 'EXTREME WIND' in event_upper:
            return WeatherEventType.EXTREME_WIND
        elif 'WIND' in event_upper and ('LAKE' in event_upper or 'MARINE' in event_upper):
            return WeatherEventType.MARINE_WEATHER
        elif 'GALE' in event_upper:
            return WeatherEventType.GALE
        elif 'HIGH SURF' in event_upper:
            return WeatherEventType.HIGH_SURF
        elif 'EARTHQUAKE' in event_upper:
            return WeatherEventType.EARTHQUAKE
        elif 'TSUNAMI' in event_upper:
            return WeatherEventType.TSUNAMI
        elif 'VOLCANO' in event_upper:
            return WeatherEventType.VOLCANIC_ACTIVITY
        elif 'AVALANCHE' in event_upper:
            return WeatherEventType.AVALANCHE
        elif 'RED FLAG' in event_upper or 'FIRE WEATHER' in event_upper:
            return WeatherEventType.RED_FLAG_CONDITIONS
        elif 'DUST STORM' in event_upper:
            return WeatherEventType.DUST_STORM
        elif 'HEAT' in event_upper:
            return WeatherEventType.EXTREME_HEAT
        elif 'COLD' in event_upper:
            return WeatherEventType.EXTREME_COLD
        elif 'WIND CHILL' in event_upper:
            return WeatherEventType.WIND_CHILL
        elif 'AMBER ALERT' in event_upper or 'CHILD ABDUCTION' in event_upper:
            return WeatherEventType.AMBER_ALERT
        elif 'BLUE ALERT' in event_upper:
            return WeatherEventType.BLUE_ALERT
        elif 'CIVIL' in event_upper:
            return WeatherEventType.CIVIL_DANGER
        elif 'TEST' in event_upper:
            return WeatherEventType.TEST_MESSAGE
        elif 'SPECIAL' in event_upper and 'WEATHER' in event_upper:
            return WeatherEventType.SPECIAL_WEATHER
        else:
            return WeatherEventType.OTHER
        
    @classmethod
    def to_cloud_coverage_type( cls, nws_string : str ) -> CloudCoverageType:
        return cls.NwsCloudCoverageTypeMap.get( nws_string.strip().lower() )
        
    @classmethod
    def to_weather_phenomenon( cls, nws_string : str ) -> WeatherPhenomenon:
        return cls.NwsWeatherPhenomenonMap.get( nws_string.strip().lower() )
        
    @classmethod
    def to_weather_phenomenon_intensity( cls, nws_string : str ) -> WeatherPhenomenonIntensity:
        if not nws_string:
            return WeatherPhenomenonIntensity.MODERATE
        return cls.NwsWeatherPhenomenonIntensityMap.get( nws_string.strip().lower() )
        
    @classmethod
    def to_weather_phenomenon_modifier( cls, nws_string : str ) -> WeatherPhenomenonModifier:
        if not nws_string:
            return WeatherPhenomenonModifier.NONE
        return cls.NwsWeatherPhenomenonModifierMap.get( nws_string.strip().lower() )
        
        
