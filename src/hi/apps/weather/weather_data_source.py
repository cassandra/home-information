from abc import abstractmethod
from datetime import datetime
import logging
import redis
import requests
from urllib.parse import urlparse

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
    BASE_URL = ''  # Override in each subclass with the canonical upstream URL.

    LOCALHOST_HOSTNAMES = ( '127.0.0.1', 'localhost', '::1' )

    def _log_fetch_error( self, label : str, exc : Exception ) -> None:
        """Log an upstream-fetch failure at the right level / verbosity.

        HTTP errors and other ``requests`` failures emit a single-line
        ERROR — the status/url/message is the whole story and a
        traceback is just noise. Anything else still gets the full
        ``logger.exception`` traceback because it's likely a real bug
        in the parsing or wiring path.
        """
        if isinstance( exc, requests.exceptions.HTTPError ):
            response = exc.response
            if response is not None:
                logger.error(
                    f'Problem fetching {self._abbreviation} {label}: '
                    f'HTTP {response.status_code} for {response.url}'
                )
                return
        if isinstance( exc, requests.exceptions.RequestException ):
            logger.error(
                f'Problem fetching {self._abbreviation} {label}: '
                f'{type(exc).__name__}: {exc}'
            )
            return
        logger.exception( f'Problem fetching {self._abbreviation} {label}: {exc}' )
        return

    def _is_localhost_target( self ) -> bool:
        host = urlparse( self._get_base_url() ).hostname or ''
        return host.lower() in self.LOCALHOST_HOSTNAMES

    def _get_base_url( self ) -> str:
        """Effective base URL for this source's HTTP calls.

        Consults the configured ``<SOURCE>_BASE_URL`` setting (lets
        operators point a source at a simulator, mirror, etc.) and
        falls back to the subclass's canonical ``BASE_URL`` constant
        when the setting is unset.
        """
        helper = self._get_weather_settings_helper()
        if helper:
            override = helper.get_weather_source_base_url( self.weather_source_id() )
            if override:
                return override
        return self.BASE_URL

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

    def _api_get_json( self,
                       operation_name : str,
                       url            : str,
                       *,
                       headers        : dict  = None,
                       timeout        : float = None ) -> dict:
        """Issue a GET, track it for API health, and return parsed JSON.

        Wraps the entire request lifecycle (HTTP status check + JSON
        parse) inside ``api_call_context`` so that:

        - 4xx/5xx responses (HTTPError from ``raise_for_status``)
        - JSON parse failures
        - network errors / timeouts (RequestException)

        all count against the API success rate. Tracking only the
        ``requests.get`` call would let HTTP errors slip through as
        ``SUCCESS`` because ``requests`` returns a Response object
        even for non-2xx status — that was the original bug.
        """
        if timeout is None:
            timeout = self.get_api_timeout()
        with self.api_call_context( operation_name ):
            response = requests.get(
                url,
                headers = headers,
                timeout = timeout,
            )
            response.raise_for_status()
            return response.json()
    
    def _get_weather_settings_helper(self):
        """Lazy initialization of weather settings helper to avoid circular imports."""
        if self._weather_settings_helper is None:
            from hi.apps.weather.weather_settings_helper import WeatherSettingsHelper
            self._weather_settings_helper = WeatherSettingsHelper()
        return self._weather_settings_helper

    @property
    def is_enabled(self) -> bool:
        return self._get_weather_settings_helper().is_weather_source_enabled(self._id)

    @property
    def api_key(self) -> str:
        return self._get_weather_settings_helper().get_weather_source_api_key(self._id)

    @property
    def is_cache_enabled(self) -> bool:
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
                logger.debug(f'Polling limits. Skipping weather data fetch for: {self.label}')
            return

        logger.debug( f'Fetching weather data for: {self.label}' )
        self.set_last_poll_time()
        try:
            await self.get_data()
        except Exception as e:
            message = f'Problem with weather source: {self.label}: {e}'
            self.record_error( message )
            logger.exception( message )
        return
    
    def can_fetch(self):

        # Targeting a localhost simulator in DEBUG means the operator
        # is iterating against a fake API — rate limits don't apply.
        if settings.DEBUG and self._is_localhost_target():
            logger.debug(
                f'[{self.id}] Bypassing rate limit (DEBUG + localhost target)'
            )
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
