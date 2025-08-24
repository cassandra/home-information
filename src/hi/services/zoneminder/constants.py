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