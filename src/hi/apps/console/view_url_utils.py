import logging
from typing import Optional

from django.urls import reverse

from hi.apps.sense.models import Sensor
from hi.apps.entity.enums import EntityStateType

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
        # Look through all source details for sensor information
        for source_details in alarm.source_details_list:
            if source_details.sensor_id:
                view_url = ViewUrlUtils._get_view_url_for_sensor_id(source_details.sensor_id)
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
            # Look up the sensor
            sensor = Sensor.objects.select_related('entity_state').get(id=sensor_id)
            
            # Check if this sensor's entity has a video stream
            if ViewUrlUtils._sensor_has_video_stream(sensor):
                return reverse('console_sensor_video_stream', kwargs={'sensor_id': sensor_id})
            
            # Future: Add other view types based on entity state type
            # elif sensor.entity_state.entity_state_type == EntityStateType.WEATHER:
            #     return reverse('console_weather_view', kwargs={'sensor_id': sensor_id})
            
            logger.debug(f"Sensor {sensor_id} ({sensor.entity_state.entity_state_type}) "
                        f"does not have an associated view")
            return None
            
        except Sensor.DoesNotExist:
            logger.warning(f"Sensor {sensor_id} not found")
            return None
        except Exception as e:
            logger.warning(f"Could not generate view URL for sensor {sensor_id}: {e}")
            return None
    
    @staticmethod
    def _sensor_has_video_stream(sensor: Sensor) -> bool:
        """
        Determine if the given sensor is associated with a video stream.
        
        This checks if the sensor's entity has other sensors that provide
        video stream functionality.
        
        Args:
            sensor: The Sensor object to check
            
        Returns:
            True if the sensor's entity has video stream capability
        """
        # Check if the same entity has a video stream sensor
        entity = sensor.entity_state.entity
        
        # Look for other sensors on the same entity that provide video streams
        video_stream_sensors = entity.states.filter(
            entity_state_type_str=str(EntityStateType.VIDEO_STREAM)
        ).exists()
        
        return video_stream_sensors