from hi.apps.weather.enums import (
    AlertCategory,
    AlertSeverity,
    AlertUrgency,
    AlertCertainty,
    AlertStatus,
    CloudCoverageType,
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
    def to_alerts_everity( cls, nws_string : str ) -> AlertSeverity:
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
            WeatherPhenomenonModifier.NONE
        return cls.NwsWeatherPhenomenonModifierMap.get( nws_string.strip().lower() )
        
        
