class ZmDetailKeys:
    """
    ZoneMinder detail_attrs keys used in SensorResponse objects.

    WARNING: These keys are persisted in the database and used across
    multiple integrations. Changing them will break compatibility with
    historical data and require data migration.
    """
    EVENT_ID_ATTR_NAME = 'Event Id'  # DO NOT CHANGE - stored in database
    START_TIME = 'Start Time'
    SCORE = 'Score'
    DURATION_SECS = 'Duration (secs)'
    ALARMED_FRAMES = 'Alarmed Frames'
    TOTAL_FRAMES = 'Total Frames'
    NOTES = 'Notes'


class ZmTimeouts:
    """
    Centralized timeout and interval constants for ZoneMinder integration.

    These values are carefully aligned to ensure reliable operation:
    - API timeout should be less than polling interval to avoid overlapping calls
    - PyZM client timeout should align with API timeout for consistency
    - Health check intervals provide regular status updates without overwhelming the system
    """
    # Core polling configuration
    POLLING_INTERVAL_SECS = 4
    API_TIMEOUT_SECS = 10.0  # Longer than polling to allow for network delays but not too long to block

    # PyZM client timeout (should align with API timeout for consistency)
    PYZM_CLIENT_TIMEOUT_SECS = 10.0

    # Health check intervals
    HEALTH_CHECK_INTERVAL_SECS = 30  # Regular health status updates
    MONITOR_HEARTBEAT_TIMEOUT_SECS = 20  # 5x polling interval = reasonable timeout for heartbeat

    # Cache refresh intervals (from zm_manager.py)
    STATE_REFRESH_INTERVAL_SECS = 300
    MONITOR_REFRESH_INTERVAL_SECS = 300

    # Performance thresholds for alerting
    API_RESPONSE_WARNING_THRESHOLD_SECS = 5.0  # Warn if API calls take longer than this
    API_RESPONSE_CRITICAL_THRESHOLD_SECS = 8.0  # Critical if API calls approach timeout
