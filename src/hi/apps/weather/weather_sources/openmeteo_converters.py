"""
OpenMeteo API data converters for transforming OpenMeteo-specific data formats 
into the canonical weather data model.
"""

import logging

logger = logging.getLogger(__name__)


class OpenMeteoConverters:

    # WMO weather interpretation codes (WW). See https://open-meteo.com/en/docs
    WEATHER_CODE_DESCRIPTIONS = {
        0: "Clear sky",
        1: "Mainly clear",
        2: "Partly cloudy", 
        3: "Overcast",
        45: "Fog",
        48: "Depositing rime fog",
        51: "Light drizzle",
        53: "Moderate drizzle",
        55: "Dense drizzle",
        56: "Light freezing drizzle",
        57: "Dense freezing drizzle",
        61: "Slight rain",
        63: "Moderate rain",
        65: "Heavy rain",
        66: "Light freezing rain",
        67: "Heavy freezing rain",
        71: "Slight snow fall",
        73: "Moderate snow fall",
        75: "Heavy snow fall",
        77: "Snow grains",
        80: "Slight rain showers",
        81: "Moderate rain showers",
        82: "Violent rain showers",
        85: "Slight snow showers",
        86: "Heavy snow showers",
        95: "Thunderstorm",
        96: "Thunderstorm with slight hail",
        99: "Thunderstorm with heavy hail",
    }

    @staticmethod
    def weather_code_to_description(weather_code: int) -> str:
        if weather_code in OpenMeteoConverters.WEATHER_CODE_DESCRIPTIONS:
            return OpenMeteoConverters.WEATHER_CODE_DESCRIPTIONS[weather_code]

        raise ValueError(f'Unknown OpenMeteo weather code: {weather_code}')

    @staticmethod
    def normalize_temperature_unit(unit_str: str) -> str:
        if unit_str == '°C':
            return 'degC'
        elif unit_str == '°F':
            return 'degF'
        elif unit_str == 'K':
            return 'K'
        else:
            logger.warning(f'Unknown OpenMeteo temperature unit: {unit_str}, assuming Celsius')
            return 'degC'

    @staticmethod
    def normalize_wind_unit(unit_str: str) -> str:
        if unit_str == 'km/h':
            return 'km/h'
        elif unit_str == 'm/s':
            return 'm/s'
        elif unit_str == 'mph':
            return 'mph'
        elif unit_str == 'kn':
            return 'knot'
        else:
            logger.warning(f'Unknown OpenMeteo wind unit: {unit_str}, assuming km/h')
            return 'km/h'

    @staticmethod
    def normalize_precipitation_unit(unit_str: str) -> str:
        if unit_str == 'mm':
            return 'mm'
        elif unit_str == 'inch':
            return 'inch'
        else:
            logger.warning(f'Unknown OpenMeteo precipitation unit: {unit_str}, assuming mm')
            return 'mm'

    @staticmethod
    def normalize_pressure_unit(unit_str: str) -> str:
        if unit_str == 'hPa':
            return 'hPa'
        elif unit_str == 'Pa':
            return 'Pa'
        elif unit_str == 'inHg':
            return 'inHg'
        elif unit_str == 'mmHg':
            return 'mmHg'
        else:
            logger.warning(f'Unknown OpenMeteo pressure unit: {unit_str}, assuming hPa')
            return 'hPa'

    @staticmethod
    def is_weather_code_precipitation(weather_code: int) -> bool:
        precipitation_codes = {
            51, 53, 55, 56, 57,  # Drizzle
            61, 63, 65, 66, 67,  # Rain
            71, 73, 75, 77,      # Snow
            80, 81, 82, 85, 86,  # Showers
            95, 96, 99           # Thunderstorms
        }
        return weather_code in precipitation_codes

    @staticmethod
    def is_weather_code_clear(weather_code: int) -> bool:
        clear_codes = {0, 1}  # Clear sky, mainly clear
        return weather_code in clear_codes

    @staticmethod
    def get_weather_code_severity(weather_code: int) -> str:
        """Return one of: 'clear', 'light', 'moderate', 'heavy', 'severe'."""
        if weather_code in {0, 1}:
            return 'clear'
        elif weather_code in {2, 3}:
            return 'light'
        elif weather_code in {45, 48, 51, 56, 61, 66, 71, 77, 80, 85}:
            return 'light'
        elif weather_code in {53, 63, 73, 81}:
            return 'moderate'
        elif weather_code in {55, 57, 65, 67, 75, 82, 86}:
            return 'heavy'
        elif weather_code in {95, 96, 99}:
            return 'severe'
        else:
            return 'moderate'
