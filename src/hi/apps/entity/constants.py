"""
Constants for the entity app.
"""


class VideoStreamMetadataKeys:
    """Standard metadata keys for VideoStream objects."""

    # Core metadata fields
    STREAM_MODE = 'stream_mode'      # VideoStreamMode enum value (LIVE or RECORDED)
    DURATION_SECS = 'duration_secs'  # Duration in seconds for recorded content

    # Future extensibility
    # RESOLUTION = 'resolution'      # e.g., "1920x1080"
    # FPS = 'fps'                    # Frames per second
    # BITRATE = 'bitrate'            # Stream bitrate
