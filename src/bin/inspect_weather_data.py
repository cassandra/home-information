#!/usr/bin/env python3
"""
Weather Data Inspector

A utility script for inspecting the weather data aggregation pipeline. 
This script follows the proper data flow pattern:

1. Calls get_data() on weather sources to populate WeatherManager data structures
2. Inspects the aggregated data from WeatherManager (the final processed results)

This approach correctly follows the WeatherDataSource interface where get_data() 
is the entry point that populates internal structures, and WeatherManager 
provides the aggregated, processed data (e.g., NWS 12-hour forecasts -> daily).

Usage:
    python src/bin/inspect_weather_data.py [options]

Options:
    --source <source>     Weather source to inspect (openmeteo, nws, all)
    --data-type <type>    Data type to inspect (current, hourly, daily, history, all)
    --compact             Use compact output format
    --raw-only            Show only weather source fetch results
    --parsed-only         Show only parsed data structures (same as raw-only)
    --aggregated-only     Show only aggregated data from weather manager
    --limit <n>           Limit number of records shown (default: 5)
"""

import argparse
import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict
import zoneinfo

# Add the Django app to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root / 'src'))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hi.settings')
import django
django.setup()

# Now import the weather modules
from asgiref.sync import sync_to_async
from hi.apps.weather.weather_manager import WeatherManager
from hi.apps.weather.weather_source_discovery import WeatherSourceDiscovery
from hi.apps.weather.transient_models import (
    DataPoint,
    NumericDataPoint,
    StringDataPoint,
    BooleanDataPoint,
    TimeDataPoint,
)


