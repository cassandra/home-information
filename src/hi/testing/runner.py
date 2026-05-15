"""
Custom test runner that isolates tests from real Redis.

Replaces the direct Redis client with fakeredis and Django's cache backend
with LocMemCache before any test runs. This ensures no test touches the
real Redis instance regardless of which test base class is used.

Configured via TEST_RUNNER in settings/base.py.
"""
import fakeredis

from django.test import override_settings
from django.test.runner import DiscoverRunner

import hi.apps.common.redis_client as redis_client_module

LOCMEM_CACHE = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}


class HiTestRunner( DiscoverRunner ):

    def setup_test_environment( self, **kwargs ):
        super().setup_test_environment( **kwargs )

        # Replace the global Redis client with an in-memory fake so no
        # test hits real Redis. Mark as initialized so the real
        # initialize_global_cache_client() is never called.
        self._original_redis_client = redis_client_module._g_global_redis_client
        self._original_redis_initialized = redis_client_module._g_global_redis_initialized_attempted
        redis_client_module._g_global_redis_client = fakeredis.FakeRedis( decode_responses = True )
        redis_client_module._g_global_redis_initialized_attempted = True

        # Override Django's cache to use in-memory backend so cache.clear()
        # does not execute FLUSHDB on real Redis.
        self._cache_override = override_settings( CACHES = LOCMEM_CACHE )
        self._cache_override.enable()
        return

    def teardown_test_environment( self, **kwargs ):
        self._cache_override.disable()
        redis_client_module._g_global_redis_client = self._original_redis_client
        redis_client_module._g_global_redis_initialized_attempted = self._original_redis_initialized
        super().teardown_test_environment( **kwargs )
        return
