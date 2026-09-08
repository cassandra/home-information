import logging
import time

import redis

from django.conf import settings

logger = logging.getLogger(__name__)

# How long to wait before re-attempting a connection after one fails. A single
# transient failure -- the bundled Redis not yet accepting connections while the
# app starts, say -- must not cost the process its cache for its whole lifetime.
# The cooldown keeps an outage from paying a connection timeout on every cache
# access.
#
RECONNECT_COOLDOWN_SECS = 60

# According to docs, the Redis client is thread safe.
#
_g_global_redis_client = None

# Monotonic timestamp of the last connection attempt, None before the first.
# Monotonic so that a system clock adjustment can neither postpone nor stampede
# reconnection.
#
_g_last_connect_attempt = None


def _is_connect_attempt_due():
    if _g_last_connect_attempt is None:
        return True
    return bool( ( time.monotonic() - _g_last_connect_attempt ) >= RECONNECT_COOLDOWN_SECS )


def initialize_global_cache_client():
    """
    Establishes the shared Redis client. Safe to call repeatedly: it returns
    immediately once connected, and while disconnected it re-attempts no more
    often than RECONNECT_COOLDOWN_SECS.
    """
    global _g_global_redis_client
    global _g_last_connect_attempt

    if _g_global_redis_client is not None:
        return
    if not _is_connect_attempt_due():
        return
    _g_last_connect_attempt = time.monotonic()

    host = settings.REDIS_HOST
    port = settings.REDIS_PORT
    password = settings.REDIS_PASSWORD
    if not port:
        port = 6379

    logger.info( "Attempting to connect to Redis at %s:%s ..." % ( host, port ))

    try:
        # An empty password is falsy to redis-py, which then sends no AUTH, so
        # this is the same connection as one built without credentials.
        redis_client = redis.StrictRedis( host                   = host,
                                          port                   = port,
                                          db                     = 0,
                                          password               = password or None,
                                          socket_timeout         = 5,
                                          socket_connect_timeout = 5,
                                          decode_responses       = True )
        redis_client.ping()
        _g_global_redis_client = redis_client
        logger.info( "Successfully connected to Redis at %s:%s" % ( host, port ))

    except redis.exceptions.AuthenticationError as e:
        # Every credential rejection arrives here: wrong password, a password
        # configured for a server that requires none, and a server requiring one
        # when none is configured. Subclass of ConnectionError, so it must
        # precede that handler to report credentials rather than reachability.
        logger.error( f'Redis rejected the credentials. Check whether the configured'
                      f' Redis password matches the server, and whether the server'
                      f' requires a password at all: {e}' )
    except redis.exceptions.ResponseError as e:
        # AuthenticationWrongNumberOfArgsError lands here rather than above, and
        # ResponseError is not a ConnectionError subclass, so without this it
        # would escape uncaught.
        logger.error( f'Redis refused the connection: {e}' )
    except ( ConnectionRefusedError, redis.exceptions.ConnectionError ) as e:
        logger.error( f'Could not connect to Redis server: {e}' )
    except ValueError as ve:
        logger.exception( f'Problem seting up Redis client: {ve}' )
        
    return


def exists_redis_client():
    if not _g_global_redis_client:
        initialize_global_cache_client()
    return _g_global_redis_client is not None
       

def get_redis_client():
    if not _g_global_redis_client:
        initialize_global_cache_client()
    return _g_global_redis_client


def clear_redis_client():
    """
    Discards the shared client and allows an immediate reconnect. Provided for
    test convenience; live code has no reason to call it, since reconnection is
    handled by initialize_global_cache_client().
    """
    global _g_global_redis_client
    global _g_last_connect_attempt
    if _g_global_redis_client:
        logger.info( "Clearing existing Redis connection" )
    _g_global_redis_client = None  # No good way to explicitly "close" this
    _g_last_connect_attempt = None
    return


class CacheNotAvailableError(Exception):
    pass


    
