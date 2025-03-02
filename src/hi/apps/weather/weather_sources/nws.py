from datetime import datetime
import json
import logging
import requests
from typing import Any, Dict, List

from django.conf import settings

import hi.apps.common.datetimeproxy as datetimeproxy
import hi.apps.common.geo_utils as geo_utils
from hi.apps.common.utils import str_to_bool
from hi.apps.weather.weather_data_source import WeatherDataSource
from hi.apps.weather.enums import WeatherPhenomenonModifier, WindDirection
from hi.apps.weather.transient_models import (
    BooleanDataPoint,
    DataPointList,
    NotablePhenomenon,
    NumericDataPoint,
    StringDataPoint,
    WeatherConditionsData,
    WeatherForecastData,
    WeatherStation,
)
from hi.apps.weather.weather_mixins import WeatherMixin
from hi.apps.weather.wmo_units import WmoUnits
from hi.transient_models import GeographicLocation
from hi.units import UnitQuantity

from .nws_converters import NwsConverters

logger = logging.getLogger(__name__)


class NationalWeatherService( WeatherDataSource, WeatherMixin ):

    BASE_URL = "https://api.weather.gov/"

    POINTS_DATA_CACHE_EXPIRY_SECS = 12 * 60 * 60  # Can change, but not often
    STATIONS_DATA_CACHE_EXPIRY_SECS = 12 * 60 * 60  # Can change, but not often
    OBSERVATIONS_DATA_CACHE_EXPIRY_SECS = 5 * 60  # Cache for rate-limit risk reduction
    FORECAST_DATA_CACHE_EXPIRY_SECS = 60 * 60
    
    SKIP_CACHE = False  # For debugging    
    
    def __init__( self ):
        super().__init__(
            id = 'nws',
            label = 'National Weather Service',
            priority = 1,
            requests_per_day_limit = 432,
            requests_per_polling_interval = 3,
            min_polling_interval_secs = 10 * 60,  # NWS stations seem to update only hourly
        )

        self._headers = {
            'User-Agent': 'HomeInformation (weather@homeinformation.org)',
            'Feature-Flags': 'forecast_temperature_qv,forecast_wind_speed_qv',  # Important
        }
        return
    
    async def get_data(self):

        geographic_location = self.geographic_location
        if not geographic_location:
            logger.warning( 'No geographic location setting. Skipping NWS weather fetch.' )
            return
            
        current_conditions_data = self.get_current_conditions(
            geographic_location = geographic_location,
        )
        weather_manager = await self.weather_manager_async()
        await weather_manager.update_current_conditions(
            weather_data_source = self,
            weather_conditions_data = current_conditions_data,
        )




        #  ZZZZ get two type of forecasts, but only once an hour???
        # reconsile with superclass logic Maybe the subclass should be
        # responsible for all actual intervals, while superclass is just
        # the min periodicx interval.


        # zzzz Also, need to update the forecast to remove past periods as
        # time advances.

        



        
        
        return

    def get_current_conditions( self, geographic_location : GeographicLocation ) -> WeatherConditionsData:
        weather_station = self._get_weather_station( geographic_location = geographic_location )
        observations_data = self._get_observations_data( weather_station = weather_station )
        return self._parse_observation_data(
            observations_data = observations_data,
            weather_station = weather_station,
        )

    def get_forecast_hourly( self, geographic_location : GeographicLocation ) -> List[ WeatherForecastData ]:
        points_data = self._get_points_data( geographic_location = geographic_location )

        properties_data = points_data.get('properties')
        if not properties_data:
            logger.warning( 'No properties seen in NWS points data response.' )
            return 

        geo_location = self._parse_geometry(
            geometry_dict = properties_data.get('geometry'),
            elevation = None,
        )
        weather_station = WeatherStation(
            source = self.data_point_source,
            station_id = '%s:%s' % ( properties_data.get('gridId'), 'hourly' ),
            name = properties_data.get('gridId'),
            geo_location = geo_location,
            station_url = properties_data.get('forecastOffice'),
            observations_url = None,
            forecast_url = properties_data.get('forecastHourly'),
        )
        if not weather_station.forecast_url:
            logger.warning( 'No hourly forecast URL seen in NWS points data response.' )
            return 

        forecast_hourly_data = self._get_forecast_hourly_data( weather_station = weather_station )
        return self._parse_forecast_data(
            forecast_hourly_data = forecast_hourly_data,
            weather_station = weather_station,
        )

    def get_forecast_12h( self, geographic_location : GeographicLocation ) -> List[ WeatherForecastData ]:
        points_data = self._get_points_data( geographic_location = geographic_location )

        properties_data = points_data.get('properties')
        if not properties_data:
            logger.warning( 'No properties seen in NWS points data response.' )
            return 

        geo_location = self._parse_geometry(
            geometry_dict = properties_data.get('geometry'),
            elevation = None,
        )
        weather_station = WeatherStation(
            source = self.data_point_source,
            station_id = '%s:%s' % ( properties_data.get('gridId'), '12h' ),
            name = properties_data.get('gridId'),
            geo_location = geo_location,
            station_url = properties_data.get('forecastOffice'),
            observations_url = None,
            forecast_url = properties_data.get('forecast'),
        )
        if not weather_station.forecast_url:
            logger.warning( 'No 12h forecast URL seen in NWS points data response.' )
            return 

        forecast_12h_data = self._get_forecast_12h_data( weather_station = weather_station )
        return self._parse_forecast_data(
            forecast_data = forecast_12h_data,
            weather_station = weather_station,
        )

    def _parse_observation_data( self,
                                 observations_data  : Dict,
                                 weather_station    : WeatherStation ) -> WeatherConditionsData:
        
        properties_data = observations_data['properties']
        if not properties_data:
            raise ValueError('Missing "properties" in NWS observation payload.')
        
        try:
            timestamp_str = properties_data.get( 'timestamp' )
            source_datetime = datetime.fromisoformat( timestamp_str )
        except Exception as e:
            # Use current time if problem.
            logger.warning( f'Missing or bad timestamp in NWS observation payload: {e}' )
            source_datetime = datetimeproxy.now()

        elevation = self._parse_elevation( properties_data.get('elevation'),
                                           default = weather_station.elevation )
            
        weather_conditions_data = WeatherConditionsData()

        weather_conditions_data.barometric_pressure = self._create_numeric_data_point(
            nws_data_dict = properties_data.get( 'barometricPressure' ),
            source_datetime = source_datetime,
            weather_station = weather_station,
            elevation = elevation,
        )

        weather_conditions_data.dew_point = self._create_numeric_data_point(
            nws_data_dict = properties_data.get( 'dewpoint' ),
            source_datetime = source_datetime,
            weather_station = weather_station,
            elevation = elevation,
        )
        weather_conditions_data.heat_index = self._create_numeric_data_point(
            nws_data_dict = properties_data.get( 'heatIndex' ),
            source_datetime = source_datetime,
            weather_station = weather_station,
            elevation = elevation,
        )
        weather_conditions_data.temperature_max_last_24h = self._create_numeric_data_point(
            nws_data_dict = properties_data.get( 'maxTemperatureLast24Hours' ),
            source_datetime = source_datetime,
            weather_station = weather_station,
            elevation = elevation,
        )
        weather_conditions_data.temperature_min_last_24h = self._create_numeric_data_point(
            nws_data_dict = properties_data.get( 'minTemperatureLast24Hours' ),
            source_datetime = source_datetime,
            weather_station = weather_station,
            elevation = elevation,
        )
        weather_conditions_data.precipitation_last_3h = self._create_numeric_data_point(
            nws_data_dict = properties_data.get( 'precipitationLast3Hours' ),
            source_datetime = source_datetime,
            weather_station = weather_station,
            elevation = elevation,
        )
        weather_conditions_data.precipitation_last_6h = self._create_numeric_data_point(
            nws_data_dict = properties_data.get( 'precipitationLast6Hours' ),
            source_datetime = source_datetime,
            weather_station = weather_station,
            elevation = elevation,
        )
        weather_conditions_data.precipitation_last_hour = self._create_numeric_data_point(
            nws_data_dict = properties_data.get( 'precipitationLastHour' ),
            source_datetime = source_datetime,
            weather_station = weather_station,
            elevation = elevation,
        )
        weather_conditions_data.relative_humidity = self._create_numeric_data_point(
            nws_data_dict = properties_data.get( 'relativeHumidity' ),
            source_datetime = source_datetime,
            weather_station = weather_station,
            elevation = elevation,
        )
        weather_conditions_data.sea_level_pressure = self._create_numeric_data_point(
            nws_data_dict = properties_data.get( 'seaLevelPressure' ),
            source_datetime = source_datetime,
            weather_station = weather_station,
            elevation = elevation,
        )
        weather_conditions_data.temperature = self._create_numeric_data_point(
            nws_data_dict = properties_data.get( 'temperature' ),
            source_datetime = source_datetime,
            weather_station = weather_station,
            elevation = elevation,
        )
        weather_conditions_data.visibility = self._create_numeric_data_point(
            nws_data_dict = properties_data.get( 'visibility' ),
            source_datetime = source_datetime,
            weather_station = weather_station,
            elevation = elevation,
        )
        weather_conditions_data.wind_chill = self._create_numeric_data_point(
            nws_data_dict = properties_data.get( 'windChill' ),
            source_datetime = source_datetime,
            weather_station = weather_station,
            elevation = elevation,
        )
        weather_conditions_data.wind_direction = self._create_numeric_data_point(
            nws_data_dict = properties_data.get( 'windDirection' ),
            source_datetime = source_datetime,
            weather_station = weather_station,
            elevation = elevation,
        )
        weather_conditions_data.windspeed_max = self._create_numeric_data_point(
            nws_data_dict = properties_data.get( 'windGust' ),
            source_datetime = source_datetime,
            weather_station = weather_station,
            elevation = elevation,
        )
        weather_conditions_data.windspeed_ave = self._create_numeric_data_point(
            nws_data_dict = properties_data.get( 'windSpeed' ),
            source_datetime = source_datetime,
            weather_station = weather_station,
            elevation = elevation,
        )
        description_short = properties_data.get( 'textDescription' )
        if description_short:
            weather_conditions_data.description_short = StringDataPoint(
                weather_station = weather_station,
                source_datetime = source_datetime,
                elevation = elevation,
                value = description_short,
            )
        self._parse_cloud_layers( 
            properties_data = properties_data,
            weather_conditions_data = weather_conditions_data,
            source_datetime = source_datetime,
            weather_station = weather_station,
            elevation = elevation,
        )
        self._parse_present_weather( 
            properties_data = properties_data,
            weather_conditions_data = weather_conditions_data,
            source_datetime = source_datetime,
            weather_station = weather_station,
            elevation = elevation,
        )
        return weather_conditions_data
    
    def _parse_forecast_data( self,
                              forecast_data  : Dict,
                              weather_station       : WeatherStation ) -> List[ WeatherForecastData ]:

        properties_data = forecast_data['properties']
        if not properties_data:
            raise ValueError('Missing "properties" in NWS hourly forecast payload.')

        try:
            timestamp_str = properties_data.get( 'generatedAt' )
            source_datetime = datetime.fromisoformat( timestamp_str )
        except Exception as e:
            # Use current time if problem.
            logger.warning( f'Missing or bad timestamp in NWS hourly forecast payload: {e}' )
            source_datetime = datetimeproxy.now()

        elevation = self._parse_elevation( properties_data.get('elevation'),
                                           default = weather_station.elevation )
        
        period_data_list = properties_data['periods']
        if not period_data_list:
            raise ValueError('Missing "periods" in NWS hourly forecast payload.')

        weather_forecast_data_list = list()
        for period_data in period_data_list:

            forecast_data = WeatherForecastData()
            try:
                interval_start_str = period_data.get( 'startTime' )
                forecast_data.interval_start = datetime.fromisoformat( interval_start_str )
            except Exception as e:
                logger.warning( f'Missing or bad startTime in NWS forecast payload: {e}' )
                continue
            try:
                interval_end_str = period_data.get( 'endTime' )
                forecast_data.interval_end = datetime.fromisoformat( interval_end_str )
            except Exception as e:
                logger.warning( f'Missing or bad endTime in NWS forecast payload: {e}' )
                continue
            
            interval_name = period_data.get('name')
            if interval_name:
                forecast_data.interval_name = StringDataPoint(
                    weather_station = weather_station,
                    source_datetime = source_datetime,
                    elevation = elevation,
                    value = interval_name,
                )
            description_short = period_data.get('shortForecast')
            if description_short:
                forecast_data.description_short = StringDataPoint(
                    weather_station = weather_station,
                    source_datetime = source_datetime,
                    elevation = elevation,
                    value = description_short,
                )
            description_long = period_data.get('detailedForecast')
            if description_long:
                forecast_data.description_long = StringDataPoint(
                    weather_station = weather_station,
                    source_datetime = source_datetime,
                    elevation = elevation,
                    value = description_long,
                )
            is_daytime = period_data.get('isDaytime')
            if is_daytime is not None:
                forecast_data.is_daytime = BooleanDataPoint(
                    weather_station = weather_station,
                    source_datetime = source_datetime,
                    elevation = elevation,
                    value = str_to_bool( is_daytime ),
                )
            forecast_data.precipitation_probability = self._create_numeric_data_point(
                nws_data_dict = period_data.get( 'probabilityOfPrecipitation' ),
                source_datetime = source_datetime,
                weather_station = weather_station,
                elevation = elevation,
            )
            forecast_data.dew_point = self._create_numeric_data_point(
                nws_data_dict = period_data.get( 'dewpoint' ),
                source_datetime = source_datetime,
                weather_station = weather_station,
                elevation = elevation,
            )
            forecast_data.relative_humidity = self._create_numeric_data_point(
                nws_data_dict = period_data.get( 'relativeHumidity' ),
                source_datetime = source_datetime,
                weather_station = weather_station,
                elevation = elevation,
            )
            forecast_data.temperature_ave = self._create_numeric_data_point(
                nws_data_dict = period_data.get( 'temperature' ),
                source_datetime = source_datetime,
                weather_station = weather_station,
                elevation = elevation,
            )
            forecast_data.temperature_min = self._create_numeric_data_point(
                nws_data_dict = period_data.get( 'temperature' ),
                source_datetime = source_datetime,
                weather_station = weather_station,
                elevation = elevation,
                for_min_value = True,
            )
            forecast_data.temperature_max = self._create_numeric_data_point(
                nws_data_dict = period_data.get( 'temperature' ),
                source_datetime = source_datetime,
                weather_station = weather_station,
                elevation = elevation,
                for_max_value = True,
            )
            forecast_data.windspeed_ave = self._create_numeric_data_point(
                nws_data_dict = period_data.get( 'windSpeed' ),
                source_datetime = source_datetime,
                weather_station = weather_station,
                elevation = elevation,
            )
            forecast_data.windspeed_min = self._create_numeric_data_point(
                nws_data_dict = period_data.get( 'windSpeed' ),
                source_datetime = source_datetime,
                weather_station = weather_station,
                elevation = elevation,
                for_min_value = True,
            )
            forecast_data.windspeed_max = self._create_numeric_data_point(
                nws_data_dict = period_data.get( 'windSpeed' ),
                source_datetime = source_datetime,
                weather_station = weather_station,
                elevation = elevation,
                for_max_value = True,
            )
            wind_direction_str = period_data.get( 'windDirection' )
            if wind_direction_str:
                try:
                    wind_direction_enum = WindDirection.from_menomic( wind_direction_str )
                    forecast_data.wind_direction = NumericDataPoint(
                        weather_station = weather_station,
                        source_datetime = source_datetime,
                        elevation = elevation,
                        quantity = UnitQuantity( wind_direction_enum.angle_degrees, 'degrees' )
                    )
                except ValueError:
                    logger.warning( f'Unknown NWS wind direction "{wind_direction_str}"' )
            
            weather_forecast_data_list.append( forecast_data )
            continue

        return weather_forecast_data_list
        
    def _get_observations_data( self, weather_station : WeatherStation ) -> Dict[ str, Any ]:
        cache_key = f'ws:{self.id}:observations:{weather_station.key}'
        observations_data_str = self.redis_client.get( cache_key )

        if settings.DEBUG and self.SKIP_CACHE:
            logger.warning( 'Skip caching in effect.' )
            observations_data_str = None
            
        if observations_data_str:
            logger.debug( 'NWS observations data from cache.' )
            observations_data = json.loads( observations_data_str )
            return observations_data

        observations_data = self._get_observations_data_from_api( weather_station = weather_station )
        if observations_data:
            observations_data_str = json.dumps( observations_data )
            self.redis_client.set( cache_key, observations_data_str,
                                   ex = self.OBSERVATIONS_DATA_CACHE_EXPIRY_SECS  )
        return observations_data

    def _get_observations_data_from_api( self, weather_station : WeatherStation ) -> Dict[ str, Any ]:
        observations_response = requests.get( weather_station.observations_url, headers = self._headers )
        observations_response.raise_for_status()
        observations_data = observations_response.json()           
        return observations_data

    def _get_forecast_hourly_data( self, weather_station : WeatherStation ) -> Dict[ str, Any ]:
        cache_key = f'ws:{self.id}:forecast-hourly:{weather_station.key}'
        forecast_hourly_data_str = self.redis_client.get( cache_key )

        if settings.DEBUG and self.SKIP_CACHE:
            logger.warning( 'Skip caching in effect.' )
            forecast_hourly_data_str = None
            
        if forecast_hourly_data_str:
            logger.debug( 'NWS hourly forecast data from cache.' )
            forecast_hourly_data = json.loads( forecast_hourly_data_str )
            return forecast_hourly_data

        forecast_hourly_data = self._get_forecast_hourly_data_from_api( weather_station = weather_station )
        if forecast_hourly_data:
            forecast_hourly_data_str = json.dumps( forecast_hourly_data )
            self.redis_client.set( cache_key, forecast_hourly_data_str,
                                   ex = self.FORECAST_DATA_CACHE_EXPIRY_SECS  )
        return forecast_hourly_data

    def _get_forecast_hourly_data_from_api( self, weather_station : WeatherStation ) -> Dict[ str, Any ]:
        forecast_hourly_response = requests.get( weather_station.forecast_url, headers = self._headers )
        forecast_hourly_response.raise_for_status()
        forecast_hourly_data = forecast_hourly_response.json()           
        return forecast_hourly_data

    def _get_forecast_12h_data( self, weather_station : WeatherStation ) -> Dict[ str, Any ]:
        cache_key = f'ws:{self.id}:forecast-12h:{weather_station.key}'
        forecast_12h_data_str = self.redis_client.get( cache_key )

        if settings.DEBUG and self.SKIP_CACHE:
            logger.warning( 'Skip caching in effect.' )
            forecast_12h_data_str = None
            
        if forecast_12h_data_str:
            logger.debug( 'NWS 12h forecast data from cache.' )
            forecast_12h_data = json.loads( forecast_12h_data_str )
            return forecast_12h_data

        forecast_12h_data = self._get_forecast_12h_data_from_api( weather_station = weather_station )
        if forecast_12h_data:
            forecast_12h_data_str = json.dumps( forecast_12h_data )
            self.redis_client.set( cache_key, forecast_12h_data_str,
                                   ex = self.FORECAST_DATA_CACHE_EXPIRY_SECS  )
        return forecast_12h_data

    def _get_forecast_12h_data_from_api( self, weather_station : WeatherStation ) -> Dict[ str, Any ]:
        forecast_12h_response = requests.get( weather_station.forecast_url, headers = self._headers )
        forecast_12h_response.raise_for_status()
        forecast_12h_data = forecast_12h_response.json()           
        return forecast_12h_data
    
    def _get_weather_station( self, geographic_location : GeographicLocation  ) -> WeatherStation:
        stations_data = self._get_stations_data( geographic_location = geographic_location )
        return self._get_closest_weather_station(
            geographic_location = geographic_location,
            stations_data = stations_data,
        )
    
    def _get_stations_data( self, geographic_location : GeographicLocation ) -> Dict[ str, Any ]:
        cache_key = f'ws:{self.id}:stations:{geographic_location}'
        stations_data_str = self.redis_client.get( cache_key )

        if settings.DEBUG and self.SKIP_CACHE:
            logger.warning( 'Skip caching in effect.' )
            stations_data_str = None
            
        if stations_data_str:
            logger.debug( 'NWS stations data from cache.' )
            stations_data = json.loads( stations_data_str )
            return stations_data
        
        stations_data = self._get_stations_data_from_api( geographic_location = geographic_location )
        if stations_data:
            stations_data_str = json.dumps( stations_data )
            self.redis_client.set( cache_key, stations_data_str,
                                   ex = self.STATIONS_DATA_CACHE_EXPIRY_SECS  )
        return stations_data

    def _get_stations_data_from_api( self, geographic_location : GeographicLocation ) -> Dict[ str, Any ]:
        # Can cache this data, expires 12 hours-ish (they do not change often)
        points_data = self._get_points_data( geographic_location = geographic_location )
        stations_url = points_data['properties']['observationStations']
        stations_response = requests.get( stations_url, headers = self._headers )
        stations_response.raise_for_status()
        stations_data = stations_response.json()
        return stations_data
        
    def _get_points_data( self, geographic_location : GeographicLocation ) -> Dict[ str, Any ]:
        cache_key = f'ws:{self.id}:points:{geographic_location}'
        points_data_str = self.redis_client.get( cache_key )

        if settings.DEBUG and self.SKIP_CACHE:
            logger.warning( 'Skip caching in effect.' )
            points_data_str = None
            
        if points_data_str:
            logger.debug( 'NWS points data from cache.' )
            points_data = json.loads( points_data_str )
            return points_data
        points_data = self._get_points_data_from_api( geographic_location = geographic_location )
        if points_data:
            points_data_str = json.dumps( points_data )
            self.redis_client.set( cache_key, points_data_str,
                                   ex = self.POINTS_DATA_CACHE_EXPIRY_SECS  )
        return points_data

    def _get_points_data_from_api( self, geographic_location : GeographicLocation ) -> Dict[ str, Any ]:
        # Can cache this data, expires 12 hours-ish (they do not change often)
        points_url = f'{self.BASE_URL}points/{geographic_location.latitude},{geographic_location.longitude}'
        points_response = requests.get( points_url, headers = self._headers )
        points_response.raise_for_status()
        points_data = points_response.json()
        return points_data
    
    def _get_closest_weather_station( self,
                                      geographic_location : GeographicLocation,
                                      stations_data       : Dict ) -> WeatherStation:

        minimum_distance = 9999999.0
        closest_weather_station = None
        for stations_feature_data in stations_data['features']:
            try:
                weather_station = self._get_weather_station_from_station_data_feature( stations_feature_data )
                if not weather_station:
                    continue
                current_distance = geo_utils.get_distance(
                    lat1 = geographic_location.latitude,
                    lng1 = geographic_location.longitude,
                    lat2 = weather_station.geo_location.latitude,
                    lng2 = weather_station.geo_location.longitude,
                )
                if current_distance < minimum_distance:
                    minimum_distance = current_distance
                    closest_weather_station = weather_station
                
            except Exception as e:
                logger.warning( f'NWS stations feature parsing problem: {e}' )
                continue
            continue
        
        if closest_weather_station:
            return closest_weather_station
        
        # Backup if all parsing fails
        if (( 'observationStations' in stations_data )
            and len( stations_data['observationStations']) > 0 ):
            station_url = stations_data['observationStations'][0]  # Choose from list????
            observations_url = f'{station_url}/observations/latest'

            return WeatherStation(
                source = self.data_point_source,
                station_id = station_url.split( '/' )[-1],
                name = 'Unknown',
                geo_location = None,
                station_url = station_url,
                observations_url = observations_url,
                forecast_url = None,
            )

        raise ValueError( 'Problem pasring NWS station data' )
        
    def _get_weather_station_from_station_data_feature( self, stations_feature_data ) -> WeatherStation:
        
        properties_data = stations_feature_data.get('properties')

        if properties_data.get('@type') != 'wx:ObservationStation':
            return None

        if properties_data:
            elevation = self._parse_elevation( properties_data.get('elevation') )
        else:
            elevation = None

        geo_location = self._parse_geometry(
            geometry_dict = stations_feature_data.get('geometry'),
            elevation = elevation,
        )
        
        station_url = properties_data.get('@id')  # Yes, id -> url
        observations_url = f'{station_url}/observations/latest'
        weather_station = WeatherStation(
            source = self.data_point_source,
            station_id = properties_data.get('stationIdentifier'),
            name = properties_data.get('name'),
            geo_location = geo_location,
            station_url = station_url,
            observations_url = observations_url,
            forecast_url = properties_data.get('forecast'),
        )
        
        return weather_station

    def _create_numeric_data_point( self,
                                    nws_data_dict    : Dict[ str, Any ],
                                    source_datetime  : datetime,
                                    weather_station  : WeatherStation,
                                    elevation        : UnitQuantity,
                                    for_min_value    : bool              = False,
                                    for_max_value    : bool              = False  ) -> NumericDataPoint:
        try:
            quantity = self._parse_nws_quantity(
                nws_data_dict = nws_data_dict,
                for_min_value = for_min_value,
                for_max_value = for_max_value,
            )
            if quantity is not None:
                return NumericDataPoint(
                    weather_station = weather_station,
                    source_datetime = source_datetime,
                    elevation = elevation,
                    quantity = quantity,
                )
        except Exception as e:
            logger.error( f'Problem parsing NWS data: {nws_data_dict}: {e}' )
        return None        

    def _parse_geometry( self,
                         geometry_dict  : Dict[ str, Any ],
                         elevation      : UnitQuantity       = None) -> GeographicLocation:
        if not geometry_dict:
            return None
        coordinates_data = geometry_dict.get('coordinates')
        if not coordinates_data or ( len(coordinates_data) != 2 ):
            return None
        return GeographicLocation(
            longitude = coordinates_data[0],
            latitude = coordinates_data[1],
            elevation = elevation,
        )
        
    def _parse_elevation( self,
                          elevations_dict  : Dict[ str, Any ],
                          default          : UnitQuantity     = None ) -> UnitQuantity:
        try:
            elevation = self._parse_nws_quantity(
                nws_data_dict = elevations_dict,
            )
        except Exception as e:
            if default is not None:
                return default
            # Not so important for us, so just assume the standard height.
            logger.warning( f'MIssing or bad elevation in NWS observation payload: {e}' )
            elevation = UnitQuantity( 2, 'm' )
        if elevation is None:
            return default
        return elevation

    def _parse_nws_quantity( self,
                             nws_data_dict  : Dict[ str, Any ],
                             for_min_value  : bool              = False,
                             for_max_value  : bool              = False ) -> UnitQuantity:
        assert not ( for_min_value and for_max_value )
        
        if not nws_data_dict:
            return None

        min_value = nws_data_dict.get( 'minValue' )
        value = nws_data_dict.get( 'value' )
        max_value = nws_data_dict.get( 'maxValue' )

        if min_value is None and value is None and max_value is None:
            return None
        
        unit_code = nws_data_dict.get('unitCode')
        if not unit_code:
            raise ValueError( 'Missing unit code' )
        units_str = WmoUnits.normalize_unit( unit_code )

        def to_unit_quantity( nws_value : float ) -> UnitQuantity:
            if nws_value is None:
                return None
            try:
                return UnitQuantity( nws_value, units_str )
            except Exception as e:
                raise ValueError( f'Bad units: {e}' )
            return

        min_quantity = to_unit_quantity( min_value )
        quantity = to_unit_quantity( value )
        max_quantity = to_unit_quantity( max_value )
        
        if for_min_value:
            if min_quantity is not None:
                return min_quantity
            if quantity is not None:
                return quantity
            return max_quantity
        
        elif for_max_value:
            if max_quantity is not None:
                return max_quantity
            if quantity is not None:
                return quantity
            return min_quantity
        
        else:
            if quantity is not None:
                return quantity
            if min_quantity is None:
                return max_quantity
            if max_quantity is None:
                return min_quantity
            return UnitQuantity( ( min_quantity.magnitude + max_quantity.magnitude ) / 2.0, units_str )
                                       
    def _parse_cloud_layers( self,
                             properties_data          : Dict[ str, str ],
                             weather_conditions_data  : WeatherConditionsData,
                             source_datetime          : datetime,
                             weather_station          : WeatherStation,
                             elevation                : UnitQuantity ):
        """
        Translate NWS 'cloudLayers' data into a cloud coverage percentage and
        cloud ceiling height.
        """
        cloud_layers_list = properties_data.get( 'cloudLayers' )
        if cloud_layers_list is None:
            return
        if not cloud_layers_list:
            logger.info('NWS cloudLayers list is empty; assuming clear skies.')
            weather_conditions_data.cloud_cover = NumericDataPoint(
                weather_station = weather_station,
                source_datetime = source_datetime,
                elevation = elevation,
                quantity = UnitQuantity( 0, 'percent' ),
            )
            return
            
        cloud_ceiling_quantity_min = None
        cloud_coverage_type_max = None
        
        for cloud_layer_data in cloud_layers_list:
            metar_cloud_coverage_code = cloud_layer_data.get('amount')
            try:
                cloud_coverage_type = NwsConverters.to_cloud_coverage_type( metar_cloud_coverage_code )
                if (( cloud_coverage_type_max is None )
                    or ( cloud_coverage_type > cloud_coverage_type_max )):
                    cloud_coverage_type_max = cloud_coverage_type

            except ( TypeError, KeyError ):
                logger.warning( f'Problem parsing NWS cloudLayers amount "{metar_cloud_coverage_code}"' )
                continue

            if not cloud_coverage_type.is_eligible_as_cloud_ceiling:
                continue

            try:
                cloud_layer_base_quantity = self._parse_nws_quantity(
                    nws_data_dict = cloud_layer_data.get( 'base' ),
                )
                if (( cloud_ceiling_quantity_min is None )
                    or ( cloud_layer_base_quantity < cloud_ceiling_quantity_min )):
                    cloud_ceiling_quantity_min = cloud_layer_base_quantity

            except Exception as e:
                logger.warning( f'Problem parsing NWS cloudLayers base: {e}' )
                continue
            
            continue

        if cloud_ceiling_quantity_min:
            weather_conditions_data.cloud_ceiling = NumericDataPoint(
                weather_station = weather_station,
                source_datetime = source_datetime,
                elevation = elevation,
                quantity = cloud_ceiling_quantity_min,
            )                    

        if cloud_coverage_type_max:
            cloud_cover_quantity = UnitQuantity(
                cloud_coverage_type_max.cloud_cover_percent,
                'percent',
            )
            weather_conditions_data.cloud_cover = NumericDataPoint(
                weather_station = weather_station,
                source_datetime = source_datetime,
                elevation = elevation,
                quantity = cloud_cover_quantity,
            )
        return
        
    def _parse_present_weather( self,
                                properties_data          : Dict[ str, Any ],
                                weather_conditions_data  : WeatherConditionsData,
                                source_datetime          : datetime,
                                weather_station          : WeatherStation,
                                elevation                : UnitQuantity ):
        """
        The presentWeather field is populated when
        notable weather events are occurring at the observation time. This
        includes phenomena like rain, snow, thunderstorms, fog, or haze.

        If there are no significant weather events at the time of
        observation, the presentWeather field may be an empty list,
        indicating the absence of notable weather phenomena.
        """
        notable_phenomenon_list = list()

        present_weather_list = properties_data.get( 'presentWeather' )
        if not present_weather_list:
            return

        for present_weather in present_weather_list:

            weather = present_weather.get('weather')
            try:
                weather_phenomenon = NwsConverters.to_weather_phenomenon( weather )
            except ( TypeError, KeyError ):
                logger.warning( f'Problem parsing NWS weather: {weather}' )
                continue
                
            modifier = present_weather.get('modifier')
            if modifier:
                try:
                    weather_phenomenon_modifier = NwsConverters.to_weather_phenomenon_modifier( modifier )
                except ( TypeError, KeyError ):
                    logger.warning( f'Problem parsing NWS weather modifier: {modifier}' )
                    continue
            else:
                weather_phenomenon_modifier = WeatherPhenomenonModifier.NONE
                    
            intensity = present_weather.get('intensity')
            try:
                weather_phenomenon_intensity = NwsConverters.to_weather_phenomenon_intensity( intensity )
            except ( TypeError, KeyError ):
                logger.warning( f'Problem parsing NWS weather intensity: {intensity}' )
                continue
                
            modifier = present_weather.get('modifier')
            weather = present_weather.get('weather')

            # A particular weather phenomenon is occurring near the
            # observation station but not directly overhead. (METAR code
            # 'VC')
            #
            in_vicinity = present_weather.get('inVicinity')

            # Note that the intensity, modifier and weather fields are
            # already parsed representations from the "rawString" field
            # which has METAR codes and modifiers. Thus, we ignore the
            # "rawString" field.
            #
            _ = present_weather.get('rawString')
            notable_phenomenon = NotablePhenomenon(
                weather_phenomenon = weather_phenomenon,
                weather_phenomenon_modifier = weather_phenomenon_modifier,
                weather_phenomenon_intensity = weather_phenomenon_intensity,
                in_vicinity = in_vicinity,
            )
            notable_phenomenon_list.append( notable_phenomenon )    
            continue

        weather_conditions_data.notable_phenomenon_data = DataPointList(
            weather_station = weather_station,
            source_datetime = source_datetime,
            elevation = elevation,
            list_value = notable_phenomenon_list,
        )       
        return