class WeatherDataInspector:
    """Inspector for weather data flow using high-level weather APIs."""
    
    def __init__(self, compact: bool = False, limit: int = 5):
        self.compact = compact
        self.limit = limit
        # Initialize these in sync context later
        self.weather_manager = None
        self.weather_sources = None
        self.timezone_name = None
    
    def _initialize_sync_components(self):
        """Initialize Django components in sync context."""
        
        if self.weather_manager is None:
            self.weather_manager = WeatherManager()
            self.weather_manager.ensure_initialized()
        
        if self.weather_sources is None:
            self.weather_sources = WeatherSourceDiscovery.discover_weather_data_source_instances()
        
        if self.timezone_name is None:
            from hi.apps.console.console_helper import ConsoleSettingsHelper
            console_helper = ConsoleSettingsHelper()
            self.timezone_name = console_helper.get_tz_name()
            
        # Initialize timezone object for conversions
        if hasattr(self, 'timezone_name') and self.timezone_name:
            try:
                self.timezone = zoneinfo.ZoneInfo(self.timezone_name)
            except Exception:
                # Fallback to UTC if timezone is invalid
                self.timezone = zoneinfo.ZoneInfo('UTC')
        else:
            self.timezone = zoneinfo.ZoneInfo('UTC')
    
    async def _initialize_components(self):
        """Initialize components using sync_to_async."""
        await sync_to_async(self._initialize_sync_components, thread_sensitive=True)()
        
    def format_header(self, title: str) -> str:
        """Format a section header."""
        if self.compact:
            return f"\n--- {title} ---"
        else:
            border = "=" * (len(title) + 4)
            return f"\n{border}\n  {title}\n{border}"
    
    def format_subheader(self, title: str) -> str:
        """Format a subsection header."""
        if self.compact:
            return f"\n- {title}:"
        else:
            return f"\n{'-' * len(title)}\n{title}\n{'-' * len(title)}"
    
    def convert_to_local_timezone(self, dt: datetime) -> datetime:
        """Convert UTC datetime to configured local timezone."""
        if dt is None:
            return None
        
        # Ensure datetime is timezone-aware (assume UTC if naive)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=zoneinfo.ZoneInfo('UTC'))
        
        # Convert to local timezone
        if hasattr(self, 'timezone'):
            return dt.astimezone(self.timezone)
        else:
            return dt
    
    def format_data_point(self, dp: DataPoint, show_station: bool = False, show_time: bool = True) -> str:
        """Format a DataPoint for display."""
        if dp is None:
            return "None"
        
        value_str = ""
        if isinstance(dp, NumericDataPoint):
            # NumericDataPoint has quantity_ave, quantity_min, quantity_max
            if dp.quantity_ave is not None:
                value_str = f"{dp.quantity_ave.magnitude} {dp.quantity_ave.units}"
            elif dp.quantity_min is not None and dp.quantity_max is not None:
                if dp.quantity_min == dp.quantity_max:
                    value_str = f"{dp.quantity_min.magnitude} {dp.quantity_min.units}"
                else:
                    value_str = f"{dp.quantity_min.magnitude}-{dp.quantity_max.magnitude} {dp.quantity_min.units}"
            elif dp.quantity_min is not None:
                value_str = f"{dp.quantity_min.magnitude} {dp.quantity_min.units}"
            elif dp.quantity_max is not None:
                value_str = f"{dp.quantity_max.magnitude} {dp.quantity_max.units}"
            else:
                value_str = "No quantity data"
        elif isinstance(dp, (StringDataPoint, BooleanDataPoint, TimeDataPoint)):
            value_str = str(dp.value)
        else:
            value_str = str(dp.value) if hasattr(dp, 'value') else str(dp)
        
        if self.compact:
            if show_time and dp.source_datetime:
                local_dt = self.convert_to_local_timezone(dp.source_datetime)
                timestamp = local_dt.strftime('%H:%M') if local_dt else "?"
                return f"{value_str} (@{timestamp})"
            else:
                return value_str
        else:
            parts = [value_str]
            if show_station and dp.station:
                parts.append(f"Station: {dp.station.name if dp.station else 'Unknown'}")
            if show_time and dp.source_datetime:
                local_dt = self.convert_to_local_timezone(dp.source_datetime)
                timestamp = local_dt.strftime('%Y-%m-%d %H:%M:%S') if local_dt else "No timestamp"
                parts.append(f"Time: {timestamp}")
            
            if len(parts) > 1:
                return f"{parts[0]} [{', '.join(parts[1:])}]"
            else:
                return parts[0]
    
    def get_station_info(self, data_object) -> str:
        """Extract station information from the first data point found."""
        if not hasattr(data_object, '__dataclass_fields__'):
            return ""
        
        # Find the first non-None DataPoint to get station info
        for field_name in data_object.__dataclass_fields__:
            field_value = getattr(data_object, field_name, None)
            if field_value is not None and isinstance(field_value, DataPoint):
                if field_value.station:
                    return f"Station: {field_value.station.name}"
                else:
                    return "Station: Unknown"
        return ""
    
    def get_source_time_info(self, data_object) -> str:
        """Extract source time information from the first data point found."""
        if not hasattr(data_object, '__dataclass_fields__'):
            return ""
        
        # Find the first non-None DataPoint to get source time info
        for field_name in data_object.__dataclass_fields__:
            field_value = getattr(data_object, field_name, None)
            if field_value is not None and isinstance(field_value, DataPoint):
                if field_value.source_datetime:
                    local_dt = self.convert_to_local_timezone(field_value.source_datetime)
                    if local_dt:
                        if self.compact:
                            return f"Source Time: {local_dt.strftime('%m/%d %H:%M')}"
                        else:
                            return f"Source Time: {local_dt.strftime('%Y-%m-%d %H:%M:%S')}"
                    else:
                        return "Source Time: Unknown"
                else:
                    return "Source Time: Unknown"
        return ""
    
    def format_weather_data_summary(self, data: Any, title: str = "") -> str:
        """Format weather data structures for compact display."""
        if data is None:
            return f"{title}: None" if title else "None"
        
        result = f"{self.format_subheader(title)}\n" if title else ""
        
        if hasattr(data, '__dataclass_fields__'):
            # Handle dataclass objects
            station_info = self.get_station_info(data)
            source_time_info = self.get_source_time_info(data)
            
            if station_info:
                result += f"  {station_info}\n"
            if source_time_info:
                result += f"  {source_time_info}\n"
            
            non_none_fields = []
            for field_name in data.__dataclass_fields__:
                field_value = getattr(data, field_name, None)
                if field_value is not None:
                    if isinstance(field_value, DataPoint):
                        non_none_fields.append(f"  {field_name}: {self.format_data_point(field_value, show_station=False, show_time=False)}")
                    elif hasattr(field_value, '__dataclass_fields__'):
                        non_none_fields.append(f"  {field_name}: <nested dataclass>")
                    elif hasattr(field_value, 'start') and hasattr(field_value, 'end'):
                        # Time interval
                        non_none_fields.append(f"  {field_name}: {field_value.start} to {field_value.end}")
                    else:
                        str_val = str(field_value)[:50] + ("..." if len(str(field_value)) > 50 else "")
                        non_none_fields.append(f"  {field_name}: {str_val}")
            
            if self.compact and len(non_none_fields) > 8:
                non_none_fields = non_none_fields[:8] + [f"  ... ({len(non_none_fields)-8} more fields)"]
            
            result += "\n".join(non_none_fields)
            if not non_none_fields:
                result += "  <no data>"
        else:
            result += str(data)[:200] + ("..." if len(str(data)) > 200 else "")
        
        return result
    
    async def inspect_weather_source_data(self, weather_source) -> Dict[str, Any]:
        """Inspect weather source by calling get_data() and then examining its raw data structures."""
        print(self.format_header(f"Weather Source - {weather_source.label}"))
        
        source_data = {}
        
        print(f"ID: {weather_source.id}")
        print(f"Priority: {weather_source.priority}")
        print(f"Requires API Key: {weather_source.requires_api_key()}")
        print(f"Enabled: {weather_source.is_enabled}")
        
        # Get geographic location in sync context
        geographic_location = await sync_to_async(lambda: weather_source.geographic_location, thread_sensitive=True)()
        if not geographic_location:
            print("No geographic location configured")
            return source_data
        
        print(f"Geographic Location: {geographic_location.latitude:.3f}, {geographic_location.longitude:.3f}")
        
        try:
            # Call the standard get_data() method to populate WeatherManager structures
            print("\nCalling weather source get_data() to populate WeatherManager...")
            await weather_source.get_data()
            print("Weather source data fetch completed")
            source_data['fetch_completed'] = True
            
            # Now inspect the raw data that the weather source produces
            print("\nInspecting raw data structures from weather source:")
            await self.inspect_raw_weather_source_data(weather_source, geographic_location)
            
        except Exception as e:
            print(f"Error during weather source data fetch: {e}")
            source_data['fetch_error'] = str(e)
            import traceback
            traceback.print_exc()
        
        return source_data
    
    async def inspect_raw_weather_source_data(self, weather_source, geographic_location):
        """Inspect the raw data structures that a weather source produces."""
        
        # Try to get current conditions using the source's method if it exists
        try:
            if hasattr(weather_source, 'get_current_conditions'):
                current_data = await sync_to_async(weather_source.get_current_conditions, thread_sensitive=True)(geographic_location)
                if current_data:
                    print(self.format_weather_data_summary(current_data, "Current Conditions (Raw)"))
                else:
                    print(self.format_subheader("Current Conditions (Raw)"))
                    print("  No current conditions data available")
        except (NotImplementedError, AttributeError):
            print(self.format_subheader("Current Conditions (Raw)"))
            print("  Current conditions not available for this source")
        except Exception as e:
            print(f"  Error getting current conditions: {e}")
        
        # Try to get hourly forecast using the source's method if it exists
        try:
            if hasattr(weather_source, 'get_forecast_hourly'):
                hourly_forecast = await sync_to_async(weather_source.get_forecast_hourly, thread_sensitive=True)(geographic_location)
                if hourly_forecast:
                    print(self.format_subheader(f"Hourly Forecast (Raw - first {self.limit} of {len(hourly_forecast)})"))
                    # Show station and source time info once for the section
                    if hourly_forecast:
                        station_info = self.get_station_info(hourly_forecast[0])
                        source_time_info = self.get_source_time_info(hourly_forecast[0])
                        if station_info:
                            print(f"  {station_info}")
                        if source_time_info:
                            print(f"  {source_time_info}")
                    for i, interval_forecast in enumerate(hourly_forecast[:self.limit]):
                        # Handle IntervalWeatherForecast objects
                        if hasattr(interval_forecast, 'interval') and interval_forecast.interval:
                            start_local = self.convert_to_local_timezone(interval_forecast.interval.start)
                            end_local = self.convert_to_local_timezone(interval_forecast.interval.end)
                            interval = f"{start_local.strftime('%m/%d %H:%M')} - {end_local.strftime('%H:%M')}"
                        else:
                            interval = "No interval"
                        print(f"  [{i+1}] {interval}")
                        
                        # Get the actual forecast data
                        forecast = interval_forecast.data if hasattr(interval_forecast, 'data') else interval_forecast
                        key_fields = []
                        if forecast and forecast.temperature:
                            key_fields.append(f"Temp: {self.format_data_point(forecast.temperature, show_station=False, show_time=False)}")
                        if forecast and forecast.relative_humidity:
                            key_fields.append(f"Humidity: {self.format_data_point(forecast.relative_humidity, show_station=False, show_time=False)}")
                        if forecast and forecast.precipitation:
                            key_fields.append(f"Precip: {self.format_data_point(forecast.precipitation, show_station=False, show_time=False)}")
                        if forecast and forecast.windspeed:
                            key_fields.append(f"Wind: {self.format_data_point(forecast.windspeed, show_station=False, show_time=False)}")
                        print(f"      {', '.join(key_fields) if key_fields else 'No data'}")
                else:
                    print(self.format_subheader("Hourly Forecast (Raw)"))
                    print("  No hourly forecast data available")
        except (NotImplementedError, AttributeError):
            print(self.format_subheader("Hourly Forecast (Raw)"))
            print("  Hourly forecast not available for this source")
        except Exception as e:
            print(f"  Error getting hourly forecast: {e}")
        
        # Try to get daily forecast using the source's method if it exists
        try:
            if hasattr(weather_source, 'get_forecast_daily'):
                daily_forecast = await sync_to_async(weather_source.get_forecast_daily, thread_sensitive=True)(geographic_location)
                if daily_forecast:
                    print(self.format_subheader(f"Daily Forecast (Raw - first {self.limit} of {len(daily_forecast)})"))
                    # Show station and source time info once for the section
                    if daily_forecast:
                        station_info = self.get_station_info(daily_forecast[0])
                        source_time_info = self.get_source_time_info(daily_forecast[0])
                        if station_info:
                            print(f"  {station_info}")
                        if source_time_info:
                            print(f"  {source_time_info}")
                    for i, interval_forecast in enumerate(daily_forecast[:self.limit]):
                        # Handle IntervalWeatherForecast objects
                        if hasattr(interval_forecast, 'interval') and interval_forecast.interval:
                            start_local = self.convert_to_local_timezone(interval_forecast.interval.start)
                            date_str = start_local.strftime('%m/%d')
                        else:
                            date_str = "No date"
                        print(f"  [{i+1}] {date_str}")
                        
                        # Get the actual forecast data
                        forecast = interval_forecast.data if hasattr(interval_forecast, 'data') else interval_forecast
                        key_fields = []
                        if forecast and forecast.temperature:
                            key_fields.append(f"Temp: {self.format_data_point(forecast.temperature, show_station=False, show_time=False)}")
                        if forecast and forecast.precipitation:
                            key_fields.append(f"Precip: {self.format_data_point(forecast.precipitation, show_station=False, show_time=False)}")
                        if forecast and forecast.description_short:
                            key_fields.append(f"Desc: {self.format_data_point(forecast.description_short, show_station=False, show_time=False)}")
                        print(f"      {', '.join(key_fields) if key_fields else 'No data'}")
                else:
                    print(self.format_subheader("Daily Forecast (Raw)"))
                    print("  No daily forecast data available")
        except (NotImplementedError, AttributeError):
            print(self.format_subheader("Daily Forecast (Raw)"))
            print("  Daily forecast not available for this source")
        except Exception as e:
            print(f"  Error getting daily forecast: {e}")
            
        # For NWS specifically, also try to get the 12-hour forecast data that it uses to build daily forecasts
        if weather_source.id == 'nws':
            try:
                if hasattr(weather_source, 'get_forecast_12h'):
                    forecast_12h = await sync_to_async(weather_source.get_forecast_12h, thread_sensitive=True)(geographic_location)
                    if forecast_12h:
                        print(self.format_subheader(f"12-Hour Forecast (Raw NWS - first {self.limit} of {len(forecast_12h)})"))
                        print("  Note: NWS uses these 12-hour periods to construct daily forecasts")
                        # Show station and source time info once for the section
                        if forecast_12h:
                            station_info = self.get_station_info(forecast_12h[0])
                            source_time_info = self.get_source_time_info(forecast_12h[0])
                            if station_info:
                                print(f"  {station_info}")
                            if source_time_info:
                                print(f"  {source_time_info}")
                        for i, interval_forecast in enumerate(forecast_12h[:self.limit]):
                            # Handle IntervalWeatherForecast objects
                            if hasattr(interval_forecast, 'interval') and interval_forecast.interval:
                                start_local = self.convert_to_local_timezone(interval_forecast.interval.start)
                                end_local = self.convert_to_local_timezone(interval_forecast.interval.end)
                                interval = f"{start_local.strftime('%m/%d %H:%M')} - {end_local.strftime('%m/%d %H:%M')}"
                            else:
                                interval = "No interval"
                            print(f"  [{i+1}] {interval}")
                            
                            # Get the actual forecast data
                            forecast = interval_forecast.data if hasattr(interval_forecast, 'data') else interval_forecast
                            key_fields = []
                            if forecast and forecast.temperature:
                                key_fields.append(f"Temp: {self.format_data_point(forecast.temperature, show_station=False, show_time=False)}")
                            if forecast and forecast.precipitation:
                                key_fields.append(f"Precip: {self.format_data_point(forecast.precipitation, show_station=False, show_time=False)}")
                            if forecast and forecast.description_short:
                                key_fields.append(f"Desc: {self.format_data_point(forecast.description_short, show_station=False, show_time=False)}")
                            print(f"      {', '.join(key_fields) if key_fields else 'No data'}")
                    else:
                        print(self.format_subheader("12-Hour Forecast (Raw NWS)"))
                        print("  No 12-hour forecast data available")
            except (NotImplementedError, AttributeError):
                print(self.format_subheader("12-Hour Forecast (Raw NWS)"))
                print("  12-hour forecast not available")
            except Exception as e:
                print(f"  Error getting 12-hour forecast: {e}")
            
        # Try to get historical data if available
        try:
            if hasattr(weather_source, 'get_historical_weather'):
                historical_data = await sync_to_async(weather_source.get_historical_weather, thread_sensitive=True)(geographic_location, days_back=self.limit)
                if historical_data:
                    print(self.format_subheader(f"Historical Data (Raw - last {len(historical_data)} days)"))
                    # Show station and source time info once for the section
                    if historical_data:
                        station_info = self.get_station_info(historical_data[0])
                        source_time_info = self.get_source_time_info(historical_data[0])
                        if station_info:
                            print(f"  {station_info}")
                        if source_time_info:
                            print(f"  {source_time_info}")
                    for i, history in enumerate(historical_data[:self.limit]):
                        if hasattr(history, 'start') and history.start:
                            start_local = self.convert_to_local_timezone(history.start)
                            date_str = start_local.strftime('%m/%d')
                        else:
                            date_str = "No date"
                        print(f"  [{i+1}] {date_str}")
                        key_fields = []
                        if history.temperature:
                            key_fields.append(f"Temp: {self.format_data_point(history.temperature, show_station=False, show_time=False)}")
                        if history.precipitation:
                            key_fields.append(f"Precip: {self.format_data_point(history.precipitation, show_station=False, show_time=False)}")
                        print(f"      {', '.join(key_fields) if key_fields else 'No data'}")
                else:
                    print(self.format_subheader("Historical Data (Raw)"))
                    print("  No historical data available")
        except (NotImplementedError, AttributeError):
            print(self.format_subheader("Historical Data (Raw)"))
            print("  Historical data not available for this source")
        except Exception as e:
            print(f"  Error getting historical data: {e}")
    
    async def inspect_aggregated_data(self) -> Dict[str, Any]:
        """Inspect aggregated data from weather manager after sources have populated it."""
        print(self.format_header("Aggregated Weather Data from WeatherManager"))
        print("Note: This shows the final processed data after weather sources have populated WeatherManager")
        print("      (e.g., NWS 12-hour forecasts aggregated into daily data)\n")
        
        aggregated_data = {}
        
        try:
            # Current conditions
            current_conditions = await sync_to_async(self.weather_manager.get_current_conditions_data, thread_sensitive=True)()
            if current_conditions:
                aggregated_data['current_conditions'] = current_conditions
                print(self.format_weather_data_summary(current_conditions, "Current Conditions"))
            else:
                print(self.format_subheader("Current Conditions"))
                print("  No current conditions data available")
            
            # Hourly forecast - these are aggregated by WeatherManager from source data
            hourly_forecast = await sync_to_async(self.weather_manager.get_hourly_forecast, thread_sensitive=True)()
            if hourly_forecast and hourly_forecast.data_list:
                limited_hourly = hourly_forecast.data_list[:self.limit]
                aggregated_data['hourly_forecast'] = limited_hourly
                print(self.format_subheader(f"Hourly Forecast (first {self.limit} of {len(hourly_forecast.data_list)})"))
                
                # Show station and source time info once for the section if available
                if limited_hourly:
                    first_forecast = limited_hourly[0]
                    station_info = self.get_station_info(first_forecast)
                    source_time_info = self.get_source_time_info(first_forecast)
                    if station_info:
                        print(f"  {station_info}")
                    if source_time_info:
                        print(f"  {source_time_info}")
                
                for i, forecast in enumerate(limited_hourly):
                    print(f"  [{i+1}] Hourly forecast data")
                    
                    key_fields = []
                    if forecast.temperature:
                        key_fields.append(f"Temp: {self.format_data_point(forecast.temperature, show_station=False, show_time=False)}")
                    if forecast.relative_humidity:
                        key_fields.append(f"Humidity: {self.format_data_point(forecast.relative_humidity, show_station=False, show_time=False)}")
                    if forecast.precipitation_probability:
                        key_fields.append(f"Precip%: {self.format_data_point(forecast.precipitation_probability, show_station=False, show_time=False)}")
                    if forecast.precipitation:
                        key_fields.append(f"Precip: {self.format_data_point(forecast.precipitation, show_station=False, show_time=False)}")
                    if forecast.windspeed:
                        key_fields.append(f"Wind: {self.format_data_point(forecast.windspeed, show_station=False, show_time=False)}")
                    print(f"      {', '.join(key_fields) if key_fields else 'No key data'}")
            else:
                print(self.format_subheader("Hourly Forecast"))
                print("  No hourly forecast data available")
            
            # Daily forecast - these are aggregated by WeatherManager (e.g., NWS 12-hour -> daily)
            daily_forecast = await sync_to_async(self.weather_manager.get_daily_forecast, thread_sensitive=True)()
            if daily_forecast and daily_forecast.data_list:
                limited_daily = daily_forecast.data_list[:self.limit]
                aggregated_data['daily_forecast'] = limited_daily
                print(self.format_subheader(f"Daily Forecast (first {self.limit} of {len(daily_forecast.data_list)})"))
                
                # Show station and source time info once for the section if available
                if limited_daily:
                    first_forecast = limited_daily[0]
                    station_info = self.get_station_info(first_forecast)
                    source_time_info = self.get_source_time_info(first_forecast)
                    if station_info:
                        print(f"  {station_info}")
                    if source_time_info:
                        print(f"  {source_time_info}")
                
                for i, forecast in enumerate(limited_daily):
                    print(f"  [{i+1}] Daily forecast data")
                    
                    key_fields = []
                    if forecast.temperature:
                        key_fields.append(f"Temp: {self.format_data_point(forecast.temperature, show_station=False, show_time=False)}")
                    if forecast.precipitation_probability:
                        key_fields.append(f"Precip%: {self.format_data_point(forecast.precipitation_probability, show_station=False, show_time=False)}")
                    if forecast.precipitation:
                        key_fields.append(f"Precip: {self.format_data_point(forecast.precipitation, show_station=False, show_time=False)}")
                    if forecast.description_short:
                        key_fields.append(f"Desc: {self.format_data_point(forecast.description_short, show_station=False, show_time=False)}")
                    print(f"      {', '.join(key_fields) if key_fields else 'No key data'}")
            else:
                print(self.format_subheader("Daily Forecast"))
                print("  No daily forecast data available")
            
            # Daily history
            daily_history = await sync_to_async(self.weather_manager.get_daily_history, thread_sensitive=True)()
            if daily_history and daily_history.data_list:
                limited_history = daily_history.data_list[:self.limit]
                aggregated_data['daily_history'] = limited_history
                print(self.format_subheader(f"Daily History (last {self.limit} of {len(daily_history.data_list)})"))
                
                # Show station and source time info once for the section if available  
                if limited_history:
                    first_history = limited_history[0]
                    station_info = self.get_station_info(first_history)
                    source_time_info = self.get_source_time_info(first_history)
                    if station_info:
                        print(f"  {station_info}")
                    if source_time_info:
                        print(f"  {source_time_info}")
                
                for i, history in enumerate(limited_history):
                    # Show date if available
                    if hasattr(history, 'start') and history.start:
                        start_local = self.convert_to_local_timezone(history.start)
                        date_str = start_local.strftime('%m/%d')
                        print(f"  [{i+1}] {date_str}")
                    else:
                        print(f"  [{i+1}] Historical data")
                    
                    key_fields = []
                    if history.temperature:
                        key_fields.append(f"Temp: {self.format_data_point(history.temperature, show_station=False, show_time=False)}")
                    if history.precipitation:
                        key_fields.append(f"Precip: {self.format_data_point(history.precipitation, show_station=False, show_time=False)}")
                    if history.description_short:
                        key_fields.append(f"Desc: {self.format_data_point(history.description_short, show_station=False, show_time=False)}")
                    print(f"      {', '.join(key_fields) if key_fields else 'No key data'}")
            else:
                print(self.format_subheader("Daily History"))
                print("  No daily history data available")
                    
        except Exception as e:
            print(f"Error getting aggregated data: {e}")
            import traceback
            traceback.print_exc()
        
        return aggregated_data
    
    async def run_inspection( self,
                              source_filter    : str = 'all', 
                              data_type_filter : str = 'all',
                              raw_only         : bool = False,
                              parsed_only      : bool = False, 
                              aggregated_only  : bool = False):
        """Run the complete inspection."""
        
        print(f"Weather Data Inspector - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Inspecting: {source_filter} sources, {data_type_filter} data types")
        print(f"Output mode: {'Compact' if self.compact else 'Detailed'}, Limit: {self.limit}")

        # Initialize Django components in sync context
        await self._initialize_components()
        
        # Get weather sources
        weather_sources = self.weather_sources
        
        if source_filter != 'all':
            weather_sources = [ws for ws in weather_sources if ws.id == source_filter]
        
        if not weather_sources:
            print(f"No weather sources found matching filter: {source_filter}")
            return
        
        print(f"Found {len(weather_sources)} weather source(s)")
        
        # Always call get_data() to populate WeatherManager, but only show raw data if requested
        for weather_source in weather_sources:
            if not aggregated_only:
                # Show both raw data and call get_data()
                _ = await self.inspect_weather_source_data(weather_source)
            else:
                # Only call get_data() without showing raw data
                print(f"Calling {weather_source.label} get_data() to populate WeatherManager...")
                try:
                    await weather_source.get_data()
                    print("Completed")
                except Exception as e:
                    print(f"Error: {e}")
        
        # Inspect aggregated data from weather manager (the main output)
        if not raw_only and not parsed_only:
            _ = await self.inspect_aggregated_data()
        
        print( self.format_header("Inspection Complete") )
        print( "Tip: Use --compact for shorter output, --limit N to control record count" )
        print( "     Use --source <name> to focus on specific weather source" )


