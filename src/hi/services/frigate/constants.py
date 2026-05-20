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

    # Per-camera live snapshot — Frigate exposes the most recent
    # decoded frame as a JPEG at this path. Used by HI's
    # ``get_entity_video_snapshot`` for the camera entity.
    CAMERA_SNAPSHOT_PATH_TEMPLATE = '/api/{camera_name}/latest.jpg'

    # Per-event snapshot — the frame captured at the time of
    # detection, attached to a SensorResponse as ``source_image_url``
    # so the alert / history views can show what the camera saw.
    EVENT_SNAPSHOT_PATH_TEMPLATE = '/api/events/{event_id}/snapshot.jpg'

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
    SNAPSHOT_URL = 'Snapshot Url'
    CLIP_URL = 'Clip Url'


class FrigateTimeouts:
    """Centralized timing knobs. Polling cadence inherited from the
    ZM defaults as a starting point — tune per real-install behavior."""

    POLLING_INTERVAL_SECS = 4
    API_TIMEOUT_SECS = 10.0

    HEALTH_CHECK_INTERVAL_SECS = 30
    MONITOR_HEARTBEAT_TIMEOUT_SECS = 20
