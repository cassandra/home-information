from datetime import datetime
import json
import logging
import requests
from typing import Dict

import hi.apps.common.datetimeproxy as datetimeproxy
from hi.apps.weather.weather_data_source import WeatherDataSource
from hi.apps.weather.enums import WeatherPhenomenonModifier
from hi.apps.weather.transient_models import (
    ListDataPoint,
    NotablePhenomenon,
    NumericDataPoint,
    StringDataPoint,
    WeatherConditionsData,
)
from hi.apps.weather.weather_mixins import WeatherMixin
from hi.apps.weather.wmo_units import WmoUnits
from hi.units import UnitQuantity

from .nws_converters import NwsConverters

logger = logging.getLogger(__name__)


class NationalWeatherService( WeatherDataSource, WeatherMixin ):

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
    
    async def get_data(self):

        geographic_location = self.geographic_location
        if not geographic_location:
            logger.warning( 'No geographic location setting. Skipping NWS weather fetch.' )
            return
            
        current_conditions_data = self.get_current_conditions(
            latitude = geographic_location.latitude,
            longitude = geographic_location.longitude,
        )
        weather_manager = await self.weather_manager_async()
        weather_manager.update_current_conditions(
            weather_data_source = self,
            weather_conditions_data = current_conditions_data,
        )
        return

    def get_current_conditions( self, latitude : float, longitude : float ) -> WeatherConditionsData:
        observations_data = self._get_observations_data( latitude = latitude, longitude = longitude )
        return self._parse_observation_data( observations_data = observations_data )

    def _parse_observation_data( self, observations_data : Dict ) -> WeatherConditionsData:
        
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
        description = properties.get( 'textDescription' )
        if description:
            weather_conditions_data.description = StringDataPoint(
                source = self.data_point_source,
                source_datetime = source_datetime,
                elevation = elevation,
                value = description,
            )
        self._parse_cloud_layers( 
            properties = properties,
            weather_conditions_data = weather_conditions_data,
            source_datetime = source_datetime,
            elevation = elevation,
        )
        self._parse_present_weather( 
            properties = properties,
            weather_conditions_data = weather_conditions_data,
            source_datetime = source_datetime,
            elevation = elevation,
        )
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
            raise ValueError( 'Missing unit code' )
        units_str = WmoUnits.normalize_unit( unit_code )
        value = nws_data_dict.get('value')
        if value is None:
            raise ValueError( 'Missing value' )
        try:
            return UnitQuantity( value, units_str )
        except Exception as e:
            raise ValueError( f'Bad units: {e}' )

    def _create_numeric_data_point( self,
                                    nws_data_dict    : dict,
                                    source_datetime  : datetime,
                                    elevation        : UnitQuantity ) -> NumericDataPoint:
        try:
            quantity = self._parse_nws_quantity( nws_data_dict = nws_data_dict )
            return NumericDataPoint(
                source = self.data_point_source,
                source_datetime = source_datetime,
                elevation = elevation,
                quantity = quantity,
            )
        except Exception as e:
            logger.error( f'Problem parsing NWS data: {nws_data_dict}: {e}' )
        return None

    def _parse_cloud_layers( self,
                             properties               : Dict[ str, str ],
                             weather_conditions_data  : WeatherConditionsData,
                             source_datetime          : datetime,
                             elevation                : UnitQuantity ):
        """
        Translate NWS 'cloudLayers' data into a cloud coverage percentage and
        cloud ceiling height.
        """
        cloud_layers_list = properties.get( 'cloudLayers' )
        if cloud_layers_list is None:
            return
        if not cloud_layers_list:
            logger.info('NWS cloudLayers list is empty; assuming clear skies.')
            weather_conditions_data.cloud_cover = NumericDataPoint(
                source = self.data_point_source,
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
                source = self.data_point_source,
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
                source = self.data_point_source,
                source_datetime = source_datetime,
                elevation = elevation,
                quantity = cloud_cover_quantity,
            )
        return
        
    def _parse_present_weather( self,
                                properties               : Dict[ str, str ],
                                weather_conditions_data  : WeatherConditionsData,
                                source_datetime          : datetime,
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

        present_weather_list = properties.get( 'presentWeather' )
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

        weather_conditions_data.notable_phenomenon_data = ListDataPoint(
            source = self.data_point_source,
            source_datetime = source_datetime,
            elevation = elevation,
            list_value = notable_phenomenon_list,
        )       
        return