def main():
    parser = argparse.ArgumentParser(description='Inspect weather data flow from sources to aggregated data')
    parser.add_argument('--source', default='all', 
                        help='Weather source to inspect (openmeteo, nws, all)')
    parser.add_argument('--data-type', default='all',
                        help='Data type to inspect (current, hourly, daily, history, all)')
    parser.add_argument('--compact', action='store_true',
                        help='Use compact output format')
    parser.add_argument('--raw-only', action='store_true',
                        help='Show only weather source data')
    parser.add_argument('--parsed-only', action='store_true', 
                        help='Show only parsed data structures (same as raw-only)')
    parser.add_argument('--aggregated-only', action='store_true',
                        help='Show only aggregated data from weather manager')
    parser.add_argument('--limit', type=int, default=5,
                        help='Limit number of records shown (default: 5)')
    
    args = parser.parse_args()
    inspector = WeatherDataInspector(compact=args.compact, limit=args.limit)
    
    try:
        asyncio.run(inspector.run_inspection(
            source_filter=args.source,
            data_type_filter=args.data_type,
            raw_only=args.raw_only,
            parsed_only=args.parsed_only,
            aggregated_only=args.aggregated_only
        ))
    except KeyboardInterrupt:
        print("\nInspection interrupted by user")
    except Exception as e:
        print(f"\nError during inspection: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
