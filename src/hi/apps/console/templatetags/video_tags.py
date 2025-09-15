import logging
from django import template

from hi.apps.common.utils import get_humanized_secs

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
        # Check if entity has video stream capability
        if not entity.has_video_stream:
            logger.debug(f"Entity {entity.id} does not have video stream capability")
            return None

        # Get integration gateway for this entity
        from hi.integrations.integration_manager import IntegrationManager
        integration_manager = IntegrationManager()
        gateway = integration_manager.get_integration_gateway(entity.integration_id)

        if not gateway:
            logger.warning(f"No integration gateway found for {entity.integration_id}")
            return None
            
        # Get live video stream
        video_stream = gateway.get_entity_video_stream(entity)

        if video_stream:
            return video_stream

        logger.debug(f"No video stream available for entity {entity.id}")
        return None
        
    except Exception as e:
        logger.error(f"Error getting video stream for entity {entity.id}: {e}")
        return None


@register.filter
def format_duration(duration_secs):
    """
    Format duration in seconds to a human-readable format using existing utility.

    Args:
        duration_secs: Duration in seconds (int or float)

    Returns:
        Formatted duration string using get_humanized_secs
    """
    if duration_secs is None:
        return ""

    try:
        return get_humanized_secs(duration_secs)
    except (ValueError, TypeError):
        return ""


