class FrigateApi:
    """Centralized Frigate wire-format strings (endpoint paths,
    response field names, object-class constants). All wire-side
    string literals for the Frigate integration MUST be declared
    here — see ``docs/dev/integrations/integration-guidelines.md``.

    Filled out incrementally as each capability is implemented.
    """

    # --- Endpoints (paths under the configured BASE_URL) ---
    EVENTS_PATH = '/api/events'
    STATS_PATH = '/api/stats'
    CONFIG_PATH = '/api/config'

    CAMERA_SNAPSHOT_PATH_TEMPLATE = '/api/{camera_name}/latest.jpg'
    EVENT_SNAPSHOT_PATH_TEMPLATE = '/api/events/{event_id}/snapshot.jpg'
    EVENT_CLIP_PATH_TEMPLATE = '/api/events/{event_id}/clip.mp4'

    # --- Frigate object-class wire values (subset; extended as needed) ---
    OBJECT_CLASS_PERSON = 'person'
    OBJECT_CLASS_CAR = 'car'
    OBJECT_CLASS_DOG = 'dog'
    OBJECT_CLASS_CAT = 'cat'
    OBJECT_CLASS_PACKAGE = 'package'


class FrigateDetailKeys:
    """``SensorResponse.detail_attrs`` keys used by the Frigate
    integration.

    WARNING: These keys are persisted in the database and surfaced in
    the event-detail UI. Changing them breaks historical data and
    requires a migration. Add new keys; do not rename.
    """
    EVENT_ID = 'Event Id'
    START_TIME = 'Start Time'
    OBJECT_CLASS = 'Object Class'
    SCORE = 'Score'
    SUB_LABEL = 'Sub Label'
    ZONES = 'Zones'
    DURATION_SECS = 'Duration (secs)'


class FrigateTimeouts:
    """Centralized timing knobs. Polling cadence inherited from the
    ZM defaults as a starting point — tune per real-install behavior."""

    POLLING_INTERVAL_SECS = 4
    API_TIMEOUT_SECS = 10.0

    HEALTH_CHECK_INTERVAL_SECS = 30
    MONITOR_HEARTBEAT_TIMEOUT_SECS = 20

    # Upper bound on how long an event may stay open in HI's tracking
    # set before we force-close it. Frigate normally closes events
    # within minutes; an event still open after this threshold is
    # treated as orphaned (Frigate restart, dropped detection, etc.).
    MAX_OPEN_EVENT_AGE_SECS = 60 * 60
