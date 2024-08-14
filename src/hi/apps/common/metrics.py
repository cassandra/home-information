# See: https://datadogpy.readthedocs.io/en/latest/

from datadog import initialize, statsd
from functools import wraps
import logging
import time

from django.conf import settings

logger = logging.getLogger( __name__ )


if settings.UNIT_TESTING:
    from unittest.mock import Mock
    statsd.socket = Mock()

    
options = {
    'statsd_host': settings.DATADOG_AGENT_HOST,
    'statsd_port': settings.DATADOG_AGENT_PORT,
    'statsd_namespace': 'waa',
    'statsd_constant_tags': [ f'environment:{settings.ENVIRONMENT}' ],
}

initialize(**options)


def timed( method ):
    """ Decorator for timing function/method execution times """

    @wraps( method )
    def wrapper( *args, **kwargs):
        start_time = time.time()
        result = method(*args, **kwargs)
        end_time = time.time()
        elapsed_time_ms = (end_time - start_time)

        statsd.timing( 'timing',
                       elapsed_time_ms,
                       tags = [ f'name:{method.__name__}' ] )
        
        logger.debug( f'TIMED: {method.__name__} : {elapsed_time_ms:.2f} ms' )
        return result
    return wrapper


def increment( name, tags = None ):
    statsd.increment( name, tags = tags )
    return


def decrement( name, tags = None ):
    statsd.decrement( name, tags = tags )
    return


def gauge( name, value, tags = None ):
    statsd.gauge( name, value, tags = tags )
    return


def histogram( name, value, tags = None ):
    statsd.histogram( name, value, tags = tags )
    return


def event( title, text, alert_type = 'info', tags = None ):
    assert alert_type in { 'error', 'warning', 'success', 'info' }
    statsd.event( title, text, alert_type = alert_type, tags=tags )
    return


def exception( exception : Exception ):
    statsd.increment( 'exception', tags = [ f'name:{type(exception)}' ] )
    return


def error( label : str ):
    statsd.increment( 'error', tags = [ f'name:{label}' ] )
    return


def warning( label : str ):
    statsd.increment( 'warning', tags = [ f'name:{label}' ] )
    return


def increment_event( label : str ):
    statsd.increment( 'event', tags = [ f'name:{label}' ] )
    return
