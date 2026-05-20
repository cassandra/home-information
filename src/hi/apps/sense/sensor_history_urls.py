"""URL-construction helpers for click-through from a sensor-history
data point (live ``SensorResponse``, persisted ``SensorHistory``, or a
merged-timeline row) to the corresponding video event browser or
details modal. Kept as pure functions of the values they need so any
data shape carrying sensor-history-derived fields can drive these
URLs without inheriting from a specific class or coupling to a
specific transient model."""

from typing import Optional

from django.urls import reverse


def sensor_history_video_browse_url(
        *,
        entity_id              : int,
        sensor_id              : int,
        sensor_history_id      : Optional[ int ],
        has_event_video_clip       : bool,
        provides_event_video_clip  : bool,
) -> Optional[ str ]:
    """Best URL to the video event browser for a given sensor-history
    data point. Returns the per-event detail URL when the data point
    itself has a stream; falls back to the sensor's event-timeline URL
    when the sensor produces streams generally; returns ``None`` when
    no video affordance is appropriate."""
    if has_event_video_clip and sensor_history_id:
        return reverse(
            'console_entity_video_sensor_history_detail',
            kwargs = {
                'entity_id': entity_id,
                'sensor_id': sensor_id,
                'sensor_history_id': sensor_history_id,
            },
        )
    if provides_event_video_clip:
        return reverse(
            'console_entity_video_sensor_history',
            kwargs = {
                'entity_id': entity_id,
                'sensor_id': sensor_id,
            },
        )
    return None


def sensor_history_details_url(
        *,
        sensor_history_id  : Optional[ int ],
        has_details        : bool,
) -> Optional[ str ]:
    """URL to the per-row details modal when the data point carries
    detail attributes; ``None`` otherwise."""
    if has_details and sensor_history_id:
        return reverse(
            'sense_sensor_history_details',
            kwargs = { 'sensor_history_id': sensor_history_id },
        )
    return None
