import logging
from unittest.mock import Mock, patch

import redis

from hi.apps.common.redis_client import get_redis_client
import hi.apps.common.redis_client as redis_client_module
from hi.testing.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class RedisClientConnectFailureTestCase( BaseTestCase ):
    """
    A failed connection must leave the module client as None rather than
    raising, since callers treat None as "cache unavailable".
    """

    def setUp(self):
        super().setUp()

        # The test runner installs a process-global fake client and marks
        # initialization as already attempted. Both must be restored, or the
        # Redis isolation of every later test in the process is broken.
        original_client = redis_client_module._g_global_redis_client
        original_attempted = redis_client_module._g_global_redis_initialized_attempted

        def restore():
            redis_client_module._g_global_redis_client = original_client
            redis_client_module._g_global_redis_initialized_attempted = original_attempted

        self.addCleanup( restore )

        redis_client_module._g_global_redis_client = None
        redis_client_module._g_global_redis_initialized_attempted = False
        return

    def test_rejected_credentials_yield_no_client(self):
        """
        A password the server rejects must produce None, not an exception. This
        also pins the password actually reaching the connection: were it dropped,
        no AuthenticationError would be raised and a client would be returned.
        """
        def raise_authentication_error( **kwargs ):
            if not kwargs.get('password'):
                return Mock()  # No password forwarded: the server would accept.
            client = Mock()
            client.ping.side_effect = redis.exceptions.AuthenticationError(
                'invalid username-password pair' )
            return client

        with self.settings( REDIS_PASSWORD = 'wrong-password' ):
            with patch.object( redis_client_module.redis, 'StrictRedis',
                               side_effect = raise_authentication_error ):
                self.assertIsNone( get_redis_client() )
        return

    def test_server_side_rejection_yields_no_client(self):
        """
        ResponseError is not a ConnectionError subclass, so without its own
        handler it would escape initialize_global_cache_client() uncaught.
        """
        client = Mock()
        client.ping.side_effect = redis.exceptions.ResponseError( 'wrong number of arguments' )

        with patch.object( redis_client_module.redis, 'StrictRedis', return_value = client ):
            self.assertIsNone( get_redis_client() )
        return
