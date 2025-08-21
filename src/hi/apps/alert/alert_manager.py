from datetime import datetime
import logging

from hi.apps.common.singleton import Singleton
from hi.apps.console.console_helper import ConsoleSettingsHelper
from hi.apps.console.transient_view_manager import TransientViewManager
from hi.apps.security.security_mixins import SecurityMixin
from hi.apps.notify.notify_mixins import NotificationMixin

from .alert import Alert
from .alert_queue import AlertQueue
from .alarm import Alarm
from .alert_status import AlertStatusData
from .enums import AlarmSource

logger = logging.getLogger(__name__)


class AlertManager( Singleton, NotificationMixin, SecurityMixin ):

    def __init_singleton__(self):
        self._alert_queue = AlertQueue()
        self._was_initialized = False
        return

    def ensure_initialized(self):
        if self._was_initialized:
            return
        # Any future heavyweight initializations go here (e.g., any DB operations).
        self._was_initialized = True
        return

    @property
    def unacknowledged_alert_list(self):
        return self._alert_queue.unacknowledged_alert_list

    def get_alert( self, alert_id : str ) -> Alert:
        return self._alert_queue.get_alert( alert_id = alert_id )

    def get_alert_status_data( self, last_alert_status_datetime : datetime ) -> AlertStatusData:
        
        # Things to check on alert status:
        #
        #   1) Has the alert list changed in any way? If so, return new HTML
        #      Note that the alert list could be empty, but still could be
        #      different from last time.
        #
        #   2) Has a new alert been added?  If so, tell the client so it
        #      can signal the user (audible).
        #
        #   3) What is the most critical alert in the list?  This is sent
        #      to the client so it can periodically re-notify that there are
        #      unacknowledged events.
        #
        # Because the alerts display their age, we always return the html
        # for the alert list if it is not empty so those ages can refresh
        # in the view. Also, we return it if it has changed, which include
        # it having become empty.
        
        new_alert = self._alert_queue.get_most_important_unacknowledged_alert(
            since_datetime = last_alert_status_datetime,
        )
        logger.debug(f"🔍 new_alert from queue: {new_alert}")
        
        if new_alert:
            max_alert = new_alert
        else:
            max_alert = self._alert_queue.get_most_important_unacknowledged_alert()
        
        logger.debug(f"🔍 max_alert from queue: {max_alert}")

        # Check for auto-view switching based on recent alarms
        recent_alarm = self._alert_queue.get_most_recent_alarm(
            since_datetime = last_alert_status_datetime,
        )
        
        if recent_alarm and self._should_suggest_auto_view(recent_alarm):
            camera_url = self._get_camera_url_for_alarm(recent_alarm)
            if camera_url:
                console_helper = ConsoleSettingsHelper()
                duration_seconds = console_helper.get_auto_view_duration()
                
                TransientViewManager().suggest_view_change(
                    url=camera_url,
                    duration_seconds=duration_seconds,
                    priority=recent_alarm.alarm_level.priority,
                    trigger_reason=f"{recent_alarm.alarm_type}_alarm"
                )
        
        return AlertStatusData(
            alert_list = self._alert_queue.unacknowledged_alert_list,
            max_audio_signal = max_alert.audio_signal if max_alert else None,
            new_audio_signal = new_alert.audio_signal if new_alert else None,
        )

    def acknowledge_alert( self, alert_id : str ):
        self._alert_queue.acknowledge_alert( alert_id = alert_id )
        return
    
    async def add_alarm( self, alarm : Alarm ):
        notification_manager = await self.notification_manager_async()
        if not notification_manager:
            return
        logging.debug( f'Adding Alarm: {alarm}' )
        security_state = self.security_manager().security_state
        try:
            alert = self._alert_queue.add_alarm( alarm = alarm )
            if security_state.uses_notifications and alert.has_single_alarm:
                notification_manager.add_notification_item(
                    notification_item = alert.to_notification_item(),
                )
        except ValueError as ve:
            logging.info( str(ve) )
        except Exception as e:
            logger.exception( 'Problem adding alarm to alert queue.', e )
        return
    
    async def do_periodic_maintenance(self):
        try:
            self._alert_queue.remove_expired_or_acknowledged_alerts()
        except Exception as e:
            logger.exception( 'Problem doing periodic alert maintenance.', e )
        return

    def _should_suggest_auto_view(self, alarm: Alarm) -> bool:
        """
        Determine if alarm should trigger auto-view suggestion.
        Currently handles EVENT alarms, extensible for WEATHER and other types.
        """
        console_helper = ConsoleSettingsHelper()
        
        # Check if auto-view is enabled
        if not console_helper.get_auto_view_enabled():
            return False
        
        # Currently only handle EVENT alarms (motion detection, etc.)
        # TODO: Add WEATHER alarm handling (tornado warnings → weather radar)
        # TODO: Add CONSOLE alarm handling if needed
        if alarm.alarm_source != AlarmSource.EVENT:
            return False
        
        # For EVENT alarms, check if it's a type we can handle
        # TODO: Expand this as we identify more alarm types that should trigger auto-view
        motion_related_types = ['motion', 'movement', 'detection']
        alarm_type_lower = alarm.alarm_type.lower()
        
        return any(motion_type in alarm_type_lower for motion_type in motion_related_types)

    def _get_camera_url_for_alarm(self, alarm: Alarm) -> str:
        """
        Get camera URL associated with the alarm's location/entity.
        Returns None if no associated camera view can be determined.
        """
        # For EVENT alarms, try to find associated camera/sensor
        if alarm.alarm_source == AlarmSource.EVENT:
            return self._get_camera_url_for_event_alarm(alarm)
        
        # TODO: Add handlers for other alarm sources
        # elif alarm.alarm_source == AlarmSource.WEATHER:
        #     return self._get_weather_url_for_weather_alarm(alarm)
        
        return None

    def _get_camera_url_for_event_alarm(self, alarm: Alarm) -> str:
        """
        Extract camera URL from EVENT alarm source details.
        This is the initial implementation - may need refinement based on 
        actual alarm source_details structure.
        """
        # Look through source_details_list for sensor/entity information
        for source_details in alarm.source_details_list:
            detail_attrs = source_details.detail_attrs
            
            # Try to find sensor_id in the detail attributes
            sensor_id = detail_attrs.get('sensor_id')
            if sensor_id:
                try:
                    # Construct camera URL using the same pattern as camera controls
                    from django.urls import reverse
                    return reverse('console_sensor_video_stream', kwargs={'sensor_id': sensor_id})
                except Exception as e:
                    logger.warning(f"Could not construct camera URL for sensor_id {sensor_id}: {e}")
            
            # Try other possible keys that might contain sensor/entity information
            entity_id = detail_attrs.get('entity_id')
            if entity_id:
                # TODO: Implement entity_id → sensor_id mapping if needed
                logger.debug(f"Found entity_id {entity_id} but no direct mapping to camera URL yet")
        
        logger.debug(f"No camera URL found for alarm: {alarm.alarm_type}")
        return None
