from datetime import datetime
import json
import logging
import requests

import hi.apps.common.datetimeproxy as datetimeproxy
from hi.apps.weather.weather_data_source import WeatherDataSource
from hi.apps.weather.enums import CloudCoverage
from hi.apps.weather.transient_models import (
    NumericDataPoint,
    WeatherConditionsData,
)
from hi.units import UnitQuantity

logger = logging.getLogger(__name__)


class NationalWeatherService( WeatherDataSource ):

    BASE_URL = "https://api.weather.gov/"

    POINTS_DATA_CACHE_EXPIRY_SECS = 12 * 60 * 60
    STATIONS_DATA_CACHE_EXPIRY_SECS = 12 * 60 * 60
    OBSERVATIONS_DATA_CACHE_EXPIRY_SECS = 5 * 60  # Cache for rate-limit risk reduction
    
    def __init__( self ):
        super().__init__(
            id = 'nws',
            label = 'National Weather Service',
            priority = 1,
            requests_per_day = 144,  # Every 10 minutes
        )

        self._headers = {'User-Agent': 'HomeInformation (weather@homeinformation.org)'}
        return
    
    def get_data(self):

        geographic_location = self.geographic_location
        current_conditions_data = self.get_current_conditions(
            latitude = geographic_location.latitude,
            longitude = geographic_location.longitude,
        )





        
        ##zzz_fold_into_weather_manager





        
        return

    def get_current_conditions( self, latitude : float, longitude : float ) -> WeatherConditionsData:
        observations_data = self._get_observations_data( latitude = latitude, longitude = longitude )
        properties = observations_data['properties']
        if not properties:
            raise ValueError('Missing "properties" in NWS observation payload.')
        
        try:
            timestamp_str = properties.get( 'timestamp' )
            source_datetime = datetime.fromisoformat( timestamp_str )
        except Exception as e:
            # Use local time if problem.
            logger.warning( f'Missing or bad timestamp in NWS observation payload: {e}' )
            source_datetime = datetimeproxy.now()
            
        try:
            elevation = self._parse_nws_quantity(
                nws_data_dict = properties.get( 'elevation' ),
            )
        except Exception as e:
            # Not so important for us, so just assume the standard height.
            logger.warning( f'MIssing or bad elevation in NWS observation payload: {e}' )
            elevation = UnitQuantity( 2, 'm' )
            
        weather_conditions_data = WeatherConditionsData()

        weather_conditions_data.barometric_pressure = self._create_numeric_data_point(
            nws_data_dict = properties.get( 'barometricPressure' ),
            source_datetime = source_datetime,
            elevation = elevation,
        )

        weather_conditions_data.dew_point = self._create_numeric_data_point(
            nws_data_dict = properties.get( 'dewpoint' ),
            source_datetime = source_datetime,
            elevation = elevation,
        )
        weather_conditions_data.heat_index = self._create_numeric_data_point(
            nws_data_dict = properties.get( 'heatIndex' ),
            source_datetime = source_datetime,
            elevation = elevation,
        )
        weather_conditions_data.temperature_max_last_24h = self._create_numeric_data_point(
            nws_data_dict = properties.get( 'maxTemperatureLast24Hours' ),
            source_datetime = source_datetime,
            elevation = elevation,
        )
        weather_conditions_data.temperature_min_last_24h = self._create_numeric_data_point(
            nws_data_dict = properties.get( 'minTemperatureLast24Hours' ),
            source_datetime = source_datetime,
            elevation = elevation,
        )
        weather_conditions_data.precipitation_last_3h = self._create_numeric_data_point(
            nws_data_dict = properties.get( 'precipitationLast3Hours' ),
            source_datetime = source_datetime,
            elevation = elevation,
        )
        weather_conditions_data.precipitation_last_6h = self._create_numeric_data_point(
            nws_data_dict = properties.get( 'precipitationLast6Hours' ),
            source_datetime = source_datetime,
            elevation = elevation,
        )
        weather_conditions_data.precipitation_last_hour = self._create_numeric_data_point(
            nws_data_dict = properties.get( 'precipitationLastHour' ),
            source_datetime = source_datetime,
            elevation = elevation,
        )
        weather_conditions_data.relative_humidity = self._create_numeric_data_point(
            nws_data_dict = properties.get( 'relativeHumidity' ),
            source_datetime = source_datetime,
            elevation = elevation,
        )
        weather_conditions_data.sea_level_pressure = self._create_numeric_data_point(
            nws_data_dict = properties.get( 'seaLevelPressure' ),
            source_datetime = source_datetime,
            elevation = elevation,
        )
        weather_conditions_data.temperature = self._create_numeric_data_point(
            nws_data_dict = properties.get( 'temperature' ),
            source_datetime = source_datetime,
            elevation = elevation,
        )
        weather_conditions_data.visibility = self._create_numeric_data_point(
            nws_data_dict = properties.get( 'visibility' ),
            source_datetime = source_datetime,
            elevation = elevation,
        )
        weather_conditions_data.wind_chill = self._create_numeric_data_point(
            nws_data_dict = properties.get( 'windChill' ),
            source_datetime = source_datetime,
            elevation = elevation,
        )
        weather_conditions_data.wind_direction = self._create_numeric_data_point(
            nws_data_dict = properties.get( 'windDirection' ),
            source_datetime = source_datetime,
            elevation = elevation,
        )
        weather_conditions_data.windspeed_max = self._create_numeric_data_point(
            nws_data_dict = properties.get( 'windGust' ),
            source_datetime = source_datetime,
            elevation = elevation,
        )
        weather_conditions_data.windspeed_ave = self._create_numeric_data_point(
            nws_data_dict = properties.get( 'windSpeed' ),
            source_datetime = source_datetime,
            elevation = elevation,
        )
        
        cloud_layers_list = properties.get( 'cloudLayers' )
        if cloud_layers_list:

            min_cloud_layer_base = None
            highest_coverage = None
            for cloud_layer_data in cloud_layers_list:
                wmo_cloud_coverage_code = cloud_layer_data.get('amount')
                try:
                    cloud_coverage = CloudCoverage.from_wmo_code( wmo_cloud_coverage_code )
                    if ( highest_coverage is None ) or ( cloud_coverage > highest_coverage ):
                        highest_coverage = cloud_coverage
                        
                except ValueError as e:
                    logger.warning( f'Problem parsing NWS cloudLayers amound: {e}' )
                    continue

                try:
                    cloud_layer_base = self._parse_nws_quantity(
                        nws_data_dict = cloud_layer_data.get( 'base' ),
                    )
                    if ( min_cloud_layer_base is None ) or ( cloud_layer_base < min_cloud_layer_base ):
                        min_cloud_layer_base = cloud_layer_base
                        
                except Exception as e:
                    logger.warning( f'Problem parsing NWS cloudLayers base: {e}' )
                    continue
                
                
        present_weather_list = properties.get( 'presentWeather' )

        properties.get( 'textDescription' )
        
        

        return weather_conditions_data

    def _get_observations_data( self, latitude : float, longitude : float ):
        cache_key = f'ws:{self.id}:observations:{latitude}:{longitude}'
        observations_data_str = self.redis_client.get( cache_key )
        if observations_data_str:
            observations_data = json.loads( observations_data_str )
            return observations_data

        observations_data = self._get_observations_data_from_api( latitude = latitude, longitude = longitude )
        if observations_data:
            observations_data_str = json.dumps( observations_data )
            self.redis_client.set( cache_key, observations_data_str,
                                   ex = self.OBSERVATIONS_DATA_CACHE_EXPIRY_SECS  )
        return observations_data

    def _get_observations_data_from_api( self, latitude : float, longitude : float):
        stations_data = self._get_stations_data( latitude = latitude, longitude = longitude )
        station_url = stations_data['observationStations'][0]  # Choose from list????
        observation_url = f'{station_url}/observations/latest'
        observations_response = requests.get( observation_url, headers = self._headers )
        observations_response.raise_for_status()
        observations_data = observations_response.json()           
        return observations_data
    
    def _get_stations_data( self, latitude : float, longitude : float  ):
        cache_key = f'ws:{self.id}:stations:{latitude}:{longitude}'
        stations_data_str = self.redis_client.get( cache_key )
        if stations_data_str:
            stations_data = json.loads( stations_data_str )
            return stations_data
        stations_data = self._get_stations_data_from_api( latitude = latitude, longitude = longitude )
        if stations_data:
            stations_data_str = json.dumps( stations_data )
            self.redis_client.set( cache_key, stations_data_str,
                                   ex = self.STATIONS_DATA_CACHE_EXPIRY_SECS  )
        return stations_data

    def _get_stations_data_from_api( self, latitude : float, longitude : float):
        # Can cache this data, expires 12 hours-ish (they do not change often)
        points_data = self._get_points_data( latitude = latitude, longitude = longitude )
        stations_url = points_data['properties']['observationStations']
        stations_response = requests.get( stations_url, headers = self._headers )
        stations_response.raise_for_status()
        stations_data = stations_response.json()
        return stations_data
        
    def _get_points_data( self, latitude : float, longitude : float  ):
        cache_key = f'ws:{self.id}:points:{latitude}:{longitude}'
        points_data_str = self.redis_client.get( cache_key )
        if points_data_str:
            points_data = json.loads( points_data_str )
            return points_data
        points_data = self._get_points_data_from_api( latitude = latitude, longitude = longitude )
        if points_data:
            points_data_str = json.dumps( points_data )
            self.redis_client.set( cache_key, points_data_str,
                                   ex = self.POINTS_DATA_CACHE_EXPIRY_SECS  )
        return points_data

    def _get_points_data_from_api( self, latitude : float, longitude : float):
        # Can cache this data, expires 12 hours-ish (they do not change often)
        points_url = f'{self.BASE_URL}points/{latitude},{longitude}'
        points_response = requests.get( points_url, headers = self._headers )
        points_response.raise_for_status()
        points_data = points_response.json()
        return points_data

    def _parse_nws_quantity( self, nws_data_dict : dict ) -> UnitQuantity:
        if not nws_data_dict:
            raise ValueError('No data')
        unit_code = nws_data_dict.get('unitCode')
        if not unit_code:
            raise KeyError( 'Missing unit code' )
        if unit_code.startswith( 'wmoUnit:' ):
            units_str = unit_code[8:]
        elif unit_code.startswith( 'unit:' ):
            units_str = unit_code[5:]
        else:
            units_str = unit_code
        value = nws_data_dict.get('value')
        if value is None:
            raise 'Missing value'            
        return UnitQuantity( value, units_str ),
    
    def _create_numeric_data_point( self,
                                    nws_data_dict    : dict,
                                    source_datetime  : datetime,
                                    elevation        : UnitQuantity ) -> NumericDataPoint:
        try:
            quantity = self._parse_nws_quantity( nws_data_dict = nws_data_dict )
            return NumericDataPoint(
                source = self.data_source,
                source_datetime = source_datetime,
                elevation = elevation,
                quantity = quantity,
            )
        except Exception as e:
            logger.error( f'Problem parsing NWS data: {nws_data_dict}: {e}' )
        return None
    
    
