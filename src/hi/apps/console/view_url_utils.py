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
            
            # Find the video stream sensor for this entity
            video_stream_sensor = ViewUrlUtils._get_video_stream_sensor(sensor)
            if video_stream_sensor:
                # Use the video stream sensor's ID, not the original sensor's ID
                return reverse('console_sensor_video_stream', kwargs={'sensor_id': video_stream_sensor.id})
            
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
    def _get_video_stream_sensor(sensor: Sensor) -> Optional[Sensor]:
        """
        Get the video stream sensor associated with the given sensor's entity.
        
        This finds the video stream sensor that belongs to the same entity
        as the given sensor (e.g., finding the video stream sensor when
        given a motion detection sensor from the same camera entity).
        
        Args:
            sensor: The Sensor object to check
            
        Returns:
            The video stream Sensor if one exists, None otherwise
        """
        # Get the entity this sensor belongs to
        entity = sensor.entity_state.entity
        
        # Look for video stream entity states on the same entity
        video_stream_states = entity.states.filter(
            entity_state_type_str=str(EntityStateType.VIDEO_STREAM)
        ).prefetch_related('sensors')
        
        # Return the first video stream sensor found
        for state in video_stream_states:
            sensors = state.sensors.all()
            if sensors:
                return sensors.first()
        
        return None
