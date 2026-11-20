from hi.apps.common.keypad_spec import KeypadSpec


class ConsoleConstants:

    LOCK_PIN_KEYPAD = KeypadSpec(
        alphabet = '1234567890',
        length = 4,
        columns = 3,
    )

    CONSOLE_LOCKED_SESSION_VAR = 'console_locked'
    CONSOLE_AWAY_LOCK_TIMESTAMP_SESSION_VAR = 'console_away_lock_timestamp'

    DEVICE_CAPABILITIES_COOKIE_NAME = 'hi_device_capabilities'
    DEVICE_CAPABILITIES_COOKIE_MAX_AGE_SECS = 10 * 365 * 24 * 60 * 60
