from datetime import datetime, timedelta, time
import random
from typing import List

import hi.apps.common.datetimeproxy as datetimeproxy
from hi.apps.weather.enums import (
    WeatherPhenomenon,
    WeatherPhenomenonIntensity,
    WeatherPhenomenonModifier,
    WeatherEventType,
    AlertStatus,
    AlertCategory,
    AlertSeverity,
    AlertCertainty,
    AlertUrgency,
)
from hi.apps.weather.transient_models import (
    BooleanDataPoint,
    CommonWeatherData,
    AstronomicalData,
    DataPointSource,
    DataPointList,
    NotablePhenomenon,
    NumericDataPoint,
    StringDataPoint,
    TimeDataPoint,
    TimeInterval,
    WeatherConditionsData,
    WeatherForecastData,
    WeatherHistoryData,
    WeatherOverviewData,
    IntervalWeatherForecast,
    IntervalWeatherHistory,
    Station,
    WeatherAlert,
)
from hi.units import UnitQuantity


class WeatherSyntheticData:

    @classmethod
    def _create_test_station(cls, source: DataPointSource) -> Station:
        """Create a standardized test station to reduce duplication"""
        return Station(
            source=source,
            station_id='test',
            name='Testing',
            geo_location=None,
            station_url=None,
            observations_url=None,
            forecast_url=None,
        )

    @classmethod
    def _create_default_source(cls) -> DataPointSource:
        """Create a default test data source"""
        return DataPointSource(
            id='test',
            label='Test',
            abbreviation='TEST',
            priority=1,
        )

    @classmethod
    def get_random_weather_overview_data(cls,
                                         now: datetime = None,
                                         source: DataPointSource = None) -> WeatherOverviewData:
        if not now:
            now = datetimeproxy.now()
        if not source:
            source = cls._create_default_source()
        
        return WeatherOverviewData(
            current_conditions_data=cls.get_random_weather_conditions_data(now=now, source=source),
            todays_astronomical_data=cls.get_random_daily_astronomical_data(now=now, source=source),
        )
    
    @classmethod
    def get_random_weather_conditions_data(cls,
                                           now: datetime = None,
                                           source: DataPointSource = None) -> WeatherConditionsData:
        if not now:
            now = datetimeproxy.now()
        if not source:
            source = cls._create_default_source()
        
        station = cls._create_test_station(source)
            
        weather_conditions_data = WeatherConditionsData(
            temperature=NumericDataPoint(
                station=station,
                source_datetime=now,
                quantity_ave=UnitQuantity(random.randint(-5, 115), 'degF'),
            ),
            temperature_min_last_24h=NumericDataPoint(
                station=station,
                source_datetime=now,
                quantity_ave=UnitQuantity(random.randint(-5, 90), 'degF'),
            ),
            temperature_max_last_24h=NumericDataPoint(
                station=station,
                source_datetime=now,
                quantity_ave=UnitQuantity(random.randint(40, 115), 'degF'),
            ),
            temperature_min_today=NumericDataPoint(
                station=station,
                source_datetime=now,
                quantity_ave=UnitQuantity(random.randint(-5, 90), 'degF'),
            ),
            temperature_max_today=NumericDataPoint(
                station=station,
                source_datetime=now,
                quantity_ave=UnitQuantity(random.randint(40, 115), 'degF'),
            ),
            precipitation_last_hour=NumericDataPoint(
                station=station,
                source_datetime=now,
                quantity_ave=UnitQuantity(1.0 * random.random(), 'inches'),
            ),
            precipitation_last_3h=NumericDataPoint(
                station=station,
                source_datetime=now,
                quantity_ave=UnitQuantity(2.0 * random.random(), 'inches'),
            ),
            precipitation_last_6h=NumericDataPoint(
                station=station,
                source_datetime=now,
                quantity_ave=UnitQuantity(3.0 * random.random(), 'inches'),
            ),
            precipitation_last_24h=NumericDataPoint(
                station=station,
                source_datetime=now,
                quantity_ave=UnitQuantity(4.0 * random.random(), 'inches'),
            ),
        )
        cls.set_random_notable_phenomenon(
            weather_conditions_data=weather_conditions_data,
            now=now,
            source=source,
        )
        cls.set_random_common_weather_data(
            data_obj=weather_conditions_data,
            now=now,
            source=source,
        )
        return weather_conditions_data

    @classmethod
    def get_random_daily_astronomical_data(cls,
                                           now: datetime = None,
                                           source: DataPointSource = None) -> AstronomicalData:
        if not now:
            now = datetimeproxy.now()
        if not source:
            source = cls._create_default_source()
        
        station = cls._create_test_station(source)
        
        # Create realistic astronomical times
        base_sunrise_hour = 6 + random.randint(-2, 2)  # 4-8 AM
        base_sunset_hour = 18 + random.randint(-2, 2)  # 4-8 PM
        
        sunrise_time = time(
            hour=base_sunrise_hour,
            minute=random.randint(0, 59),
            second=random.randint(0, 59)
        )
        sunset_time = time(
            hour=base_sunset_hour,
            minute=random.randint(0, 59),
            second=random.randint(0, 59)
        )
        solar_noon_time = time(
            hour=12,
            minute=random.randint(0, 59),
            second=random.randint(0, 59)
        )
        
        return AstronomicalData(
            sunrise=TimeDataPoint(
                station=station,
                source_datetime=now,
                value=sunrise_time,
            ),
            sunset=TimeDataPoint(
                station=station,
                source_datetime=now,
                value=sunset_time,
            ),
            solar_noon=TimeDataPoint(
                station=station,
                source_datetime=now,
                value=solar_noon_time,
            ),
            moonrise=TimeDataPoint(
                station=station,
                source_datetime=now,
                value=time(
                    hour=random.randint(18, 23),
                    minute=random.randint(0, 59),
                    second=random.randint(0, 59)
                ),
            ),
            moonset=TimeDataPoint(
                station=station,
                source_datetime=now,
                value=time(
                    hour=random.randint(5, 10),
                    minute=random.randint(0, 59),
                    second=random.randint(0, 59)
                ),
            ),
            moon_illumnination=NumericDataPoint(
                station=station,
                source_datetime=now,
                quantity_ave=UnitQuantity(random.randint(0, 100), 'percent'),
            ),
            moon_is_waxing=BooleanDataPoint(
                station=station,
                source_datetime=now,
                value=bool(random.random() < 0.5),
            ),
            civil_twilight_begin=TimeDataPoint(
                station=station,
                source_datetime=now,
                value=time(
                    hour=max(0, base_sunrise_hour - 1),
                    minute=random.randint(0, 59),
                    second=random.randint(0, 59)
                ),
            ),
            civil_twilight_end=TimeDataPoint(
                station=station,
                source_datetime=now,
                value=time(
                    hour=min(23, base_sunset_hour + 1),
                    minute=random.randint(0, 59),
                    second=random.randint(0, 59)
                ),
            ),
            nautical_twilight_begin=TimeDataPoint(
                station=station,
                source_datetime=now,
                value=time(
                    hour=max(0, base_sunrise_hour - 2),
                    minute=random.randint(0, 59),
                    second=random.randint(0, 59)
                ),
            ),
            nautical_twilight_end=TimeDataPoint(
                station=station,
                source_datetime=now,
                value=time(
                    hour=min(23, base_sunset_hour + 2),
                    minute=random.randint(0, 59),
                    second=random.randint(0, 59)
                ),
            ),
            astronomical_twilight_begin=TimeDataPoint(
                station=station,
                source_datetime=now,
                value=time(
                    hour=max(0, base_sunrise_hour - 3),
                    minute=random.randint(0, 59),
                    second=random.randint(0, 59)
                ),
            ),
            astronomical_twilight_end=TimeDataPoint(
                station=station,
                source_datetime=now,
                value=time(
                    hour=min(23, base_sunset_hour + 3),
                    minute=random.randint(0, 59),
                    second=random.randint(0, 59)
                ),
            ),
        )

    @classmethod
    def get_random_interval_hourly_forecast_list(cls,
                                             now: datetime = None,
                                             source: DataPointSource = None) -> List[IntervalWeatherForecast]:
        if not now:
            now = datetimeproxy.now()
        if not source:
            source = cls._create_default_source()
        
        interval_hourly_forecast_list = list()
        for hour_idx in range(24):
            interval_start = now.replace(minute=0, second=0, microsecond=0)
            interval_start += timedelta(hours=hour_idx + 1)
            interval_end = interval_start + timedelta(hours=1)
            
            # Create the interval
            time_interval = TimeInterval(
                start=interval_start,
                end=interval_end
            )
            
            # Create the forecast data
            forecast_data = cls.get_random_forecast_data( 
                interval_start=interval_start,
                interval_end=interval_end,
                now=now,
                source=source,
            )
            
            # Create the interval forecast
            interval_forecast = IntervalWeatherForecast(
                interval=time_interval,
                data=forecast_data
            )
            
            interval_hourly_forecast_list.append(interval_forecast)
            continue
        return interval_hourly_forecast_list
    
    @classmethod
    def get_random_interval_daily_forecast_list(cls,
                                            now: datetime = None,
                                            source: DataPointSource = None) -> List[IntervalWeatherForecast]:
        if not now:
            now = datetimeproxy.now()
        if not source:
            source = cls._create_default_source()
        
        interval_daily_forecast_list = list()
        for day_idx in range(10):
            interval_start = now.replace(hour=0, minute=0, second=0, microsecond=1)
            interval_start += timedelta(hours=24 * day_idx)
            interval_end = interval_start + timedelta(hours=24)
            
            # Create the interval
            time_interval = TimeInterval(
                start=interval_start,
                end=interval_end
            )
            
            # Create the forecast data
            forecast_data = cls.get_random_forecast_data( 
                interval_start=interval_start,
                interval_end=interval_end,
                now=now,
                source=source,
            )
            
            # Create the interval forecast
            interval_forecast = IntervalWeatherForecast(
                interval=time_interval,
                data=forecast_data
            )
            
            interval_daily_forecast_list.append(interval_forecast)
            continue
        return interval_daily_forecast_list

    @classmethod
    def get_random_hourly_interval_forecast_data_list(cls,
                                                      now: datetime = None,
                                                      source: DataPointSource = None) -> List[IntervalWeatherForecast]:
        """Get random hourly forecast data wrapped in IntervalWeatherForecast objects."""
        if not now:
            now = datetimeproxy.now()
        if not source:
            source = cls._create_default_source()
        
        interval_forecast_data_list = list()
        
        for hour_idx in range(24):
            interval_start = now.replace(minute=0, second=0, microsecond=0)
            interval_start += timedelta(hours=hour_idx + 1)
            interval_end = interval_start + timedelta(hours=1)
            
            # Create time interval
            time_interval = TimeInterval(
                start=interval_start,
                end=interval_end
            )
            
            # Create forecast data
            forecast_data = cls.get_random_forecast_data(
                interval_start=interval_start,
                interval_end=interval_end,
                now=now,
                source=source,
            )
            
            # Create interval weather forecast
            interval_weather_forecast = IntervalWeatherForecast(
                interval=time_interval,
                data=forecast_data
            )
            interval_forecast_data_list.append(interval_weather_forecast)
            continue
        return interval_forecast_data_list
    
    @classmethod
    def get_random_daily_interval_forecast_data_list(cls,
                                                     now: datetime = None,
                                                     source: DataPointSource = None) -> List[IntervalWeatherForecast]:
        """Get random daily forecast data wrapped in IntervalWeatherForecast objects."""
        if not now:
            now = datetimeproxy.now()
        if not source:
            source = cls._create_default_source()
        
        interval_forecast_data_list = list()
        
        for day_idx in range(10):
            interval_start = now.replace(hour=0, minute=0, second=0, microsecond=1)
            interval_start += timedelta(hours=24 * day_idx)
            interval_end = interval_start + timedelta(hours=24)
            
            # Create time interval
            time_interval = TimeInterval(
                start=interval_start,
                end=interval_end
            )
            
            # Create forecast data
            forecast_data = cls.get_random_forecast_data(
                interval_start=interval_start,
                interval_end=interval_end,
                now=now,
                source=source,
            )
            
            # Create interval weather forecast
            interval_weather_forecast = IntervalWeatherForecast(
                interval=time_interval,
                data=forecast_data
            )
            interval_forecast_data_list.append(interval_weather_forecast)
            continue
        return interval_forecast_data_list

    @classmethod
    def get_random_daily_interval_history_data_list(cls,
                                                    now: datetime = None,
                                                    source: DataPointSource = None) -> List[IntervalWeatherHistory]:
        """Get random daily history data wrapped in IntervalWeatherHistory objects."""
        if not now:
            now = datetimeproxy.now()
        if not source:
            source = cls._create_default_source()
        
        interval_history_data_list = list()
        
        for day_idx in range(10):
            interval_start = now.replace(hour=0, minute=0, second=0, microsecond=1)
            interval_start -= timedelta(hours=24 * (day_idx + 1))
            interval_end = interval_start + timedelta(hours=24)
            
            # Create time interval
            time_interval = TimeInterval(
                start=interval_start,
                end=interval_end
            )
            
            # Create history data
            history_data = cls.get_random_history_data(
                interval_start=interval_start,
                interval_end=interval_end,
                now=now,
                source=source,
            )
            
            # Create interval weather history
            interval_weather_history = IntervalWeatherHistory(
                interval=time_interval,
                data=history_data
            )
            interval_history_data_list.append(interval_weather_history)
            continue
        return interval_history_data_list

    @classmethod
    def get_random_forecast_data(cls,
                                 interval_start: datetime,
                                 interval_end: datetime,
                                 now: datetime = None,
                                 source: DataPointSource = None) -> WeatherForecastData:
        if not now:
            now = datetimeproxy.now()
        if not source:
            source = cls._create_default_source()
        
        # Create empty forecast data, then populate it
        forecast_data = WeatherForecastData()
        cls.set_random_weather_forecast_data(
            data_obj=forecast_data,
            now=now,
            source=source,
        )
        return forecast_data

    @classmethod
    def get_random_interval_daily_history_list(cls,
                                           now: datetime = None,
                                           source: DataPointSource = None) -> List[IntervalWeatherHistory]:
        if not now:
            now = datetimeproxy.now()
        if not source:
            source = cls._create_default_source()
        
        interval_daily_history_list = list()
        for day_idx in range(10):
            interval_start = now.replace(hour=0, minute=0, second=0, microsecond=1)
            interval_start -= timedelta(hours=24 * (day_idx + 1))
            interval_end = interval_start + timedelta(hours=24)
            
            # Create the interval
            time_interval = TimeInterval(
                start=interval_start,
                end=interval_end
            )
            
            # Create the history data
            history_data = cls.get_random_history_data( 
                interval_start=interval_start,
                interval_end=interval_end,
                now=now,
                source=source,
            )
            
            # Create the interval history
            interval_history = IntervalWeatherHistory(
                interval=time_interval,
                data=history_data
            )
            
            interval_daily_history_list.append(interval_history)
            continue
        return interval_daily_history_list
    
    @classmethod
    def get_random_history_data(cls,
                                interval_start: datetime,
                                interval_end: datetime,
                                now: datetime = None,
                                source: DataPointSource = None) -> WeatherHistoryData:
        if not now:
            now = datetimeproxy.now()
        if not source:
            source = cls._create_default_source()
        
        # Create empty history data, then populate it
        history_data = WeatherHistoryData()
        cls.set_random_weather_history_data(
            data_obj=history_data,
            now=now,
            source=source,
        )
        return history_data

    @classmethod
    def set_random_common_weather_data(cls,
                                       data_obj: CommonWeatherData,
                                       now: datetime = None,
                                       source: DataPointSource = None):
        if not now:
            now = datetimeproxy.now()
        if not source:
            source = cls._create_default_source()
        
        station = cls._create_test_station(source)
        
        # Generate realistic temperature ranges (min <= ave <= max)
        temp_min = random.randint(-5, 85)
        temp_max = random.randint(temp_min + 5, 115)
        temp_ave = random.randint(temp_min, temp_max)
        
        data_obj.temperature = NumericDataPoint(
            station=station,
            source_datetime=now,
            quantity_min=UnitQuantity(temp_min, 'degF'),
            quantity_ave=UnitQuantity(temp_ave, 'degF'),
            quantity_max=UnitQuantity(temp_max, 'degF'),
        )
        
        data_obj.precipitation = NumericDataPoint(
            station=station,
            source_datetime=now,
            quantity_ave=UnitQuantity(4.0 * random.random(), 'inches'),
        )
        
        # Generate realistic wind speed ranges (min <= ave <= max)
        wind_min = random.randint(0, 15)
        wind_max = random.randint(wind_min + 5, 80)
        wind_ave = random.randint(wind_min, wind_max)
        
        data_obj.windspeed = NumericDataPoint(
            station=station,
            source_datetime=now,
            quantity_min=UnitQuantity(wind_min, 'mph'),
            quantity_ave=UnitQuantity(wind_ave, 'mph'),
            quantity_max=UnitQuantity(wind_max, 'mph'),
        )
        
        data_obj.wind_direction = NumericDataPoint(
            station=station,
            source_datetime=now,
            quantity_ave=UnitQuantity(random.randint(0, 359), 'deg'),
        )
        
        data_obj.cloud_cover = NumericDataPoint(
            station=station,
            source_datetime=now,
            quantity_ave=UnitQuantity(random.randint(0, 100), 'percent'),
        )
        
        data_obj.cloud_ceiling = NumericDataPoint(
            station=station,
            source_datetime=now,
            quantity_ave=UnitQuantity(random.randint(300, 5000), 'm'),
        )
        
        data_obj.relative_humidity = NumericDataPoint(
            station=station,
            source_datetime=now,
            quantity_ave=UnitQuantity(random.randint(0, 100), 'percent'),
        )
        
        data_obj.dew_point = NumericDataPoint(
            station=station,
            source_datetime=now,
            quantity_ave=UnitQuantity(random.randint(0, 100), 'degF'),
        )
        
        # Fix pressure units - use hPa with realistic range
        data_obj.barometric_pressure = NumericDataPoint(
            station=station,
            source_datetime=now,
            quantity_ave=UnitQuantity(random.randint(980, 1050), 'hPa'),
        )
        
        data_obj.sea_level_pressure = NumericDataPoint(
            station=station,
            source_datetime=now,
            quantity_ave=UnitQuantity(random.randint(980, 1050), 'hPa'),
        )
        
        data_obj.heat_index = NumericDataPoint(
            station=station,
            source_datetime=now,
            quantity_ave=UnitQuantity(random.randint(temp_ave, 120), 'degF'),
        )
        
        data_obj.wind_chill = NumericDataPoint(
            station=station,
            source_datetime=now,
            quantity_ave=UnitQuantity(random.randint(-20, temp_ave), 'degF'),
        )
        
        data_obj.visibility = NumericDataPoint(
            station=station,
            source_datetime=now,
            quantity_ave=UnitQuantity(random.randint(0, 10), 'miles'),
        )
        
        data_obj.description_short = StringDataPoint(
            station=station,
            source_datetime=now,
            value='A lot of weather today.',
        )
        
        data_obj.description_long = StringDataPoint(
            station=station,
            source_datetime=now,
            value='A lot of weather today blah blah blah blah blah blah blah blah blah blah blah blah.',
        )
        
        # Add missing is_daytime field
        data_obj.is_daytime = BooleanDataPoint(
            station=station,
            source_datetime=now,
            value=6 <= now.hour <= 18,  # Simple day/night logic
        )
        
        return

    @classmethod
    def set_random_weather_forecast_data(cls,
                                         data_obj: CommonWeatherData,
                                         now: datetime = None,
                                         source: DataPointSource = None):
        if not now:
            now = datetimeproxy.now()
        if not source:
            source = cls._create_default_source()
        
        station = cls._create_test_station(source)
        
        data_obj.precipitation_probability = NumericDataPoint(
            station=station,
            source_datetime=now,
            quantity_ave=UnitQuantity(random.random(), 'probability'),
        )
        cls.set_random_common_weather_data(
            data_obj=data_obj,
            now=now,
            source=source,
        )
        return

    @classmethod
    def set_random_weather_history_data(cls,
                                        data_obj: CommonWeatherData,
                                        now: datetime = None,
                                        source: DataPointSource = None):
        # Add if/when weather history has more than just the common weather fields.
        cls.set_random_common_weather_data(
            data_obj=data_obj,
            now=now,
            source=source,
        )
        return

    @classmethod
    def set_random_notable_phenomenon(cls,
                                      weather_conditions_data: WeatherConditionsData,
                                      now: datetime = None,
                                      source: DataPointSource = None):
        if not now:
            now = datetimeproxy.now()
        if not source:
            source = cls._create_default_source()
        
        station = cls._create_test_station(source)
        
        notable_phenomenon_list = list()
        for idx in range(random.randint(0, 2)):
            notable_phenomenon = NotablePhenomenon(
                weather_phenomenon=random.choice(list(WeatherPhenomenon)),
                weather_phenomenon_modifier=random.choice(list(WeatherPhenomenonModifier)),
                weather_phenomenon_intensity=random.choice(list(WeatherPhenomenonIntensity)),
                in_vicinity=bool(random.random() < 0.5),
            )
            notable_phenomenon_list.append(notable_phenomenon)
            continue
        
        weather_conditions_data.notable_phenomenon_data = DataPointList(
            station=station,
            source_datetime=now,
            list_value=notable_phenomenon_list,
        )
        return
    
    @classmethod
    def get_random_weather_alerts(cls, 
                                 count: int = None,
                                 now: datetime = None,
                                 source: DataPointSource = None) -> List[WeatherAlert]:
        """
        Generate a list of random WeatherAlert instances for UI testing.
        
        Args:
            count: Number of alerts to generate (default: random 0-5)
            now: Base datetime for alerts (default: current time)
            source: Data source (unused but kept for consistency)
            
        Returns:
            List of randomly generated WeatherAlert instances
        """
        if count is None:
            count = random.randint(0, 3)  # 0 to 3 random alerts
        if not now:
            now = datetimeproxy.now()
        
        alerts = []
        
        # Define realistic event types with their common descriptions
        event_scenarios = [
            # Critical weather events
            (WeatherEventType.TORNADO, "Tornado Warning", "Tornado Warning issued"),
            (WeatherEventType.FLASH_FLOOD, "Flash Flood Warning", "Flash Flood Warning issued"),
            (WeatherEventType.SEVERE_THUNDERSTORM, "Severe Thunderstorm Warning", "Severe Thunderstorm Warning issued"),
            (WeatherEventType.HURRICANE, "Hurricane Warning", "Hurricane Warning issued"),
            (WeatherEventType.BLIZZARD, "Blizzard Warning", "Blizzard Warning issued"),
            (WeatherEventType.WINTER_STORM, "Winter Storm Warning", "Winter Storm Warning issued"),
            (WeatherEventType.ICE_STORM, "Ice Storm Warning", "Ice Storm Warning issued"),
            
            # Watches and advisories
            (WeatherEventType.SEVERE_THUNDERSTORM, "Severe Thunderstorm Watch", "Severe Thunderstorm Watch issued"),
            (WeatherEventType.TORNADO, "Tornado Watch", "Tornado Watch issued"),
            (WeatherEventType.FLOOD, "Flood Advisory", "Flood Advisory issued"),
            (WeatherEventType.EXTREME_HEAT, "Excessive Heat Warning", "Excessive Heat Warning issued"),
            (WeatherEventType.EXTREME_COLD, "Wind Chill Warning", "Wind Chill Warning issued"),
            (WeatherEventType.WINTER_STORM, "Winter Weather Advisory", "Winter Weather Advisory issued"),
            (WeatherEventType.COASTAL_FLOOD, "Coastal Flood Advisory", "Coastal Flood Advisory issued"),
            
            # Marine weather
            (WeatherEventType.MARINE_WEATHER, "Small Craft Advisory", "Small Craft Advisory issued"),
            (WeatherEventType.GALE, "Gale Warning", "Gale Warning issued for marine areas"),
            (WeatherEventType.HIGH_SURF, "High Surf Advisory", "High Surf Advisory issued"),
            
            # Fire weather
            (WeatherEventType.RED_FLAG_CONDITIONS, "Red Flag Warning", "Red Flag Warning issued"),
            (WeatherEventType.WILDFIRE, "Fire Weather Watch", "Fire Weather Watch issued"),
            
            # Special conditions  
            (WeatherEventType.DUST_STORM, "Dust Storm Warning", "Dust Storm Warning issued"),
            (WeatherEventType.SPECIAL_WEATHER, "Dense Fog Advisory", "Dense Fog Advisory issued"),
            (WeatherEventType.AIR_QUALITY, "Air Quality Alert", "Air Quality Alert issued"),
            (WeatherEventType.AVALANCHE, "Avalanche Warning", "Avalanche Warning issued"),
            
            # Test/special messages
            (WeatherEventType.SPECIAL_WEATHER, "Special Weather Statement", "Special Weather Statement issued"),
            (WeatherEventType.TEST_MESSAGE, "Test Message", "This is a test message"),
        ]
        
        for i in range(count):
            # Pick a random event scenario
            event_type, event_name, headline_base = random.choice(event_scenarios)
            
            # Generate time windows (effective -> expires)
            effective_offset_hours = random.randint(-2, 24)  # Can be past, current, or future
            duration_hours = random.randint(1, 72)  # 1 to 72 hours duration
            
            effective_time = now + timedelta(hours=effective_offset_hours)
            expires_time = effective_time + timedelta(hours=duration_hours)
            onset_time = effective_time + timedelta(minutes=random.randint(0, 60))
            ends_time = expires_time + timedelta(minutes=random.randint(-30, 30))
            
            # Generate geographic areas (realistic county/region names)
            areas_options = [
                "Travis County", "Williamson County", "Hays County",
                "Harris County", "Dallas County", "Tarrant County", 
                "Bexar County", "Collin County", "Denton County",
                "Fort Bend County", "Montgomery County", "Brazoria County",
                "Central Texas", "East Texas", "North Texas", "South Texas",
                "Austin Metro Area", "Dallas-Fort Worth Metroplex", "Houston Metro Area",
                "Hill Country", "Coastal Plains", "Piney Woods Region"
            ]
            affected_areas = random.choice(areas_options)
            
            # Generate severity based on event type (some events tend to be more severe)
            if event_type in [WeatherEventType.TORNADO, WeatherEventType.HURRICANE, 
                             WeatherEventType.FLASH_FLOOD, WeatherEventType.EARTHQUAKE]:
                # Critical events tend to be severe/extreme
                severity_weights = [(AlertSeverity.EXTREME, 0.4), (AlertSeverity.SEVERE, 0.4), 
                                  (AlertSeverity.MODERATE, 0.15), (AlertSeverity.MINOR, 0.05)]
            elif "Warning" in event_name:
                # Warnings tend to be more severe than watches/advisories
                severity_weights = [(AlertSeverity.SEVERE, 0.5), (AlertSeverity.MODERATE, 0.3),
                                  (AlertSeverity.EXTREME, 0.15), (AlertSeverity.MINOR, 0.05)]
            elif "Watch" in event_name or "Advisory" in event_name:
                # Watches and advisories tend to be less severe
                severity_weights = [(AlertSeverity.MODERATE, 0.5), (AlertSeverity.MINOR, 0.3),
                                  (AlertSeverity.SEVERE, 0.15), (AlertSeverity.EXTREME, 0.05)]
            else:
                # Default distribution
                severity_weights = [(AlertSeverity.MODERATE, 0.4), (AlertSeverity.MINOR, 0.3),
                                  (AlertSeverity.SEVERE, 0.2), (AlertSeverity.EXTREME, 0.1)]
            
            # Weighted random selection
            severity = random.choices(
                [s for s, w in severity_weights], 
                weights=[w for s, w in severity_weights]
            )[0]
            
            # Generate realistic headlines with timing
            time_phrases = [
                f"until {expires_time.strftime('%I:%M %p')} {expires_time.strftime('%Z')}",
                f"from {effective_time.strftime('%I:%M %p')} to {expires_time.strftime('%I:%M %p')} {expires_time.strftime('%Z')}",
                f"in effect until {expires_time.strftime('%A %I:%M %p')}",
                f"issued {effective_time.strftime('%B %d at %I:%M %p')} {effective_time.strftime('%Z')}",
            ]
            headline = f"{headline_base} {random.choice(time_phrases)}"
            
            # Generate descriptions based on event type
            description_templates = {
                WeatherEventType.TORNADO: "At {time}, a severe thunderstorm capable of producing a tornado was located {location}. This dangerous storm was moving {direction} at {speed} mph. Damaging winds and large hail are also possible.",
                WeatherEventType.SEVERE_THUNDERSTORM: "At {time}, severe thunderstorms were located {location}, moving {direction} at {speed} mph. Hazards include {hazards}.",
                WeatherEventType.FLASH_FLOOD: "Heavy rainfall has caused flash flooding across {location}. Water levels are rising rapidly in low-lying areas and near creeks and streams.",
                WeatherEventType.EXTREME_HEAT: "Dangerously hot temperatures are expected with heat index values reaching {temp}°F. The combination of hot temperatures and high humidity will create dangerous conditions.",
                WeatherEventType.WINTER_STORM: "Heavy snow and strong winds are expected. Total snow accumulations of {amount} inches are forecast. Winds could gust as high as {wind} mph.",
            }
            
            if event_type in description_templates:
                desc_template = description_templates[event_type]
                description = desc_template.format(
                    time=effective_time.strftime('%I:%M %p'),
                    location=f"near {affected_areas.split(' ')[0]}",
                    direction=random.choice(["northeast", "southeast", "northwest", "southwest", "north", "south"]),
                    speed=random.randint(15, 45),
                    hazards=random.choice(["60 mph wind gusts and quarter size hail", "70 mph wind gusts and half dollar size hail", "destructive winds and large hail"]),
                    temp=random.randint(100, 115),
                    amount=random.randint(3, 12),
                    wind=random.randint(30, 50)
                )
            else:
                # Generic description
                descriptions = [
                    f"The National Weather Service has issued a {event_name} for {affected_areas}.",
                    f"Hazardous weather conditions are expected across {affected_areas}.",
                    f"Monitor weather conditions closely and take appropriate precautions.",
                    f"Conditions may become dangerous. Stay informed and be prepared to take action."
                ]
                description = random.choice(descriptions)
            
            # Generate instructions based on event type and severity
            instruction_templates = {
                WeatherEventType.TORNADO: [
                    "TAKE COVER NOW! Move to a basement or an interior room on the lowest floor of a sturdy building. Avoid windows.",
                    "Move immediately to the lowest floor and get under a sturdy object. Avoid auditoriums, cafeterias and gymnasiums.",
                    "Flying debris will be dangerous to those caught without shelter."
                ],
                WeatherEventType.FLASH_FLOOD: [
                    "Turn around, don't drown when encountering flooded roads. Most flood deaths occur in vehicles.",
                    "Move to higher ground immediately. Do not drive through flooded roadways.",
                    "Stay away from storm drains, culverts, creeks and streams."
                ],
                WeatherEventType.SEVERE_THUNDERSTORM: [
                    "Prepare immediately for large hail and damaging winds. Move to an interior room on the lowest floor.",
                    "For your protection move to an interior room on the lowest floor of a building.",
                    "Large hail and damaging winds and continuous cloud to ground lightning is occurring."
                ],
                WeatherEventType.EXTREME_HEAT: [
                    "Drink plenty of fluids, stay in an air-conditioned room, and avoid sun exposure.",
                    "Take extra precautions if you work or spend time outside. Reschedule strenuous activities to early morning or evening.",
                    "Check on relatives and neighbors. Young children and adults over 65 are more vulnerable to heat illness."
                ]
            }
            
            if event_type in instruction_templates:
                instruction = random.choice(instruction_templates[event_type])
            else:
                # Generic instructions based on severity
                if severity in [AlertSeverity.EXTREME, AlertSeverity.SEVERE]:
                    instruction = "Take immediate action to protect life and property. Monitor official sources for updates."
                else:
                    instruction = "Monitor weather conditions and be prepared to take action if conditions worsen."
            
            # Generate status (mostly actual, some tests)
            status_weights = [(AlertStatus.ACTUAL, 0.85), (AlertStatus.TEST, 0.1), 
                             (AlertStatus.EXERCISE, 0.03), (AlertStatus.DRAFT, 0.02)]
            status = random.choices(
                [s for s, w in status_weights],
                weights=[w for s, w in status_weights]
            )[0]
            
            # Category is mostly meteorological for weather
            category_weights = [(AlertCategory.METEOROLOGICAL, 0.9), (AlertCategory.GEOPHYSICAL, 0.05),
                               (AlertCategory.PUBLIC_SAFETY, 0.03), (AlertCategory.SECURITY, 0.02)]
            category = random.choices(
                [c for c, w in category_weights],
                weights=[w for c, w in category_weights]
            )[0]
            
            # Certainty and urgency correlate with severity
            if severity == AlertSeverity.EXTREME:
                certainty = random.choices([AlertCertainty.OBSERVED, AlertCertainty.LIKELY, AlertCertainty.POSSIBLE], 
                                         weights=[0.6, 0.3, 0.1])[0]
                urgency = random.choices([AlertUrgency.IMMEDIATE, AlertUrgency.EXPECTED], weights=[0.8, 0.2])[0]
            elif severity == AlertSeverity.SEVERE:
                certainty = random.choices([AlertCertainty.LIKELY, AlertCertainty.OBSERVED, AlertCertainty.POSSIBLE], 
                                         weights=[0.5, 0.3, 0.2])[0]
                urgency = random.choices([AlertUrgency.IMMEDIATE, AlertUrgency.EXPECTED], weights=[0.6, 0.4])[0]
            else:
                certainty = random.choices([AlertCertainty.LIKELY, AlertCertainty.POSSIBLE, AlertCertainty.OBSERVED], 
                                         weights=[0.4, 0.4, 0.2])[0]
                urgency = random.choices([AlertUrgency.EXPECTED, AlertUrgency.FUTURE, AlertUrgency.IMMEDIATE], 
                                       weights=[0.5, 0.3, 0.2])[0]
            
            # Create the weather alert
            alert = WeatherAlert(
                event_type=event_type,
                event=event_name,
                status=status,
                category=category,
                headline=headline,
                description=description,
                instruction=instruction,
                affected_areas=affected_areas,
                effective=effective_time,
                onset=onset_time,
                expires=expires_time,
                ends=ends_time,
                severity=severity,
                certainty=certainty,
                urgency=urgency,
            )
            
            alerts.append(alert)
        
        # Sort alerts by severity (extreme first) for better UI display
        severity_order = {AlertSeverity.EXTREME: 0, AlertSeverity.SEVERE: 1, 
                         AlertSeverity.MODERATE: 2, AlertSeverity.MINOR: 3}
        alerts.sort(key=lambda a: severity_order.get(a.severity, 4))
        
        return alerts
