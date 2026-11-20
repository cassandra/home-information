import logging

from django.test import SimpleTestCase

import hi.apps.common.datetimeproxy as datetimeproxy
from hi.apps.console.unlock_throttle import UnlockThrottle

logging.disable( logging.CRITICAL )


class TestUnlockThrottle( SimpleTestCase ):

    def setUp( self ):
        datetimeproxy.reset()
        self.addCleanup( datetimeproxy.reset )
        self.session = {}
        self.throttle = UnlockThrottle( self.session )
        return

    def fail_times( self, count ):
        for _ in range( count ):
            self.throttle.record_failure()
        return

    def test_no_lockout_below_max_failures( self ):
        self.fail_times( UnlockThrottle.MAX_FAILURES - 1 )
        self.assertEqual( self.throttle.remaining_lockout_secs(), 0 )
        return

    def test_max_failures_start_lockout( self ):
        self.fail_times( UnlockThrottle.MAX_FAILURES )
        self.assertEqual( self.throttle.remaining_lockout_secs(), UnlockThrottle.LOCKOUT_SECS )
        return

    def test_lockout_expires_and_count_starts_over( self ):
        self.fail_times( UnlockThrottle.MAX_FAILURES )
        datetimeproxy.increment( seconds = UnlockThrottle.LOCKOUT_SECS )
        self.assertEqual( self.throttle.remaining_lockout_secs(), 0 )

        self.fail_times( UnlockThrottle.MAX_FAILURES - 1 )
        self.assertEqual( self.throttle.remaining_lockout_secs(), 0 )
        return

    def test_remaining_rounds_up( self ):
        self.fail_times( UnlockThrottle.MAX_FAILURES )
        datetimeproxy.increment( seconds = UnlockThrottle.LOCKOUT_SECS - 1, milliseconds = 500 )
        self.assertEqual( self.throttle.remaining_lockout_secs(), 1 )
        return

    def test_reset_clears_failures( self ):
        self.fail_times( UnlockThrottle.MAX_FAILURES - 1 )
        self.throttle.reset()
        self.throttle.record_failure()
        self.assertEqual( self.throttle.remaining_lockout_secs(), 0 )
        return
