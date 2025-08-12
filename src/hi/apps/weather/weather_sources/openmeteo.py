from datetime import datetime, timedelta
import json
import logging
import requests
from typing import Any, Dict, List

from django.conf import settings

import hi.apps.common.datetimeproxy as datetimeproxy
from hi.apps.weather.weather_data_source import WeatherDataSource
from hi.apps.weather.transient_models import (
    BooleanDataPoint,
    NumericDataPoint,
    StringDataPoint,
    TimeInterval,
    WeatherConditionsData,
    WeatherForecastData,
    WeatherHistoryData,
    IntervalWeatherForecast,
    IntervalWeatherHistory,
    Station,
)
from hi.apps.weather.weather_mixins import WeatherMixin
from hi.apps.weather.wmo_units import WmoUnits
from hi.transient_models import GeographicLocation
from hi.units import UnitQuantity

from .openmeteo_converters import OpenMeteoConverters

logger = logging.getLogger(__name__)


class OpenMeteo(WeatherDataSource, WeatherMixin):

    BASE_URL = "https://api.open-meteo.com/v1/"
    ARCHIVE_BASE_URL = "https://archive-api.open-meteo.com/v1/archive"

    CURRENT_DATA_CACHE_EXPIRY_SECS = 10 * 60  # Cache for 10 minutes
    FORECAST_DATA_CACHE_EXPIRY_SECS = 60 * 60  # Cache for 1 hour
    HISTORICAL_DATA_CACHE_EXPIRY_SECS = 30 * 24 * 60 * 60  # Cache for 30 days - historical data rarely changes
    
    SKIP_CACHE = False  # For debugging    
    
    def __init__(self):
        super().__init__(
            id = 'openmeteo',
            label = 'Open-Meteo',
            abbreviation = 'OpenMeteo',
            priority = 2,  # Lower priority than NWS
            requests_per_day_limit = 10000,  # Open-Meteo is very generous
            requests_per_polling_interval = 5,
            min_polling_interval_secs = 5 * 60,  # 5 minutes minimum
        )

        self._headers = {
            'User-Agent': 'HomeInformation (weather@homeinformation.org)',
        }
        return
    
    def requires_api_key(self) -> bool:
        """Open-Meteo does not require an API key."""
        return False
    
    def get_default_enabled_state(self) -> bool:
        """Open-Meteo is enabled by default."""
        return True
    
    async def get_data(self):

        geographic_location = self.geographic_location
        if not geographic_location:
            logger.warning('No geographic location setting. Skipping OpenMeteo weather fetch.')
            return
            
        weather_manager = await self.weather_manager_async()
        if not weather_manager:
            logger.warning('Weather manager not available. Skipping OpenMeteo weather fetch.')
            return

        # Fetch current conditions
        try:
            current_conditions_data = self.get_current_conditions(
                geographic_location = geographic_location,
            )
            if current_conditions_data:
                await weather_manager.update_current_conditions(
                    weather_data_source = self,
                    weather_conditions_data = current_conditions_data,
                )
        except Exception as e:
            logger.exception(f'Problem fetching OpenMeteo current conditions: {e}')

        # Fetch hourly forecast data
        try:
            hourly_forecast_data_list = self.get_forecast_hourly(
                geographic_location = geographic_location,
            )
            if hourly_forecast_data_list:
                await weather_manager.update_hourly_forecast(
                    weather_data_source = self,
                    forecast_data_list = hourly_forecast_data_list,
                )
        except Exception as e:
            logger.exception(f'Problem fetching OpenMeteo hourly forecast: {e}')

        # Fetch daily forecast data
        try:
            daily_forecast_data_list = self.get_forecast_daily(
                geographic_location = geographic_location,
            )
            if daily_forecast_data_list:
                await weather_manager.update_daily_forecast(
                    weather_data_source = self,
                    forecast_data_list = daily_forecast_data_list,
                )
        except Exception as e:
            logger.exception(f'Problem fetching OpenMeteo daily forecast: {e}')

        # Fetch historical weather data (last 7 days)
        try:
            logger.debug(f'Fetching OpenMeteo historical weather data for 7 days')
            historical_data_list = self.get_historical_weather(
                geographic_location = geographic_location,
                days_back = 7,
            )
            logger.debug(f'OpenMeteo returned {len(historical_data_list) if historical_data_list else 0} historical data items')
            if historical_data_list:
                await weather_manager.update_daily_history(
                    weather_data_source = self,
                    history_data_list = historical_data_list,
                )
                logger.debug(f'Successfully updated daily history with {len(historical_data_list)} items')
            else:
                logger.warning('OpenMeteo returned no historical weather data')
        except Exception as e:
            logger.exception(f'Problem fetching OpenMeteo historical data: {e}')

        # Note: OpenMeteo does not provide astronomical data
        # This would need to be fetched from other sources if needed
        
        return

    def get_current_conditions(self, geographic_location: GeographicLocation) -> WeatherConditionsData:
        current_data = self._get_current_weather_data(geographic_location = geographic_location)
        return self._parse_current_weather_data(
            current_data = current_data,
            geographic_location = geographic_location,
        )

    def get_forecast_hourly(self, geographic_location: GeographicLocation) -> List[IntervalWeatherForecast]:
        forecast_data = self._get_hourly_forecast_data(geographic_location = geographic_location)
        return self._parse_hourly_forecast_data(
            forecast_data = forecast_data,
            geographic_location = geographic_location,
        )

    def get_forecast_daily(self, geographic_location: GeographicLocation) -> List[IntervalWeatherForecast]:
        forecast_data = self._get_daily_forecast_data(geographic_location = geographic_location)
        return self._parse_daily_forecast_data(
            forecast_data = forecast_data,
            geographic_location = geographic_location,
        )

    def get_historical_weather(self, geographic_location: GeographicLocation, days_back: int = 7) -> List[IntervalWeatherHistory]:
        end_date = datetimeproxy.now().date()
        start_date = end_date - timedelta(days = days_back)
        
        historical_data = self._get_historical_weather_data(
            geographic_location = geographic_location,
            start_date = start_date,
            end_date = end_date,
        )
        return self._parse_historical_weather_data(
            historical_data = historical_data,
            geographic_location = geographic_location,
        )

    def _parse_current_weather_data(self, 
                                    current_data: Dict,
                                    geographic_location: GeographicLocation) -> WeatherConditionsData:
        
        current_weather_data = current_data.get('current_weather', {})
        hourly_data = current_data.get('hourly', {})
        current_weather_units = current_data.get('current_weather_units', {})
        hourly_units = current_data.get('hourly_units', {})
        
        try:
            timestamp_str = current_weather_data.get('time')
            source_datetime = datetimeproxy.iso_naive_to_datetime_utc(timestamp_str)
        except Exception as e:
            logger.warning(f'Missing or bad timestamp in OpenMeteo current weather payload: {e}')
            source_datetime = datetimeproxy.now()

        elevation = current_data.get('elevation')
        elevation_quantity = UnitQuantity(elevation, 'm') if elevation is not None else None

        station = Station(
            source = self.data_point_source,
            station_id = f'openmeteo:{geographic_location.latitude:.3f}:{geographic_location.longitude:.3f}',
            name = f'OpenMeteo ({geographic_location.latitude:.3f}, {geographic_location.longitude:.3f})',
            geo_location = GeographicLocation(
                latitude = current_data.get('latitude', geographic_location.latitude),
                longitude = current_data.get('longitude', geographic_location.longitude),
                elevation = elevation_quantity,
            ),
            station_url = None,
            observations_url = None,
            forecast_url = None,
        )
            
        weather_conditions_data = WeatherConditionsData()

        # Temperature from current weather
        temperature = current_weather_data.get('temperature')
        if temperature is not None:
            temp_unit = current_weather_units.get('temperature', '°C')
            weather_conditions_data.temperature = NumericDataPoint(
                station = station,
                source_datetime = source_datetime,
                quantity_ave = UnitQuantity(temperature, OpenMeteoConverters.normalize_temperature_unit(temp_unit)),
            )

        # Wind speed from current weather
        windspeed = current_weather_data.get('windspeed')
        if windspeed is not None:
            wind_unit = current_weather_units.get('windspeed', 'km/h')
            weather_conditions_data.windspeed = NumericDataPoint(
                station = station,
                source_datetime = source_datetime,
                quantity_ave = UnitQuantity(windspeed, OpenMeteoConverters.normalize_wind_unit(wind_unit)),
            )

        # Wind direction from current weather
        wind_direction = current_weather_data.get('winddirection')
        if wind_direction is not None:
            weather_conditions_data.wind_direction = NumericDataPoint(
                station = station,
                source_datetime = source_datetime,
                quantity_ave = UnitQuantity(wind_direction, 'degrees'),
            )

        # Weather code description
        weather_code = current_weather_data.get('weathercode')
        if weather_code is not None:
            try:
                weather_description = OpenMeteoConverters.weather_code_to_description(weather_code)
                weather_conditions_data.description_short = StringDataPoint(
                    station = station,
                    source_datetime = source_datetime,
                    value = weather_description,
                )
            except ValueError:
                logger.warning(f'Unknown OpenMeteo weather code: {weather_code}')

        # Is daytime
        is_day = current_weather_data.get('is_day')
        if is_day is not None:
            weather_conditions_data.is_daytime = BooleanDataPoint(
                station = station,
                source_datetime = source_datetime,
                value = bool(is_day),
            )

        # Additional data from hourly arrays (get current hour data)
        if hourly_data and hourly_data.get('time'):
            current_hour_str = source_datetime.strftime('%Y-%m-%dT%H:00')
            try:
                current_hour_index = hourly_data['time'].index(current_hour_str)
                
                # Relative humidity
                if 'relativehumidity_2m' in hourly_data:
                    humidity = hourly_data['relativehumidity_2m'][current_hour_index]
                    if humidity is not None:
                        weather_conditions_data.relative_humidity = NumericDataPoint(
                            station = station,
                            source_datetime = source_datetime,
                            quantity_ave = UnitQuantity(humidity, 'percent'),
                        )

                # Dew point
                if 'dewpoint_2m' in hourly_data:
                    dewpoint = hourly_data['dewpoint_2m'][current_hour_index]
                    if dewpoint is not None:
                        dewpoint_unit = hourly_units.get('dewpoint_2m', '°C')
                        weather_conditions_data.dew_point = NumericDataPoint(
                            station = station,
                            source_datetime = source_datetime,
                            quantity_ave = UnitQuantity(dewpoint, OpenMeteoConverters.normalize_temperature_unit(dewpoint_unit)),
                        )

                # Precipitation
                if 'precipitation' in hourly_data:
                    precipitation = hourly_data['precipitation'][current_hour_index]
                    if precipitation is not None:
                        precip_unit = hourly_units.get('precipitation', 'mm')
                        weather_conditions_data.precipitation_last_hour = NumericDataPoint(
                            station = station,
                            source_datetime = source_datetime,
                            quantity_ave = UnitQuantity(precipitation, OpenMeteoConverters.normalize_precipitation_unit(precip_unit)),
                        )

                # Pressure (sea level)
                if 'pressure_msl' in hourly_data:
                    pressure = hourly_data['pressure_msl'][current_hour_index]
                    if pressure is not None:
                        pressure_unit = hourly_units.get('pressure_msl', 'hPa')
                        weather_conditions_data.sea_level_pressure = NumericDataPoint(
                            station = station,
                            source_datetime = source_datetime,
                            quantity_ave = UnitQuantity(pressure, OpenMeteoConverters.normalize_pressure_unit(pressure_unit)),
                        )

            except (ValueError, IndexError):
                logger.debug('Could not find current hour in OpenMeteo hourly data')

        return weather_conditions_data
    
    def _parse_hourly_forecast_data(self, 
                                    forecast_data: Dict,
                                    geographic_location: GeographicLocation) -> List[IntervalWeatherForecast]:

        hourly_data = forecast_data.get('hourly', {})
        hourly_units = forecast_data.get('hourly_units', {})
        
        if not hourly_data or not hourly_data.get('time'):
            raise ValueError('Missing "hourly" or "time" in OpenMeteo forecast payload.')

        try:
            generation_time = forecast_data.get('generationtime_ms', 0) / 1000.0
            source_datetime = datetimeproxy.now()
        except Exception as e:
            logger.warning(f'Problem with OpenMeteo generation time: {e}')
            source_datetime = datetimeproxy.now()

        elevation = forecast_data.get('elevation')
        elevation_quantity = UnitQuantity(elevation, 'm') if elevation is not None else None

        station = Station(
            source = self.data_point_source,
            station_id = f'openmeteo-hourly:{geographic_location.latitude:.3f}:{geographic_location.longitude:.3f}',
            name = f'OpenMeteo Hourly ({geographic_location.latitude:.3f}, {geographic_location.longitude:.3f})',
            geo_location = GeographicLocation(
                latitude = forecast_data.get('latitude', geographic_location.latitude),
                longitude = forecast_data.get('longitude', geographic_location.longitude),
                elevation = elevation_quantity,
            ),
            station_url = None,
            observations_url = None,
            forecast_url = None,
        )

        time_list = hourly_data['time']
        interval_weather_forecast_list = list()
        
        for i, time_str in enumerate(time_list):
            
            # Parse time interval
            try:
                interval_start = datetimeproxy.iso_naive_to_datetime_utc(time_str)
                interval_end = interval_start + timedelta(hours = 1)
            except Exception as e:
                logger.warning(f'Missing or bad time in OpenMeteo hourly forecast payload: {e}')
                continue
                
            # Create time interval
            time_interval = TimeInterval(
                start=interval_start,
                end=interval_end
            )
            
            # Create weather forecast data
            forecast_data = WeatherForecastData()
            
            # Temperature
            if 'temperature_2m' in hourly_data and i < len(hourly_data['temperature_2m']):
                temperature = hourly_data['temperature_2m'][i]
                if temperature is not None:
                    temp_unit = hourly_units.get('temperature_2m', '°C')
                    forecast_data.temperature = NumericDataPoint(
                        station = station,
                        source_datetime = source_datetime,
                        quantity_ave = UnitQuantity(temperature, OpenMeteoConverters.normalize_temperature_unit(temp_unit)),
                    )

            # Relative humidity
            if 'relativehumidity_2m' in hourly_data and i < len(hourly_data['relativehumidity_2m']):
                humidity = hourly_data['relativehumidity_2m'][i]
                if humidity is not None:
                    forecast_data.relative_humidity = NumericDataPoint(
                        station = station,
                        source_datetime = source_datetime,
                        quantity_ave = UnitQuantity(humidity, 'percent'),
                    )

            # Wind speed
            if 'windspeed_10m' in hourly_data and i < len(hourly_data['windspeed_10m']):
                windspeed = hourly_data['windspeed_10m'][i]
                if windspeed is not None:
                    wind_unit = hourly_units.get('windspeed_10m', 'km/h')
                    forecast_data.windspeed = NumericDataPoint(
                        station = station,
                        source_datetime = source_datetime,
                        quantity_ave = UnitQuantity(windspeed, OpenMeteoConverters.normalize_wind_unit(wind_unit)),
                    )

            # Wind direction
            if 'winddirection_10m' in hourly_data and i < len(hourly_data['winddirection_10m']):
                wind_direction = hourly_data['winddirection_10m'][i]
                if wind_direction is not None:
                    forecast_data.wind_direction = NumericDataPoint(
                        station = station,
                        source_datetime = source_datetime,
                        quantity_ave = UnitQuantity(wind_direction, 'degrees'),
                    )

            # Precipitation
            if 'precipitation' in hourly_data and i < len(hourly_data['precipitation']):
                precipitation = hourly_data['precipitation'][i]
                if precipitation is not None:
                    precip_unit = hourly_units.get('precipitation', 'mm')
                    forecast_data.precipitation_probability = NumericDataPoint(
                        station = station,
                        source_datetime = source_datetime,
                        quantity_ave = UnitQuantity(precipitation, OpenMeteoConverters.normalize_precipitation_unit(precip_unit)),
                    )

            # Weather code
            if 'weathercode' in hourly_data and i < len(hourly_data['weathercode']):
                weather_code = hourly_data['weathercode'][i]
                if weather_code is not None:
                    try:
                        weather_description = OpenMeteoConverters.weather_code_to_description(weather_code)
                        forecast_data.description_short = StringDataPoint(
                            station = station,
                            source_datetime = source_datetime,
                            value = weather_description,
                        )
                    except ValueError:
                        logger.warning(f'Unknown OpenMeteo weather code: {weather_code}')

            # Create interval weather forecast
            interval_weather_forecast = IntervalWeatherForecast(
                interval=time_interval,
                data=forecast_data
            )
            interval_weather_forecast_list.append(interval_weather_forecast)
            continue

        return interval_weather_forecast_list

    def _parse_daily_forecast_data(self, 
                                   forecast_data: Dict,
                                   geographic_location: GeographicLocation) -> List[IntervalWeatherForecast]:

        daily_data = forecast_data.get('daily', {})
        daily_units = forecast_data.get('daily_units', {})
        
        if not daily_data or not daily_data.get('time'):
            raise ValueError('Missing "daily" or "time" in OpenMeteo daily forecast payload.')

        try:
            source_datetime = datetimeproxy.now()
        except Exception as e:
            logger.warning(f'Problem with OpenMeteo generation time: {e}')
            source_datetime = datetimeproxy.now()

        elevation = forecast_data.get('elevation')
        elevation_quantity = UnitQuantity(elevation, 'm') if elevation is not None else None

        station = Station(
            source = self.data_point_source,
            station_id = f'openmeteo-daily:{geographic_location.latitude:.3f}:{geographic_location.longitude:.3f}',
            name = f'OpenMeteo Daily ({geographic_location.latitude:.3f}, {geographic_location.longitude:.3f})',
            geo_location = GeographicLocation(
                latitude = forecast_data.get('latitude', geographic_location.latitude),
                longitude = forecast_data.get('longitude', geographic_location.longitude),
                elevation = elevation_quantity,
            ),
            station_url = None,
            observations_url = None,
            forecast_url = None,
        )

        time_list = daily_data['time']
        interval_weather_forecast_list = list()
        
        for i, date_str in enumerate(time_list):
            
            # Parse time interval
            try:
                date_obj = datetime.fromisoformat(date_str).date()
                interval_start = datetimeproxy.iso_naive_to_datetime_utc(datetime.combine(date_obj, datetime.min.time()).isoformat())
                interval_end = interval_start + timedelta(days = 1)
            except Exception as e:
                logger.warning(f'Missing or bad date in OpenMeteo daily forecast payload: {e}')
                continue
                
            time_interval = TimeInterval(
                start=interval_start,
                end=interval_end
            )
            
            # Create weather forecast data
            forecast_data = WeatherForecastData()
            
            # Temperature max
            if 'temperature_2m_max' in daily_data and i < len(daily_data['temperature_2m_max']):
                temp_max = daily_data['temperature_2m_max'][i]
                if temp_max is not None:
                    temp_unit = daily_units.get('temperature_2m_max', '°C')
                    forecast_data.temperature = NumericDataPoint(
                        station = station,
                        source_datetime = source_datetime,
                        quantity_max = UnitQuantity(temp_max, OpenMeteoConverters.normalize_temperature_unit(temp_unit)),
                    )

            # Temperature min
            if 'temperature_2m_min' in daily_data and i < len(daily_data['temperature_2m_min']):
                temp_min = daily_data['temperature_2m_min'][i]
                if temp_min is not None:
                    temp_unit = daily_units.get('temperature_2m_min', '°C')
                    quantity_min = UnitQuantity(temp_min, OpenMeteoConverters.normalize_temperature_unit(temp_unit))
                    if forecast_data.temperature is None:
                        forecast_data.temperature = NumericDataPoint(
                            station = station,
                            source_datetime = source_datetime,
                            quantity_min = quantity_min,
                        )
                    else:
                        forecast_data.temperature.quantity_min = quantity_min

            # Precipitation sum
            if 'precipitation_sum' in daily_data and i < len(daily_data['precipitation_sum']):
                precipitation = daily_data['precipitation_sum'][i]
                if precipitation is not None:
                    precip_unit = daily_units.get('precipitation_sum', 'mm')
                    forecast_data.precipitation_probability = NumericDataPoint(
                        station = station,
                        source_datetime = source_datetime,
                        quantity_ave = UnitQuantity(precipitation, OpenMeteoConverters.normalize_precipitation_unit(precip_unit)),
                    )

            # Weather code
            if 'weathercode' in daily_data and i < len(daily_data['weathercode']):
                weather_code = daily_data['weathercode'][i]
                if weather_code is not None:
                    try:
                        weather_description = OpenMeteoConverters.weather_code_to_description(weather_code)
                        forecast_data.description_short = StringDataPoint(
                            station = station,
                            source_datetime = source_datetime,
                            value = weather_description,
                        )
                    except ValueError:
                        logger.warning(f'Unknown OpenMeteo weather code: {weather_code}')

            # Create interval weather forecast
            interval_weather_forecast = IntervalWeatherForecast(
                interval=time_interval,
                data=forecast_data
            )
            interval_weather_forecast_list.append(interval_weather_forecast)
            continue

        return interval_weather_forecast_list

    def _parse_historical_weather_data(self, 
                                       historical_data: Dict,
                                       geographic_location: GeographicLocation) -> List[WeatherHistoryData]:

        daily_data = historical_data.get('daily', {})
        daily_units = historical_data.get('daily_units', {})
        
        if not daily_data or not daily_data.get('time'):
            raise ValueError('Missing "daily" or "time" in OpenMeteo historical payload.')

        source_datetime = datetimeproxy.now()

        elevation = historical_data.get('elevation')
        elevation_quantity = UnitQuantity(elevation, 'm') if elevation is not None else None

        station = Station(
            source = self.data_point_source,
            station_id = f'openmeteo-history:{geographic_location.latitude:.3f}:{geographic_location.longitude:.3f}',
            name = f'OpenMeteo History ({geographic_location.latitude:.3f}, {geographic_location.longitude:.3f})',
            geo_location = GeographicLocation(
                latitude = historical_data.get('latitude', geographic_location.latitude),
                longitude = historical_data.get('longitude', geographic_location.longitude),
                elevation = elevation_quantity,
            ),
            station_url = None,
            observations_url = None,
            forecast_url = None,
        )

        time_list = daily_data['time']
        interval_weather_history_list = list()
        
        for i, date_str in enumerate(time_list):
            
            try:
                date_obj = datetime.fromisoformat(date_str).date()
                interval_start = datetimeproxy.iso_naive_to_datetime_utc(datetime.combine(date_obj, datetime.min.time()).isoformat())
                interval_end = interval_start + timedelta(days = 1)
            except Exception as e:
                logger.warning(f'Missing or bad date in OpenMeteo historical payload: {e}')
                continue

            time_interval = TimeInterval(
                start = interval_start,
                end = interval_end,
            )

            history_data = WeatherHistoryData()
            
            # Temperature max
            if 'temperature_2m_max' in daily_data and i < len(daily_data['temperature_2m_max']):
                temp_max = daily_data['temperature_2m_max'][i]
                if temp_max is not None:
                    temp_unit = daily_units.get('temperature_2m_max', '°C')
                    history_data.temperature = NumericDataPoint(
                        station = station,
                        source_datetime = source_datetime,
                        quantity_max = UnitQuantity(temp_max, OpenMeteoConverters.normalize_temperature_unit(temp_unit)),
                    )

            # Temperature min
            if 'temperature_2m_min' in daily_data and i < len(daily_data['temperature_2m_min']):
                temp_min = daily_data['temperature_2m_min'][i]
                if temp_min is not None:
                    temp_unit = daily_units.get('temperature_2m_min', '°C')
                    quantity_min = UnitQuantity( temp_min, OpenMeteoConverters.normalize_temperature_unit(temp_unit ))
                    if history_data.temperature is None:
                        history_data.temperature = NumericDataPoint(
                            station = station,
                            source_datetime = source_datetime,
                            quantity_min = quantity_min,
                        )
                    else:
                        history_data.temperature.quantity_min = quantity_min
                        
            # Precipitation sum
            if 'precipitation_sum' in daily_data and i < len(daily_data['precipitation_sum']):
                precipitation = daily_data['precipitation_sum'][i]
                if precipitation is not None:
                    precip_unit = daily_units.get('precipitation_sum', 'mm')
                    history_data.precipitation = NumericDataPoint(
                        station = station,
                        source_datetime = source_datetime,
                        quantity_ave = UnitQuantity(precipitation, OpenMeteoConverters.normalize_precipitation_unit(precip_unit)),
                    )

            # Weather code
            if 'weathercode' in daily_data and i < len(daily_data['weathercode']):
                weather_code = daily_data['weathercode'][i]
                if weather_code is not None:
                    try:
                        weather_description = OpenMeteoConverters.weather_code_to_description(weather_code)
                        history_data.description_short = StringDataPoint(
                            station = station,
                            source_datetime = source_datetime,
                            value = weather_description,
                        )
                    except ValueError:
                        logger.warning(f'Unknown OpenMeteo weather code: {weather_code}')

            interval_weather_history = IntervalWeatherHistory(
                interval = time_interval,
                data = history_data,
            )
            interval_weather_history_list.append( interval_weather_history )
            continue

        return interval_weather_history_list
        
    def _get_current_weather_data(self, geographic_location: GeographicLocation) -> Dict[str, Any]:
        cache_key = f'ws:{self.id}:current:{geographic_location}'
        current_data_str = self.redis_client.get(cache_key)

        if settings.DEBUG and self.SKIP_CACHE:
            logger.warning('Skip caching in effect.')
            current_data_str = None
            
        if current_data_str:
            logger.debug('OpenMeteo current weather data from cache.')
            current_data = json.loads(current_data_str)
            return current_data

        current_data = self._get_current_weather_data_from_api(geographic_location = geographic_location)
        if current_data:
            current_data_str = json.dumps(current_data)
            self.redis_client.set(cache_key, current_data_str,
                                  ex = self.CURRENT_DATA_CACHE_EXPIRY_SECS)
        return current_data

    def _get_current_weather_data_from_api(self, geographic_location: GeographicLocation) -> Dict[str, Any]:
        # Request current weather plus additional hourly data for current hour
        url = (f"{self.BASE_URL}forecast?"
               f"latitude={geographic_location.latitude}&"
               f"longitude={geographic_location.longitude}&"
               f"current_weather=true&"
               f"hourly=temperature_2m,relativehumidity_2m,dewpoint_2m,precipitation,pressure_msl&"
               f"units=metric")
        
        response = requests.get(url, headers = self._headers)
        response.raise_for_status()
        current_data = response.json()           
        return current_data

    def _get_hourly_forecast_data(self, geographic_location: GeographicLocation) -> Dict[str, Any]:
        cache_key = f'ws:{self.id}:forecast-hourly:{geographic_location}'
        forecast_data_str = self.redis_client.get(cache_key)

        if settings.DEBUG and self.SKIP_CACHE:
            logger.warning('Skip caching in effect.')
            forecast_data_str = None
            
        if forecast_data_str:
            logger.debug('OpenMeteo hourly forecast data from cache.')
            forecast_data = json.loads(forecast_data_str)
            return forecast_data

        forecast_data = self._get_hourly_forecast_data_from_api(geographic_location = geographic_location)
        if forecast_data:
            forecast_data_str = json.dumps(forecast_data)
            self.redis_client.set(cache_key, forecast_data_str,
                                  ex = self.FORECAST_DATA_CACHE_EXPIRY_SECS)
        return forecast_data

    def _get_hourly_forecast_data_from_api(self, geographic_location: GeographicLocation) -> Dict[str, Any]:
        # Request 7 days of hourly forecast data
        url = (f"{self.BASE_URL}forecast?"
               f"latitude={geographic_location.latitude}&"
               f"longitude={geographic_location.longitude}&"
               f"hourly=temperature_2m,relativehumidity_2m,windspeed_10m,winddirection_10m,precipitation,weathercode&"
               f"forecast_days=7&"
               f"units=metric")
        
        response = requests.get(url, headers = self._headers)
        response.raise_for_status()
        forecast_data = response.json()           
        return forecast_data

    def _get_daily_forecast_data(self, geographic_location: GeographicLocation) -> Dict[str, Any]:
        cache_key = f'ws:{self.id}:forecast-daily:{geographic_location}'
        forecast_data_str = self.redis_client.get(cache_key)

        if settings.DEBUG and self.SKIP_CACHE:
            logger.warning('Skip caching in effect.')
            forecast_data_str = None
            
        if forecast_data_str:
            logger.debug('OpenMeteo daily forecast data from cache.')
            forecast_data = json.loads(forecast_data_str)
            return forecast_data

        forecast_data = self._get_daily_forecast_data_from_api(geographic_location = geographic_location)
        if forecast_data:
            forecast_data_str = json.dumps(forecast_data)
            self.redis_client.set(cache_key, forecast_data_str,
                                  ex = self.FORECAST_DATA_CACHE_EXPIRY_SECS)
        return forecast_data

    def _get_daily_forecast_data_from_api(self, geographic_location: GeographicLocation) -> Dict[str, Any]:
        # Request 14 days of daily forecast data
        url = (f"{self.BASE_URL}forecast?"
               f"latitude={geographic_location.latitude}&"
               f"longitude={geographic_location.longitude}&"
               f"daily=weathercode,temperature_2m_max,temperature_2m_min,precipitation_sum&"
               f"forecast_days=14&"
               f"units=metric")
        
        response = requests.get(url, headers = self._headers)
        response.raise_for_status()
        forecast_data = response.json()           
        return forecast_data

    def _get_historical_weather_data(self, geographic_location: GeographicLocation, start_date, end_date) -> Dict[str, Any]:
        cache_key = f'ws:{self.id}:historical:{geographic_location}:{start_date}:{end_date}'
        historical_data_str = self.redis_client.get(cache_key)

        if settings.DEBUG and self.SKIP_CACHE:
            logger.warning('Skip caching in effect.')
            historical_data_str = None
            
        if historical_data_str:
            logger.debug('OpenMeteo historical data from cache.')
            historical_data = json.loads(historical_data_str)
            return historical_data

        historical_data = self._get_historical_weather_data_from_api(
            geographic_location = geographic_location,
            start_date = start_date,
            end_date = end_date,
        )
        if historical_data:
            historical_data_str = json.dumps(historical_data)
            self.redis_client.set(cache_key, historical_data_str,
                                  ex = self.HISTORICAL_DATA_CACHE_EXPIRY_SECS)
        return historical_data

    def _get_historical_weather_data_from_api(self, geographic_location: GeographicLocation, start_date, end_date) -> Dict[str, Any]:
        # Request historical weather data from archive API
        url = (f"{self.ARCHIVE_BASE_URL}?"
               f"latitude={geographic_location.latitude}&"
               f"longitude={geographic_location.longitude}&"
               f"start_date={start_date}&"
               f"end_date={end_date}&"
               f"daily=weathercode,temperature_2m_max,temperature_2m_min,precipitation_sum&"
               f"units=metric")
        
        response = requests.get(url, headers = self._headers)
        response.raise_for_status()
        historical_data = response.json()           
        return historical_data
