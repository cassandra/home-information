from datetime import datetime, timedelta, time
import random
from typing import List

import hi.apps.common.datetimeproxy as datetimeproxy
from hi.apps.weather.enums import (
    WeatherPhenomenon,
    WeatherPhenomenonIntensity,
    WeatherPhenomenonModifier,
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
            minute=random.randint(-30, 30),
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
    def get_random_hourly_forecast_data_list(cls,
                                             now: datetime = None,
                                             source: DataPointSource = None) -> List[WeatherForecastData]:
        if not now:
            now = datetimeproxy.now()
        if not source:
            source = cls._create_default_source()
        
        hourly_forecast_data_list = list()
        for hour_idx in range(24):
            interval_start = now.replace(minute=0, second=0, microsecond=0)
            interval_start += timedelta(hours=hour_idx + 1)
            interval_end = interval_start + timedelta(hours=1)
            forecast_data = cls.get_random_forecast_data( 
                interval_start=interval_start,
                interval_end=interval_end,
                now=now,
                source=source,
            )
            hourly_forecast_data_list.append(forecast_data)
            continue
        return hourly_forecast_data_list
    
    @classmethod
    def get_random_daily_forecast_data_list(cls,
                                            now: datetime = None,
                                            source: DataPointSource = None) -> List[WeatherForecastData]:
        if not now:
            now = datetimeproxy.now()
        if not source:
            source = cls._create_default_source()
        
        daily_forecast_data_list = list()
        for day_idx in range(10):
            interval_start = now.replace(hour=0, minute=0, second=0, microsecond=1)
            interval_start += timedelta(hours=24 * day_idx)
            interval_end = interval_start + timedelta(hours=24)
            forecast_data = cls.get_random_forecast_data( 
                interval_start=interval_start,
                interval_end=interval_end,
                now=now,
                source=source,
            )
            daily_forecast_data_list.append(forecast_data)
            continue
        return daily_forecast_data_list

    @classmethod
    def get_random_hourly_interval_forecast_data_list(cls,
                                                      now: datetime = None,
                                                      source: DataPointSource = None) -> List[IntervalWeatherForecast]:
        """Get random hourly forecast data wrapped in IntervalWeatherForecast objects."""
        if not now:
            now = datetimeproxy.now()
        if not source:
            source = cls._create_default_source()
        
        station = cls._create_test_station(source)
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
        
        station = cls._create_test_station(source)
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
        
        station = cls._create_test_station(source)
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
    def get_random_daily_history_data_list(cls,
                                           now: datetime = None,
                                           source: DataPointSource = None) -> List[WeatherHistoryData]:
        if not now:
            now = datetimeproxy.now()
        if not source:
            source = cls._create_default_source()
        
        daily_history_data_list = list()
        for day_idx in range(10):
            interval_start = now.replace(hour=0, minute=0, second=0, microsecond=1)
            interval_start -= timedelta(hours=24 * (day_idx + 1))
            interval_end = interval_start + timedelta(hours=24)
            history_data = cls.get_random_history_data( 
                interval_start=interval_start,
                interval_end=interval_end,
                now=now,
                source=source,
            )
            daily_history_data_list.append(history_data)
            continue
        return daily_history_data_list
    
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