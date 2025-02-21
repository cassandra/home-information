import logging
from threading import Lock
from typing import List

from hi.apps.common.singleton import Singleton
from hi.apps.config.settings_mixins import SettingsMixin

from .transient_models import (
    DailyAstronomicalData,
    WeatherConditionsData,
    WeatherForecastData,
    WeatherHistoryData,
    WeatherOverviewData,
)

logger = logging.getLogger(__name__)


class WeatherManager( Singleton, SettingsMixin ):

    def __init_singleton__(self):

        self._current_conditions_data = None
        self._todays_astronomical_data = None
        self._data_lock = Lock()
        self._was_initialized = False
        return

    def ensure_initialized(self):
        if self._was_initialized:
            return
        try:
            self._initialize()
        except Exception as e:
            logger.exception( 'Problem trying to initialize weather', e )
        self._was_initialized = True
        return

    def _initialize( self ):
        return
    
    def get_current_conditions_data(self) -> WeatherConditionsData:
        return self._current_conditions_data
    
    def get_todays_astronomical_data(self) -> DailyAstronomicalData:
        return self._todays_astronomical_data
    
    def get_weather_overview_data(self) -> WeatherOverviewData:
        return WeatherOverviewData(
            current_conditions_data = self._current_conditions_data,
            todays_astronomical_data = self._todays_astronomical_data,
        )
    
    def get_hourly_forecast_data_list(self) -> List[ WeatherForecastData ]:
        return []
    
    def get_daily_forecast_data_list(self) -> List[ WeatherForecastData ]:
        return []
    
    def get_daily_history_data_list(self) -> List[ WeatherHistoryData ]:
        return []
    
