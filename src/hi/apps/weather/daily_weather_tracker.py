"""
Daily Weather Data Tracking

Generalized tracking of daily weather statistics using calendar days in local timezone.
Provides fallback values when weather APIs don't provide daily extremes or aggregations.

Currently implements:
- Temperature min/max tracking

Designed for easy extension to track other weather fields like:
- Humidity min/max
- Wind speed max
- Pressure min/max
- Precipitation totals
- etc.
"""
import json
import logging
from datetime import datetime
from typing import Optional, Tuple, Dict, Any

import hi.apps.common.datetimeproxy as datetimeproxy
from django.core.cache import cache
from django.utils import timezone
from hi.apps.weather.transient_models import NumericDataPoint, DataPointSource, Station, WeatherConditionsData
from hi.units import UnitQuantity

logger = logging.getLogger(__name__)


class DailyWeatherTracker:
    """
    Tracks daily weather statistics for fallback values.
    
    Uses calendar days in local timezone and stores daily min/max/sum/count
    statistics for various weather fields.
    """
    
    # Redis cache key prefix
    CACHE_KEY_PREFIX = "weather:daily_stats"
    
    # Cache timeout (7 days)
    CACHE_TIMEOUT_SECONDS = 7 * 24 * 60 * 60
    
    # Supported statistic types
    STAT_MIN = 'min'
    STAT_MAX = 'max'
    STAT_SUM = 'sum'
    STAT_COUNT = 'count'
    STAT_AVG = 'avg'  # Computed from sum/count
    
    # Field names
    FIELD_TEMPERATURE = 'temperature'
    
    def __init__(self, user_timezone=None):
        """
        Initialize the daily weather tracker.
        
        Args:
            user_timezone: Timezone for day boundaries (defaults to Django's TIME_ZONE)
        """
        self._user_timezone = user_timezone or timezone.get_current_timezone()
        
        self._fallback_source = DataPointSource(
            id="daily_weather_tracker",
            label="Daily Weather Tracker",
            abbreviation="DWT",
            priority=1000  # Low priority fallback source
        )
    
    def record_weather_conditions( self,
                                   weather_conditions_data : WeatherConditionsData,
                                   location_key            : str = "default") -> None:
        """
        Record weather conditions and update daily statistics.
        
        Currently tracks:
        - Temperature min/max
        
        Args:
            weather_conditions_data: Complete weather conditions data
            location_key: Unique identifier for the location
        """
        # Record temperature if available
        if ( weather_conditions_data.temperature 
             and weather_conditions_data.temperature.quantity_ave is not None ):
            temp_celsius = weather_conditions_data.temperature.quantity_ave.to('degree_Celsius').magnitude
            temp_timestamp = weather_conditions_data.temperature.source_datetime or datetimeproxy.now()

            self._record_field_value(
                location_key=location_key,
                field_name=self.FIELD_TEMPERATURE,
                value=temp_celsius,
                units='degree_Celsius',
                timestamp=temp_timestamp,
                track_stats=[self.STAT_MIN, self.STAT_MAX]
            )
        else:
            logger.warning(f"record_weather_conditions called for {location_key} but no temperature data available")
        
        # Future: Add other weather field tracking here
        # if weather_conditions_data.relative_humidity:
        #     self._record_humidity(weather_conditions_data.relative_humidity, location_key)
        # if weather_conditions_data.windspeed:
        #     self._record_wind_speed(weather_conditions_data.windspeed, location_key)
    
    def populate_daily_fallbacks( self,
                                  weather_conditions_data : WeatherConditionsData,
                                  location_key            : str = "default") -> None:
        """
        Populate missing daily weather data with fallback values from tracking.
        
        Currently supports:
        - temperature_min_today / temperature_max_today
        
        Args:
            weather_conditions_data: Weather conditions to populate with fallbacks
            location_key: Unique identifier for the location
        """
        try:
            # Populate today's temperature min/max if not already provided by APIs
            if ( not weather_conditions_data.temperature_min_today
                 or not weather_conditions_data.temperature_max_today ):
                min_temp, max_temp = self.get_temperature_min_max_today(location_key)
                
                if min_temp and not weather_conditions_data.temperature_min_today:
                    weather_conditions_data.temperature_min_today = min_temp
                    
                if max_temp and not weather_conditions_data.temperature_max_today:
                    weather_conditions_data.temperature_max_today = max_temp
            
            # Future: Add other fallback population here
            # self._populate_humidity_fallbacks(weather_conditions_data, location_key)
            # self._populate_wind_fallbacks(weather_conditions_data, location_key)
        except Exception as e:
            logger.exception(f"Error in populate_daily_fallbacks for location {location_key}: {e}")
            # Don't re-raise - this should never break the caller
    
    def get_temperature_min_max_today(
            self,
            location_key: str = "default") -> Tuple[Optional[NumericDataPoint], Optional[NumericDataPoint]]:
        """
        Get today's minimum and maximum temperatures.
        
        Args:
            location_key: Unique identifier for the location
            
        Returns:
            Tuple of (min_temperature, max_temperature) as NumericDataPoint objects,
            or (None, None) if no data available
        """
        try:
            field_stats = self._get_field_stats_today(location_key, self.FIELD_TEMPERATURE)
            
            min_data = field_stats.get(self.STAT_MIN)
            max_data = field_stats.get(self.STAT_MAX)
            
            if not min_data or not max_data:
                return None, None
            
            # Create fallback station
            fallback_station = Station(
                source=self._fallback_source,
                station_id="daily_tracker",
                name="Daily Weather Tracker"
            )
            
            # Create NumericDataPoint objects
            min_datapoint = NumericDataPoint(
                station=fallback_station,
                source_datetime=datetime.fromisoformat(min_data['timestamp']),
                quantity_ave=UnitQuantity(min_data['value'], min_data['units'])
            )
            
            max_datapoint = NumericDataPoint(
                station=fallback_station,
                source_datetime=datetime.fromisoformat(max_data['timestamp']),
                quantity_ave=UnitQuantity(max_data['value'], max_data['units'])
            )
            
            logger.debug(f"Retrieved today's temperature min/max for location {location_key}:"
                         f" {min_data['value']:.1f}°C / {max_data['value']:.1f}°C")
            
            return min_datapoint, max_datapoint
            
        except Exception as e:
            logger.exception(f"Error getting today's temperature min/max: {e}")
            return None, None
    
    def _record_field_value( self, 
                             location_key : str, 
                             field_name   : str, 
                             value        : float, 
                             units        : str,
                             timestamp    : datetime,
                             track_stats  : list ) -> None:
        """
        Record a value for a weather field and update specified statistics.
        
        Args:
            location_key: Unique identifier for the location
            field_name: Name of the weather field (e.g., 'temperature')
            value: Numeric value to record
            units: Units of the value
            timestamp: When the value was observed
            track_stats: List of statistics to track (STAT_MIN, STAT_MAX, etc.)
        """
        try:
            # Get current date in local timezone
            now_local = datetimeproxy.now().astimezone(self._user_timezone)
            date_key = now_local.strftime('%Y-%m-%d')
            
            # Get current field statistics
            field_stats = self._get_field_stats(location_key, date_key, field_name)
            
            # Update statistics
            updated = False
            
            if self.STAT_MIN in track_stats:
                min_data = field_stats.get(self.STAT_MIN)
                if not min_data or value < min_data['value']:
                    field_stats[self.STAT_MIN] = {
                        'value': value,
                        'units': units,
                        'timestamp': timestamp.isoformat()
                    }
                    updated = True
            
            if self.STAT_MAX in track_stats:
                max_data = field_stats.get(self.STAT_MAX)
                if not max_data or value > max_data['value']:
                    field_stats[self.STAT_MAX] = {
                        'value': value,
                        'units': units,
                        'timestamp': timestamp.isoformat()
                    }
                    updated = True
            
            if self.STAT_SUM in track_stats:
                sum_data = field_stats.get(self.STAT_SUM, {'value': 0, 'units': units})
                field_stats[self.STAT_SUM] = {
                    'value': sum_data['value'] + value,
                    'units': units,
                    'last_updated': timestamp.isoformat()
                }
                updated = True
            
            if self.STAT_COUNT in track_stats:
                count_data = field_stats.get(self.STAT_COUNT, {'value': 0})
                field_stats[self.STAT_COUNT] = {
                    'value': count_data['value'] + 1,
                    'last_updated': timestamp.isoformat()
                }
                updated = True
            
            # Store updated statistics if changed
            if updated:
                self._store_field_stats(location_key, date_key, field_name, field_stats)
                logger.debug( f"Updated daily {field_name} stats for {date_key} at location {location_key}: "
                              f"min={field_stats.get('min', {}).get('value', 'None')}°C, "
                              f"max={field_stats.get('max', {}).get('value', 'None')}°C, "
                              f"new_value={value}°C")
            else:
                logger.warning(f"Temperature {value}°C not recorded"
                               f" - no min/max update needed for {date_key}")
                
        except Exception as e:
            logger.exception(f"Error recording {field_name} value: {e}")
    
    def _get_field_stats(self, location_key: str, date_key: str, field_name: str) -> Dict[str, Any]:
        """Get field statistics from cache."""
        cache_key = self._get_cache_key(location_key, date_key, field_name)
        stats_json = cache.get(cache_key)
        
        if stats_json:
            try:
                return json.loads(stats_json)
            except (json.JSONDecodeError, TypeError):
                logger.warning(f"Invalid field stats cache data for {field_name} on {date_key}")
        
        return {}
    
    def _get_field_stats_today(self, location_key: str, field_name: str) -> Dict[str, Any]:
        """Get today's field statistics."""
        today_local = datetimeproxy.now().astimezone(self._user_timezone)
        date_key = today_local.strftime('%Y-%m-%d')
        return self._get_field_stats(location_key, date_key, field_name)
    
    def _store_field_stats( self,
                            location_key : str,
                            date_key     : str,
                            field_name   : str,
                            stats        : Dict[str, Any]) -> None:
        """Store field statistics to cache."""
        cache_key = self._get_cache_key(location_key, date_key, field_name)
        stats_json = json.dumps(stats)
        success = cache.set(cache_key, stats_json, timeout=self.CACHE_TIMEOUT_SECONDS)
        if not success:
            logger.warning(f"Cache set failed for {field_name} stats on {date_key}")
    
    def clear_today(self, location_key: str = "default", field_name: Optional[str] = None) -> None:
        """
        Clear today's data for a specific field or all fields.
        
        Args:
            location_key: Unique identifier for the location
            field_name: Specific field to clear, or None to clear all
        """
        today_local = datetimeproxy.now().astimezone(self._user_timezone)
        date_key = today_local.strftime('%Y-%m-%d')
        
        if field_name:
            cache_key = self._get_cache_key(location_key, date_key, field_name)
            cache.delete(cache_key)
            logger.info(f"Cleared today's {field_name} data for {location_key}")
        else:
            # Clear all fields - would need to iterate through known fields
            # For now, just clear temperature since that's what we implement
            self.clear_today(location_key, self.FIELD_TEMPERATURE)
    
    def get_daily_summary(self, location_key: str = "default") -> Dict[str, Any]:
        """
        Get today's weather summary for debugging.
        
        Returns:
            Dict with field statistics or empty dict if no data
        """
        today_local = datetimeproxy.now().astimezone(self._user_timezone)
        date_key = today_local.strftime('%Y-%m-%d')
        
        summary = {
            'date': date_key,
            'timezone': str(self._user_timezone),
            'fields': {}
        }
        
        # Add temperature stats if available
        temp_stats = self._get_field_stats(location_key, date_key, self.FIELD_TEMPERATURE)
        if temp_stats:
            summary['fields'][self.FIELD_TEMPERATURE] = temp_stats
        
        # Return None if no fields have data
        if not summary['fields']:
            return None
            
        return summary
    
    def _get_cache_key(self, location_key: str, date_key: str, field_name: str) -> str:
        """Generate cache key for field statistics.
        
        Single source of truth for cache key format to ensure consistency
        between storage and retrieval operations.
        """
        return f"{self.CACHE_KEY_PREFIX}:{location_key}:{date_key}:{field_name}"
