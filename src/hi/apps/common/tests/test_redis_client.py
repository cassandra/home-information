import logging
import time
from unittest.mock import Mock, patch

import redis

from hi.apps.common.redis_client import get_redis_client, get_safe_cache_client
import hi.apps.common.redis_client as redis_client_module
from hi.testing.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class RedisClientTestCase( BaseTestCase ):
    """
    Connection failures must leave the module client as None rather than
    raising, and must not be permanent: singletons hold this client for the life
    of the process, so a transient failure that latched would cost the app its
    cache until a restart.
    """

    def setUp(self):
        super().setUp()

        # The test runner installs a process-global fake client. Both module
        # globals must be restored, or the Redis isolation of every later test
        # in the process is broken.
        original_client = redis_client_module._g_global_redis_client
        original_last_attempt = redis_client_module._g_last_connect_attempt

        def restore():
            redis_client_module._g_global_redis_client = original_client
            redis_client_module._g_last_connect_attempt = original_last_attempt

        self.addCleanup( restore )

        redis_client_module._g_global_redis_client = None
        redis_client_module._g_last_connect_attempt = None
        return

    def test_rejected_credentials_yield_no_client(self):
        """
        A password the server rejects must produce None, not an exception. This
        also pins the password actually reaching the connection: were it dropped,
        no AuthenticationError would be raised and a client would be returned.
        """
        def build_client( **kwargs ):
            if not kwargs.get('password'):
                return Mock()  # No password forwarded: the server would accept.
            client = Mock()
            client.ping.side_effect = redis.exceptions.AuthenticationError(
                'invalid username-password pair' )
            return client

        with self.settings( REDIS_PASSWORD = 'wrong-password' ):
            with patch.object( redis_client_module.redis, 'StrictRedis',
                               side_effect = build_client ):
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

    def test_failed_connection_is_retried_once_the_cooldown_elapses(self):
        working_client = Mock()
        failing_client = Mock()
        failing_client.ping.side_effect = redis.exceptions.ConnectionError( 'refused' )

        with patch.object( redis_client_module.redis, 'StrictRedis',
                           side_effect = [ failing_client, working_client ] ):
            self.assertIsNone( get_redis_client() )

            elapsed = redis_client_module.RECONNECT_COOLDOWN_SECS + 1
            with patch.object( redis_client_module.time, 'monotonic',
                               return_value = time.monotonic() + elapsed ):
                self.assertIs( get_redis_client(), working_client )
        return

    def test_failed_connection_is_not_retried_during_the_cooldown(self):
        """
        Without a cooldown every cache access during an outage would pay a
        connection timeout, so a second attempt must not be made immediately.
        """
        failing_client = Mock()
        failing_client.ping.side_effect = redis.exceptions.ConnectionError( 'refused' )

        with patch.object( redis_client_module.redis, 'StrictRedis',
                           return_value = failing_client ) as constructor:
            self.assertIsNone( get_redis_client() )
            self.assertIsNone( get_redis_client() )
            self.assertIsNone( get_redis_client() )

        self.assertEqual( constructor.call_count, 1 )
        return


class SafeCacheClientTestCase( BaseTestCase ):
    """
    Cache access must degrade rather than raise in both failure modes: when no
    connection was ever established, and when a live connection has since
    failed. Callers already treat a miss as normal, so degrading is invisible
    to them; raising is not.
    """

    def _patched_client( self, client ):
        return patch.object( redis_client_module, 'get_redis_client', return_value = client )

    def _assert_all_operations_degrade( self, cache ):
        self.assertIsNone( cache.get( 'some-key' ) )
        self.assertFalse( cache.set( 'some-key', 'some-value' ) )
        self.assertEqual( cache.delete( 'some-key' ), 0 )
        self.assertEqual( cache.smembers( 'some-set' ), set() )
        self.assertEqual( cache.pipeline().lindex( 'some-key', 0 ).execute(), list() )
        return

    def test_operations_degrade_when_no_client_was_established(self):
        with self._patched_client( None ):
            self._assert_all_operations_degrade( get_safe_cache_client() )
        return

    def test_operations_degrade_when_a_live_client_fails(self):
        client = Mock()
        for command_name in [ 'get', 'set', 'delete', 'smembers', 'pipeline' ]:
            getattr( client, command_name ).side_effect = redis.exceptions.ConnectionError( 'gone' )

        with self._patched_client( client ):
            self._assert_all_operations_degrade( get_safe_cache_client() )
        return

    def test_pipeline_degrades_when_execution_fails(self):
        """
        The pipeline is obtained before the server goes away, so the failure
        surfaces at execute() rather than when the pipeline is created.
        """
        pipeline = Mock()
        pipeline.execute.side_effect = redis.exceptions.ConnectionError( 'gone' )
        client = Mock()
        client.pipeline.return_value = pipeline

        with self._patched_client( client ):
            self.assertEqual( get_safe_cache_client().pipeline().lindex( 'k', 0 ).execute(),
                              list() )
        return
