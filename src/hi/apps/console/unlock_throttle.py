import math

import hi.apps.common.datetimeproxy as datetimeproxy

from .constants import ConsoleConstants


class UnlockThrottle:
    """
    Light brute-force mitigation for the console lock PIN: after
    MAX_FAILURES consecutive wrong PINs, unlock attempts are refused for
    LOCKOUT_SECS. State is kept in the session, so one console being
    throttled does not affect others.
    """

    MAX_FAILURES = 3
    LOCKOUT_SECS = 30

    def __init__( self, session ):
        self._session = session
        return

    def remaining_lockout_secs( self ) -> int:
        lockout_until = self._session.get( ConsoleConstants.UNLOCK_LOCKOUT_UNTIL_SESSION_VAR )
        if lockout_until is None:
            return 0
        remaining = lockout_until - datetimeproxy.now().timestamp()
        if remaining <= 0:
            self._session.pop( ConsoleConstants.UNLOCK_LOCKOUT_UNTIL_SESSION_VAR, None )
            return 0
        return math.ceil( remaining )

    def record_failure( self ):
        failure_count = self._session.get( ConsoleConstants.UNLOCK_FAILURE_COUNT_SESSION_VAR, 0 ) + 1
        if failure_count < self.MAX_FAILURES:
            self._session[ConsoleConstants.UNLOCK_FAILURE_COUNT_SESSION_VAR] = failure_count
            return
        self._session[ConsoleConstants.UNLOCK_FAILURE_COUNT_SESSION_VAR] = 0
        self._session[ConsoleConstants.UNLOCK_LOCKOUT_UNTIL_SESSION_VAR] = (
            datetimeproxy.now().timestamp() + self.LOCKOUT_SECS
        )
        return

    def reset( self ):
        self._session.pop( ConsoleConstants.UNLOCK_FAILURE_COUNT_SESSION_VAR, None )
        self._session.pop( ConsoleConstants.UNLOCK_LOCKOUT_UNTIL_SESSION_VAR, None )
        return
