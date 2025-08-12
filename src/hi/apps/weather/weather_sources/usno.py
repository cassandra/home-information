from datetime import datetime, date, time, timedelta
from enum import Enum
import json
import logging
import pytz
import requests
from typing import Any, Dict, List

from django.conf import settings

import hi.apps.common.datetimeproxy as datetimeproxy
from hi.apps.weather.weather_data_source import WeatherDataSource
from hi.apps.weather.transient_models import (
    AstronomicalData,
    IntervalAstronomical,
    TimeDataPoint,
    TimeInterval,
    Station,
    BooleanDataPoint,
    NumericDataPoint,
)
from hi.apps.weather.weather_mixins import WeatherMixin
from hi.transient_models import GeographicLocation
from hi.units import UnitQuantity

logger = logging.getLogger(__name__)


class USNOStatus(Enum):
    """Status codes that can be returned by the USNO API."""
    SUCCESS = "success"
    ERROR = "error"
    NO_DATA = "no_data"
    INVALID_REQUEST = "invalid_request"


class USNO(WeatherDataSource, WeatherMixin):
    """
    US Naval Observatory Astronomical Applications Department API integration.
    
    Provides sunrise, sunset, moonrise, moonset, and moon phase data.
    
    API Documentation: https://aa.usno.navy.mil/data/api
    """

    SOURCE_ID = 'usno'
    BASE_URL = "https://aa.usno.navy.mil/api/rstt/oneday"
    
    # Cache for 25 hours - astronomical data only changes once per day per location
    ASTRONOMICAL_DATA_CACHE_EXPIRY_SECS = 25 * 60 * 60
    
    SKIP_CACHE = False  # For debugging    
    
    def __init__(self):
        super().__init__(
            id = self.SOURCE_ID,
            label = 'US Naval Observatory',
            abbreviation = 'USNO',
            priority = 2,  # Higher priority than sunrise-sunset.org due to moon phase data
            requests_per_day_limit = 1000,  # Conservative estimate
            requests_per_polling_interval = 1,  # Only need one request per day per location
            min_polling_interval_secs = 24 * 60 * 60,  # Daily data - minimum 24 hours
        )

        self._headers = {
            'User-Agent': 'HomeInformation (weather@homeinformation.org)',
        }
        return
    
    def requires_api_key(self) -> bool:
        """USNO API does not require an API key."""
        return False
    
    def get_default_enabled_state(self) -> bool:
        """USNO is enabled by default."""
        return True
    
    async def get_data(self):
        
        geographic_location = self.geographic_location
        if not geographic_location:
            logger.warning('No geographic location setting. Skipping USNO fetch.')
            return
            
        weather_manager = await self.weather_manager_async()
        if not weather_manager:
            logger.warning('Weather manager not available. Skipping USNO fetch.')
            return

        # Fetch 10 days of astronomical data using the new multi-day method
        try:
            astronomical_data_list = self.get_astronomical_data_list(
                geographic_location = geographic_location,
                days_count = 10
            )
            if astronomical_data_list:
                await weather_manager.update_astronomical_data(
                    weather_data_source = self,
                    astronomical_data_list = astronomical_data_list,
                )
        except Exception as e:
            logger.exception(f'Problem fetching USNO multi-day astronomical data: {e}')
                
        # Also update today's astronomical data for backwards compatibility
        try:
            todays_astronomical_data = self.get_astronomical_data(
                geographic_location = geographic_location,
            )
            if todays_astronomical_data:
                await weather_manager.update_todays_astronomical_data(
                    weather_data_source = self,
                    astronomical_data = todays_astronomical_data,
                )
        except Exception as e:
            logger.exception(f'Problem fetching USNO today\'s astronomical data: {e}')

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

    def get_astronomical_data_list(self, geographic_location: GeographicLocation, days_count: int = 10) -> List[IntervalAstronomical]:
        """Get astronomical data for multiple consecutive days starting from today."""
        
        astronomical_data_list = []
        today = datetimeproxy.now().date()
        
        # Get local timezone from superclass
        local_tz = pytz.timezone(self.tz_name)
        
        for day_offset in range(days_count):
            target_date = today + timedelta(days=day_offset)
            
            try:
                # Get astronomical data for this date
                astronomical_data = self.get_astronomical_data(
                    geographic_location=geographic_location,
                    target_date=target_date
                )
                
                if astronomical_data:
                    # Create local day boundaries (midnight to midnight in local time)
                    local_start = local_tz.localize(datetime.combine(target_date, datetime.min.time()))
                    local_end = local_tz.localize(datetime.combine(target_date, datetime.max.time()))
                    
                    # Convert to UTC for internal storage (following IntervalDataManager pattern)
                    interval_start = local_start.astimezone(pytz.UTC)
                    interval_end = local_end.astimezone(pytz.UTC)
                    
                    interval = TimeInterval(
                        start=interval_start,
                        end=interval_end
                    )
                    
                    interval_astronomical = IntervalAstronomical(
                        interval=interval,
                        data=astronomical_data
                    )
                    
                    astronomical_data_list.append(interval_astronomical)
                    
            except Exception as e:
                logger.warning(f'Problem fetching USNO astronomical data for {target_date}: {e}')
                continue
                
        return astronomical_data_list

    def _parse_astronomical_data(self, 
                                 api_data: Dict,
                                 geographic_location: GeographicLocation,
                                 target_date: date) -> AstronomicalData:
        """Parse USNO API response into AstronomicalData object."""
        
        # Check for API errors
        if 'error' in api_data:
            raise ValueError(f'USNO API error: {api_data["error"]}')
            
        properties = api_data.get('properties', {})
        if not properties:
            raise ValueError('Missing "properties" in USNO API response')
            
        data = properties.get('data', {})
        # Note: Empty data is allowed - API might return empty data for some dates

        source_datetime = datetimeproxy.now()
        
        station = Station(
            source = self.data_point_source,
            station_id = f'usno:{geographic_location.latitude:.3f}:{geographic_location.longitude:.3f}',
            name = f'USNO ({geographic_location.latitude:.3f}, {geographic_location.longitude:.3f})',
            geo_location = geographic_location,
            station_url = None,
            observations_url = None,
            forecast_url = None,
        )
        
        astronomical_data = AstronomicalData()
        
        # Parse solar phenomena (sundata)
        sundata = data.get('sundata', [])
        for event in sundata:
            phen = event.get('phen', '').lower()
            time_str = event.get('time')
            
            if time_str and phen in ['rise', 'set', 'upper transit']:
                try:
                    # Parse time - it's already in local time from the API
                    time_obj = self._parse_usno_time(time_str)
                    if time_obj:
                        time_data_point = TimeDataPoint(
                            station = station,
                            source_datetime = source_datetime,
                            value = time_obj,
                        )
                        
                        if phen == 'rise':
                            astronomical_data.sunrise = time_data_point
                        elif phen == 'set':
                            astronomical_data.sunset = time_data_point
                        elif phen == 'upper transit':
                            astronomical_data.solar_noon = time_data_point
                            
                except Exception as e:
                    logger.warning(f'Problem parsing USNO solar {phen} time "{time_str}": {e}')
        
        # Parse lunar phenomena (moondata)
        moondata = data.get('moondata', [])
        for event in moondata:
            phen = event.get('phen', '').lower()
            time_str = event.get('time')
            
            if time_str and phen in ['rise', 'set']:
                try:
                    # Parse time - it's already in local time from the API
                    time_obj = self._parse_usno_time(time_str)
                    if time_obj:
                        time_data_point = TimeDataPoint(
                            station = station,
                            source_datetime = source_datetime,
                            value = time_obj,
                        )
                        
                        if phen == 'rise':
                            astronomical_data.moonrise = time_data_point
                        elif phen == 'set':
                            astronomical_data.moonset = time_data_point
                            
                except Exception as e:
                    logger.warning(f'Problem parsing USNO lunar {phen} time "{time_str}": {e}')
        
        # Parse moon phase data
        try:
            # Get current moon phase information
            curphase = data.get('curphase', '')
            fracillum = data.get('fracillum', '')
            
            if fracillum:
                # Parse fractional illumination (format like "35%" -> 35.0)
                illum_str = fracillum.replace('%', '').strip()
                if illum_str:
                    illumination_percent = float(illum_str)
                    
                    astronomical_data.moon_illumnination = NumericDataPoint(
                        station = station,
                        source_datetime = source_datetime,
                        quantity_ave = UnitQuantity(illumination_percent, 'percent'),
                    )
                    
                    # Determine if moon is waxing based on phase name
                    is_waxing = self._determine_moon_waxing_status(curphase)
                    if is_waxing is not None:
                        astronomical_data.moon_is_waxing = BooleanDataPoint(
                            station = station,
                            source_datetime = source_datetime,
                            value = is_waxing,
                        )
                        
        except Exception as e:
            logger.warning(f'Problem parsing USNO moon phase data: {e}')

        return astronomical_data

    def _parse_usno_time(self, time_str: str) -> time:
        """
        Parse USNO time string. Since we request data with our local timezone offset,
        the returned times are already in local time.
        """
        try:
            # Parse the time string (format: "HH:MM")
            time_parts = time_str.split(':')
            if len(time_parts) != 2:
                return None
                
            hour = int(time_parts[0])
            minute = int(time_parts[1])
            
            # Return the time object - it's already in local time
            return time(hour, minute)
            
        except Exception:
            return None

    def _determine_moon_waxing_status(self, phase_name: str) -> bool:
        """
        Determine if the moon is waxing based on the phase name.
        
        Returns True if waxing, False if waning, None if indeterminate.
        """
        phase_lower = phase_name.lower()
        
        if 'waxing' in phase_lower:
            return True
        elif 'waning' in phase_lower:
            return False
        elif 'new' in phase_lower:
            return True  # New moon is considered start of waxing cycle
        elif 'full' in phase_lower:
            return False  # Full moon is considered start of waning cycle
        elif 'first quarter' in phase_lower or 'first' in phase_lower:
            return True
        elif 'last quarter' in phase_lower or 'last' in phase_lower or 'third quarter' in phase_lower:
            return False
        else:
            # For indeterminate phases, return None
            return None

    def _get_astronomical_api_data(self, geographic_location: GeographicLocation, target_date: date) -> Dict[str, Any]:
        """Get astronomical data from cache or API."""
        cache_key = f'ws:{self.id}:astronomical:{geographic_location.latitude:.3f}:{geographic_location.longitude:.3f}:{target_date}'
        api_data_str = self.redis_client.get(cache_key)

        if settings.DEBUG and self.SKIP_CACHE:
            logger.warning('Skip caching in effect.')
            api_data_str = None
            
        if api_data_str:
            logger.debug('USNO astronomical data from cache.')
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
        """Make API call to USNO for astronomical data."""
        
        # Calculate timezone offset for the request
        local_tz = pytz.timezone(self.tz_name)
        local_dt = local_tz.localize(datetime.combine(target_date, datetime.min.time()))
        offset_seconds = local_dt.utcoffset().total_seconds()
        tz_offset = offset_seconds / 3600  # Convert to hours
        
        # Build API URL with parameters
        url = (f"{self.BASE_URL}?"
               f"date={target_date.isoformat()}&"
               f"coords={geographic_location.latitude},{geographic_location.longitude}&"
               f"tz={tz_offset}")
        
        logger.debug(f'USNO API request: {url}')
        
        response = requests.get(url, headers = self._headers)
        response.raise_for_status()
        api_data = response.json()           
        return api_data