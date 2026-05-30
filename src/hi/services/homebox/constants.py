class HbTimeouts:
    """
    Centralized timeout and interval constants for HomeBox integration.
    Lives here so the manager / enums layer can reference these
    without importing from the monitor (which would invert the
    dependency direction).
    """

    # Default polling cadence. Used both as the manager's fallback and
    # as the schema-declared initial value for the user-editable
    # IntegrationAttribute. HomeBox is inventory data -- changes are
    # infrequent and the default cadence is correspondingly slow.
    POLLING_INTERVAL_SECS = 300

    API_TIMEOUT_SECS = 20.0
