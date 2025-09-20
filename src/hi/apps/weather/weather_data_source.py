from abc import abstractmethod
from datetime import datetime
import logging
import redis

from django.conf import settings

import hi.apps.common.datetimeproxy as datetimeproxy
from hi.apps.common.redis_client import get_redis_client
from hi.apps.console.console_helper import ConsoleSettingsHelper
from hi.apps.system.api_health_status_provider import ApiHealthStatusProvider
from hi.apps.system.provider_info import ProviderInfo
from hi.apps.weather.transient_models import DataPointSource

logger = logging.getLogger(__name__)


class WeatherDataSource( ApiHealthStatusProvider ):

    TRACE = False
    FORCE_CAN_POLL = False  # For debugging

    @classmethod
    @abstractmethod
    def weather_source_id(cls):
        pass
    
    @classmethod
    @abstractmethod
    def weather_source_label(cls):
        pass
    
    @classmethod
    @abstractmethod
    def weather_source_abbreviation(cls):
        pass
    
    @abstractmethod
    async def get_data(self):
        """ Main method periodically called to fetch data """
        pass
    
    def requires_api_key(self) -> bool:
        """Override in subclasses that require an API key."""
        return False
    
    def get_default_enabled_state(self) -> bool:
        """Override in subclasses to set default enabled/disabled state."""
        return True
    
    def __init__( self,
                  priority                       : int,
                  requests_per_day_limit         : int,
                  requests_per_polling_interval  : int,
                  min_polling_interval_secs      : int ):
        self._id = self.weather_source_id()
        self._label = self.weather_source_label()
        self._abbreviation = self.weather_source_abbreviation()
        self._priority = priority  # Lower numbers are higher priority
        self._data_point_source = DataPointSource(
            id = self._id,
            label = self._label,
            abbreviation = self._abbreviation,
            priority = self._priority,
        )
        self._logger = logging.getLogger(self.__class__.__module__)

        polling_intervals_per_day_limit = requests_per_day_limit / requests_per_polling_interval
        limit_polling_interval_secs = ( 24 * 60 * 60 ) / polling_intervals_per_day_limit
        self._polling_interval_secs = max( limit_polling_interval_secs,
                                           min_polling_interval_secs )
        self.polling_started = False
        
        self._console_settings_helper = ConsoleSettingsHelper()
        self._weather_settings_helper = None  # Lazy initialized to avoid circular imports
        
        # Store last query times in redis as external API rate limits do
        # not care how many times our server restarts.
        #
        self._redis_client = get_redis_client()
        self._redis_last_poll_key = f'ws:last:dt:{self._id}'
        return

    @property
    def id(self):
        return self._id

    @property
    def label(self):
        return self._label

    @property
    def abbreviation(self):
        return self._abbreviation

    @property
    def data_point_source(self) -> DataPointSource:
        return self._data_point_source

    @property
    def priority(self):
        return self._priority

    @property
    def redis_client(self):
        return self._redis_client

    @property
    def geographic_location(self):
        return self._console_settings_helper.get_geographic_location()
    
    @property
    def tz_name(self):
        return self._console_settings_helper.get_tz_name()
    
    def get_api_timeout(self) -> float:
        return 30.0
    
    def _get_weather_settings_helper(self):
        """Lazy initialization of weather settings helper to avoid circular imports."""
        if self._weather_settings_helper is None:
            from hi.apps.weather.weather_settings_helper import WeatherSettingsHelper
            self._weather_settings_helper = WeatherSettingsHelper()
        return self._weather_settings_helper
    
    @property 
    def is_enabled(self) -> bool:
        """Check if this weather source is enabled in settings."""
        return self._get_weather_settings_helper().is_weather_source_enabled(self._id)
    
    @property
    def api_key(self) -> str:
        """Get the API key for this weather source from settings."""
        return self._get_weather_settings_helper().get_weather_source_api_key(self._id)
    
    @property
    def is_cache_enabled(self) -> bool:
        """Check if weather data caching is enabled."""
        return self._get_weather_settings_helper().is_weather_cache_enabled()
        
    @classmethod
    def get_api_provider_info(cls) -> ProviderInfo:
        """ Subclasses should override with something more meaningful. """
        return ProviderInfo(
            provider_id = f'hi.apps.weather.weather_sources.{cls.weather_source_id()}',
            provider_name = cls.weather_source_label(),
            description = f'{cls.weather_source_label()} ({cls.weather_source_abbreviation})',
        )

    async def fetch(self):
        can_fetch = self.can_fetch()

        # Need to deal with a server restart where we have recently cached
        # the last poll time, but we have not populated the data in memory
        # yet.
        #
        if not self.polling_started:
            can_fetch = True
            self.polling_started = True

        if not can_fetch:
            if self.TRACE:
                logger.debug( f'Polling limits. Skipping weather data fetch for: {self.label}' )
            return

        logger.debug( f'Fetching weather data for: {self.label}' )
        self.set_last_poll_time()
        try:
            await self.get_data()
        except Exception:
            logger.exception( f'Problem with weather source: {self.label}' )
        return
    
    def can_fetch(self):

        if settings.DEBUG and self.FORCE_CAN_POLL:
            logger.warning( 'Force polling in effect.' )
            return True
        
        last_poll_datetime = self.fetch_last_poll_datetime()
        if not last_poll_datetime:
            logger.info( f'No last polling data for: {self.label}' )
            return True
        
        last_poll_elapsed = datetimeproxy.now() - last_poll_datetime
        elapsed_secs = last_poll_elapsed.total_seconds()
        if elapsed_secs < self._polling_interval_secs:
            if self.TRACE:
                logger.debug( f'[{self.id}] Last={last_poll_datetime}, Elapsed={elapsed_secs}s'
                              f' < Limit={self._polling_interval_secs}s' )
            return False
        return True
        
    def set_last_poll_time(self):
        poll_time = datetimeproxy.now()
        poll_time_str = poll_time.isoformat()
        try:
            self._redis_client.set( self._redis_last_poll_key, poll_time_str )
            return True
        except redis.exceptions.RedisError as e:
            logger.error( f'Error storing datetime: {e}')
        return False
    
    def fetch_last_poll_datetime(self):
        poll_time_str = self._redis_client.get( self._redis_last_poll_key )
        if not poll_time_str:
            return None
        try:
            poll_time = datetime.fromisoformat( poll_time_str )
            return poll_time
        except ValueError as e:
            logger.error( f'Error parsing datetime string: {e}' )
        return None
