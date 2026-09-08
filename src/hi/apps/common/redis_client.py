import logging
import redis

from django.conf import settings

logger = logging.getLogger(__name__)

# We want to allow running without the redis dependency, so it is not
# enough to see a "None" for the client to know whether we tried to
# initialize the client or not.
#
_g_global_redis_initialized_attempted = False

# According to docs, the Redis client is thread safe.
#
_g_global_redis_client = None


def initialize_global_cache_client():
    """
    Need to call this once at process start if you want to use cache-based
    features.
    """
    global _g_global_redis_initialized_attempted
    global _g_global_redis_client

    if _g_global_redis_initialized_attempted:
        return
    _g_global_redis_initialized_attempted = True
    
    if _g_global_redis_client:
        _g_global_redis_client = None  # No good way to explicitly "close" this

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
    global _g_global_redis_initialized_attempted
    global _g_global_redis_client
    if _g_global_redis_client:
        logger.info( "Clearing existing Redis connection" )
        _g_global_redis_initialized_attempted = False
        _g_global_redis_client = None  # No good way to explicitly "close" this
    return


class CacheNotAvailableError(Exception):
    pass


    
