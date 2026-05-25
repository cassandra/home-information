import logging
import time

from django import template

from hi.integrations.integration_manager import IntegrationManager

logger = logging.getLogger(__name__)

register = template.Library()


@register.simple_tag
def sensor_response_video_stream(sensor_response):
    """
    Get recorded video stream for a SensorResponse.

    Args:
        sensor_response: SensorResponse object

    Returns:
        VideoStream object or None if no video available
    """
    if not sensor_response or not sensor_response.has_event_video_clip:
        return None

    try:
        # Get the entity from the sensor response
        if not sensor_response.sensor:
            logger.debug("SensorResponse has no associated sensor")
            return None

        entity = sensor_response.sensor.entity_state.entity

        gateway = IntegrationManager().get_integration_gateway(entity.integration_id)

        if not gateway:
            logger.warning(f"No integration gateway found for {entity.integration_id}")
            return None

        connector = gateway.get_connector()
        if connector is None:
            return None

        # Get recorded video stream from sensor response
        video_stream = connector.get_sensor_response_video_stream(sensor_response)

        if video_stream:
            return video_stream

        logger.debug("No video stream available for sensor response")
        return None

    except Exception as e:
        logger.error(f"Error getting video stream for sensor response: {e}")
        return None


@register.simple_tag
def sensor_response_event_snapshot_url(sensor_response):
    """Per-event captured-frame URL for a SensorResponse, generated
    fresh by the owning gateway each render. Returns ``None`` when
    the response carries no snapshot (``has_event_video_snapshot``
    False), the integration can't produce one, or any error
    occurs."""
    if not sensor_response or not sensor_response.has_event_video_snapshot:
        return None

    try:
        if not sensor_response.sensor:
            logger.debug("SensorResponse has no associated sensor")
            return None

        entity = sensor_response.sensor.entity_state.entity
        gateway = IntegrationManager().get_integration_gateway(entity.integration_id)
        if not gateway:
            logger.warning(f"No integration gateway found for {entity.integration_id}")
            return None
        connector = gateway.get_connector()
        if connector is None:
            return None
        return connector.get_sensor_response_event_snapshot_url(sensor_response)
    except Exception as e:
        logger.error(f"Error getting event snapshot URL for sensor response: {e}")
        return None


@register.simple_tag
def entity_video_stream(entity):
    """
    Get entity live video stream for an entity object.

    Args:
        entity: Entity object

    Returns:
        VideoStream object or None if no video available
    """
    if not entity:
        return None

    try:
        gateway = IntegrationManager().get_integration_gateway(entity.integration_id)

        if not gateway:
            logger.warning(f"No integration gateway found for {entity.integration_id}")
            return None

        connector = gateway.get_connector()
        if connector is None:
            return None

        video_stream = connector.get_entity_video_stream(entity)

        if video_stream:
            return video_stream

        logger.debug(f"No video stream available for entity {entity.id}")
        return None

    except Exception as e:
        logger.error(f"Error getting video stream for entity {entity.id}: {e}")
        return None


@register.simple_tag
def cache_bust_url(url):
    """Append a unique cache-busting query parameter so each template
    render produces a distinct URL. Snapshot URLs are otherwise stable
    enough (ZM uses 1-second resolution; HA's access_token rotates only
    every few minutes) that the browser serves a stale image when an
    async partial-DOM update revisits the same camera."""
    if not url:
        return url
    sep = '&' if '?' in url else '?'
    return f'{url}{sep}_cb={time.time_ns()}'


@register.simple_tag
def entity_video_snapshot(entity):
    """Get the current still-image snapshot for an entity, if available.

    Returns a ``VideoSnapshot`` (with ``source_url``) or ``None``.
    Parallel to ``entity_video_stream`` but for the snapshot capability.
    """
    if not entity:
        return None

    try:
        gateway = IntegrationManager().get_integration_gateway(entity.integration_id)
        if not gateway:
            logger.warning(f"No integration gateway found for {entity.integration_id}")
            return None
        connector = gateway.get_connector()
        if connector is None:
            return None
        return connector.get_entity_video_snapshot(entity)
    except Exception as e:
        logger.error(f"Error getting video snapshot for entity {entity.id}: {e}")
        return None
