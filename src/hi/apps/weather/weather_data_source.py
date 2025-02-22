from datetime import datetime
import logging
import redis

import hi.apps.common.datetimeproxy as datetimeproxy
from hi.apps.common.redis_client import get_redis_client
from hi.apps.console.console_helper import ConsoleSettingsHelper
from hi.apps.weather.transient_models import DataSource

logger = logging.getLogger(__name__)


class WeatherDataSource:

    TRACE = True

    def get_data(self):
        raise NotImplementedError('Subclasses must override this')
    
    def __init__( self,
                  id                   : str,
                  label                : str,
                  priority             : int,
                  requests_per_day : int ):
        self._id = id
        self._label = label
        self._data_source = DataSource(
            id = self._id,
            label = self._label,
        )
        self._priority = priority  # Lower numbers are higher priority
        self._requests_per_day = requests_per_day
        self._min_polling_interval_secs = ( 24 * 60 * 60 ) / self._requests_per_day

        self._console_settings_helper = ConsoleSettingsHelper()
        
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
    def data_source(self) -> DataSource:
        return self._data_source

    @property
    def priority(self):
        return self._priority

    @property
    def redis_client(self):
        return self._redis_client

    @property
    def geographic_location(self):
        self._console_settings_helper.get_geographic_location()
        
    def fetch(self):
        if not self.can_poll():
            if self.TRACE:
                logger.debug( f'Polling limits. Skipping weather data fetch for: {self.label}' )
            return

        logger.debug( f'Fetching weather data for: {self.label}' )
        self.set_last_poll_time()
        self.get_data()
        return
    
    def can_poll(self):
        last_poll_datetime = self.fetch_last_poll_datetime()
        if not last_poll_datetime:
            logger.info( f'No last polling data for: {self.label}' )
            return True
        
        last_poll_elapsed = datetimeproxy.now() - last_poll_datetime
        elapsed_secs = last_poll_elapsed.total_seconds()
        if elapsed_secs < self._min_polling_interval_secs:
            if self.TRACE:
                logger.debug( f'[{self.id}] Last={last_poll_datetime}, Elapsed={elapsed_secs}s'
                              f' < Limit={self._min_polling_interval_secs}s' )
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
