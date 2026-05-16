import logging
from django import template

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
    if not sensor_response or not sensor_response.has_video_stream:
        return None

    try:
        # Get the entity from the sensor response
        if not sensor_response.sensor:
            logger.debug("SensorResponse has no associated sensor")
            return None

        entity = sensor_response.sensor.entity_state.entity

        # Get integration gateway for this entity
        from hi.integrations.integration_manager import IntegrationManager
        integration_manager = IntegrationManager()
        gateway = integration_manager.get_integration_gateway(entity.integration_id)

        if not gateway:
            logger.warning(f"No integration gateway found for {entity.integration_id}")
            return None

        # Get recorded video stream from sensor response
        video_stream = gateway.get_sensor_response_video_stream(sensor_response)

        if video_stream:
            return video_stream

        logger.debug("No video stream available for sensor response")
        return None

    except Exception as e:
        logger.error(f"Error getting video stream for sensor response: {e}")
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
        # The gateway returns None for entities that don't have a
        # native stream, so no need to gate on ``has_video_stream``
        # here. The user-facing gate lives at the template level via
        # ``has_live_view`` so snapshot-only entities can also render
        # through the central live-view include.
        from hi.integrations.integration_manager import IntegrationManager
        integration_manager = IntegrationManager()
        gateway = integration_manager.get_integration_gateway(entity.integration_id)

        if not gateway:
            logger.warning(f"No integration gateway found for {entity.integration_id}")
            return None

        video_stream = gateway.get_entity_video_stream(entity)

        if video_stream:
            return video_stream

        logger.debug(f"No video stream available for entity {entity.id}")
        return None

    except Exception as e:
        logger.error(f"Error getting video stream for entity {entity.id}: {e}")
        return None


@register.simple_tag
def entity_video_snapshot(entity):
    """Get the current still-image snapshot for an entity, if available.

    Returns a ``VideoSnapshot`` (with ``source_url``) or ``None``.
    Parallel to ``entity_video_stream`` but for the snapshot capability.
    """
    if not entity:
        return None

    try:
        from hi.integrations.integration_manager import IntegrationManager
        gateway = IntegrationManager().get_integration_gateway(entity.integration_id)
        if not gateway:
            logger.warning(f"No integration gateway found for {entity.integration_id}")
            return None
        return gateway.get_entity_video_snapshot(entity)
    except Exception as e:
        logger.error(f"Error getting video snapshot for entity {entity.id}: {e}")
        return None
