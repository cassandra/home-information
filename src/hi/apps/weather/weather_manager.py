import logging
from threading import Lock

from hi.apps.common.singleton import Singleton
from hi.apps.config.settings_mixins import SettingsMixin

from .transient_models import WeatherOverviewData

logger = logging.getLogger(__name__)


class WeatherManager( Singleton, SettingsMixin ):

    def __init_singleton__(self):
        
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
    
    def get_weather_overview_data(self) -> WeatherOverviewData:
        return WeatherOverviewData(
            temperature = 18,
        )
    
