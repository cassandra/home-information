from datetime import datetime, date
from enum import Enum
import json
import logging
import requests
from typing import Any, Dict

from django.conf import settings

import hi.apps.common.datetimeproxy as datetimeproxy
from hi.apps.weather.weather_data_source import WeatherDataSource
from hi.apps.weather.transient_models import (
    AstronomicalData,
    TimeDataPoint,
    Station,
)
from hi.apps.weather.weather_mixins import WeatherMixin
from hi.transient_models import GeographicLocation

logger = logging.getLogger(__name__)


class SunriseSunsetStatus(Enum):
    """Status codes returned by the Sunrise-Sunset API."""
    OK = "OK"
    INVALID_REQUEST = "INVALID_REQUEST"
    INVALID_DATE = "INVALID_DATE" 
    UNKNOWN_ERROR = "UNKNOWN_ERROR"
    INVALID_TZID = "INVALID_TZID"


class SunriseSunsetOrg(WeatherDataSource, WeatherMixin):

    SOURCE_ID = 'sunrise-sunset-org'
    BASE_URL = "https://api.sunrise-sunset.org/json"
    
    # Cache for 25 hours - astronomical data only changes once per day per location
    ASTRONOMICAL_DATA_CACHE_EXPIRY_SECS = 25 * 60 * 60
    
    SKIP_CACHE = False  # For debugging    
    
    def __init__(self):
        super().__init__(
            id = self.SOURCE_ID,
            label = 'Sunrise-Sunset.org',
            abbreviation = 'SunriseSunset',
            priority = 3,  # Lower priority than NWS and OpenMeteo
            requests_per_day_limit = 1000,  # Conservative estimate for "reasonable" usage
            requests_per_polling_interval = 1,  # Only need one request per day per location
            min_polling_interval_secs = 24 * 60 * 60,  # Daily data - minimum 24 hours
        )

        self._headers = {
            'User-Agent': 'HomeInformation (weather@homeinformation.org)',
        }
        return
    
    def requires_api_key(self) -> bool:
        """Sunrise-Sunset API does not require an API key."""
        return False
    
    def get_default_enabled_state(self) -> bool:
        """Sunrise-Sunset is enabled by default."""
        return True
    
    async def get_data(self):
        
        geographic_location = self.geographic_location
        if not geographic_location:
            logger.warning('No geographic location setting. Skipping Sunrise-Sunset.org fetch.')
            return
            
        weather_manager = await self.weather_manager_async()
        if not weather_manager:
            logger.warning('Weather manager not available. Skipping Sunrise-Sunset.org fetch.')
            return

        # Fetch astronomical data
        try:
            astronomical_data = self.get_astronomical_data(
                geographic_location = geographic_location,
            )
            if astronomical_data:
                await weather_manager.update_astronomical_data(
                    weather_data_source = self,
                    astronomical_data_list = [astronomical_data],
                )
        except Exception as e:
            logger.exception(f'Problem fetching Sunrise-Sunset.org astronomical data: {e}')

        return

    def get_astronomical_data(self, geographic_location: GeographicLocation, target_date: date = None) -> AstronomicalData:
        """Get astronomical data for a specific date and location."""
        if target_date is None:
            target_date = datetimeproxy.now().date()
            
        api_data = self._get_astronomical_api_data(
            geographic_location = geographic_location,
            target_date = target_date,
        )
        return self._parse_astronomical_data(
            api_data = api_data,
            geographic_location = geographic_location,
            target_date = target_date,
        )

    def _parse_astronomical_data(self, 
                                 api_data: Dict,
                                 geographic_location: GeographicLocation,
                                 target_date: date) -> AstronomicalData:
        
        # Check API status
        status = api_data.get('status')
        if status != SunriseSunsetStatus.OK.value:
            raise ValueError(f'Sunrise-Sunset API error: {status}')
            
        results = api_data.get('results', {})
        if not results:
            raise ValueError('Missing "results" in Sunrise-Sunset API response')

        source_datetime = datetimeproxy.now()
        
        station = Station(
            source = self.data_point_source,
            station_id = f'sunrise-sunset-org:{geographic_location.latitude:.3f}:{geographic_location.longitude:.3f}',
            name = f'Sunrise-Sunset.org ({geographic_location.latitude:.3f}, {geographic_location.longitude:.3f})',
            geo_location = geographic_location,
            station_url = None,
            observations_url = None,
            forecast_url = None,
        )
        
        astronomical_data = AstronomicalData()
        
        # Parse time fields from UTC ISO format
        time_fields = [
            ('sunrise', 'sunrise'),
            ('sunset', 'sunset'), 
            ('solar_noon', 'solar_noon'),
            ('civil_twilight_begin', 'civil_twilight_begin'),
            ('civil_twilight_end', 'civil_twilight_end'),
            ('nautical_twilight_begin', 'nautical_twilight_begin'),
            ('nautical_twilight_end', 'nautical_twilight_end'),
            ('astronomical_twilight_begin', 'astronomical_twilight_begin'),
            ('astronomical_twilight_end', 'astronomical_twilight_end'),
        ]
        
        for api_field, data_field in time_fields:
            time_str = results.get(api_field)
            if time_str:
                try:
                    time_utc = datetimeproxy.iso_naive_to_datetime_utc(time_str)
                    time_data_point = TimeDataPoint(
                        station = station,
                        source_datetime = source_datetime,
                        value = time_utc.time(),
                    )
                    setattr(astronomical_data, data_field, time_data_point)
                except Exception as e:
                    logger.warning(f'Problem parsing {api_field} time "{time_str}": {e}')

        return astronomical_data
        
    def _get_astronomical_api_data(self, geographic_location: GeographicLocation, target_date: date) -> Dict[str, Any]:
        cache_key = f'ws:{self.id}:astronomical:{geographic_location.latitude:.3f}:{geographic_location.longitude:.3f}:{target_date}'
        api_data_str = self.redis_client.get(cache_key)

        if settings.DEBUG and self.SKIP_CACHE:
            logger.warning('Skip caching in effect.')
            api_data_str = None
            
        if api_data_str:
            logger.debug('Sunrise-Sunset.org astronomical data from cache.')
            api_data = json.loads(api_data_str)
            return api_data

        api_data = self._get_astronomical_api_data_from_api(
            geographic_location = geographic_location,
            target_date = target_date,
        )
        if api_data:
            api_data_str = json.dumps(api_data)
            self.redis_client.set(cache_key, api_data_str,
                                  ex = self.ASTRONOMICAL_DATA_CACHE_EXPIRY_SECS)
        return api_data

    def _get_astronomical_api_data_from_api(self, geographic_location: GeographicLocation, target_date: date) -> Dict[str, Any]:
        # Build API URL with parameters
        url = (f"{self.BASE_URL}?"
               f"lat={geographic_location.latitude}&"
               f"lng={geographic_location.longitude}&"
               f"date={target_date.isoformat()}&"
               f"formatted=0")  # Get ISO format times
        
        response = requests.get(url, headers = self._headers)
        response.raise_for_status()
        api_data = response.json()           
        return api_data