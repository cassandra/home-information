import logging
from django import template

logger = logging.getLogger(__name__)

register = template.Library()


@register.simple_tag
def sensor_response_video_stream(sensor_response):
    """
    Get recorded video stream URL for a SensorResponse.
    
    Args:
        sensor_response: SensorResponse object
        
    Returns:
        Video stream URL string or empty string if no video available
    """
    if not sensor_response or not sensor_response.has_video_stream:
        return ""
        
    try:
        # Get the entity from the sensor response
        if not sensor_response.sensor:
            logger.debug("SensorResponse has no associated sensor")
            return ""
            
        entity = sensor_response.sensor.entity_state.entity
        
        # Get integration gateway for this entity
        from hi.integrations.integration_manager import IntegrationManager
        integration_manager = IntegrationManager()
        gateway = integration_manager.get_integration_gateway(entity.integration_id)
        
        if not gateway:
            logger.warning(f"No integration gateway found for {entity.integration_id}")
            return ""
            
        # Get recorded video stream from sensor response
        video_stream = gateway.get_sensor_response_video_stream(sensor_response)
        
        if video_stream and video_stream.source_url:
            return video_stream.source_url
            
        logger.debug("No video stream available for sensor response")
        return ""
        
    except Exception as e:
        logger.error(f"Error getting video URL for sensor response: {e}")
        return ""


@register.simple_tag
def entity_video_stream(entity):
    """
    Get entity live video stream URL for a entity object.
    
    Args:
        entity: Entity object
        
    Returns:
        Video stream URL string or empty string if no video available
    """
    if not entity:
        return ""
        
    try:
        # Check if entity has video stream capability
        if not entity.has_video_stream:
            logger.debug(f"Entity {entity.id} does not have video stream capability")
            return ""
            
        # Get integration gateway for this entity
        from hi.integrations.integration_manager import IntegrationManager
        integration_manager = IntegrationManager()
        gateway = integration_manager.get_integration_gateway(entity.integration_id)
        
        if not gateway:
            logger.warning(f"No integration gateway found for {entity.integration_id}")
            return ""
            
        # Get live video stream
        video_stream = gateway.get_entity_video_stream(entity)
        
        if video_stream and video_stream.source_url:
            return video_stream.source_url
            
        logger.debug(f"No video stream available for entity {entity.id}")
        return ""
        
    except Exception as e:
        logger.error(f"Error getting video URL for entity {entity.id}: {e}")
        return ""
