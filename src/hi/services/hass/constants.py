class HassTimeouts:
    """
    Centralized timeout and interval constants for Home Assistant
    integration. Lives here so the manager / enums layer can reference
    these without importing from the monitor (which would invert the
    dependency direction).
    """

    # Default polling cadence. Used both as the manager's fallback and
    # as the schema-declared initial value for the user-editable
    # IntegrationAttribute, so the at-rest behavior matches what the
    # config page shows on a fresh install.
    POLLING_INTERVAL_SECS = 4

    # Shorter timeout appropriate for the polling cadence above.
    API_TIMEOUT_SECS = 10.0
