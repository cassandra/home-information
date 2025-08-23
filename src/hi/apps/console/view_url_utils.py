import logging
from typing import Optional

from django.urls import reverse

from hi.apps.sense.models import Sensor

logger = logging.getLogger(__name__)


class ViewUrlUtils:
    """
    Utility class for generating view URLs based on alarm/sensor data.
    
    This utility encapsulates the logic for determining what view should be shown
    for a given alarm, taking into account the sensor types, entity relationships,
    and available views in the system.
    """
    
    @staticmethod
    def get_view_url_for_alarm(alarm) -> Optional[str]:
        """
        Generate a view URL for the given alarm.
        
        This method examines the alarm's source details to find sensor information
        and determines the most appropriate view URL based on the sensor's
        associated entity state types.
        
        Args:
            alarm: The Alarm object to generate a view URL for
            
        Returns:
            A Django view URL string, or None if no appropriate view can be determined
        """
        # Look through all source details (SensorResponse objects) for sensor information
        for sensor_response in alarm.source_details_list:
            if sensor_response.sensor and sensor_response.sensor.id:
                view_url = ViewUrlUtils._get_view_url_for_sensor_id(sensor_response.sensor.id)
                if view_url:
                    return view_url
        
        logger.debug(f"No view URL found for alarm: {alarm.alarm_type} from {alarm.alarm_source}")
        return None
    
    @staticmethod
    def _get_view_url_for_sensor_id(sensor_id: str) -> Optional[str]:
        """
        Generate a view URL for the given sensor ID.
        
        This method looks up the sensor and examines its entity state to determine
        what type of view is appropriate.
        
        Args:
            sensor_id: The ID of the sensor
            
        Returns:
            A Django view URL string, or None if no appropriate view found
        """
        try:
            # Look up the sensor and its entity
            sensor = Sensor.objects.select_related('entity_state__entity').get(id=sensor_id)
            entity = sensor.entity_state.entity
            
            # Check if entity has video stream capability (Phase 4 approach)
            if entity.has_video_stream:
                # Generate entity-based video stream URL for live video feed
                return reverse('console_entity_video_stream', kwargs={'entity_id': entity.id})
            
            # Future: Add other view types based on entity state type
            # elif sensor.entity_state.entity_state_type == EntityStateType.WEATHER:
            #     return reverse('console_weather_view', kwargs={'sensor_id': sensor_id})
            
            logger.debug(f"Entity {entity.id} for sensor {sensor_id} does not have video stream capability")
            return None
            
        except Sensor.DoesNotExist:
            logger.warning(f"Sensor {sensor_id} not found")
            return None
        except Exception as e:
            logger.warning(f"Could not generate view URL for sensor {sensor_id}: {e}")
            return None
    
