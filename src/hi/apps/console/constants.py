class ConsoleConstants:

    CONSOLE_LOCKED_SESSION_VAR = 'console_locked'
    CONSOLE_AWAY_LOCK_TIMESTAMP_SESSION_VAR = 'console_away_lock_timestamp'

    # Cookie, not session: capabilities must survive session loss since
    # the sign-in page is where they matter most.
    DEVICE_CAPABILITIES_COOKIE_NAME = 'hi_device_capabilities'
    DEVICE_CAPABILITIES_COOKIE_MAX_AGE_SECS = 10 * 365 * 24 * 60 * 60
