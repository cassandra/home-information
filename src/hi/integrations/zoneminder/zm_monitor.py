from datetime import datetime, timedelta
import logging

import hi.apps.common.datetimeproxy as datetimeproxy
from hi.apps.monitor.periodic_monitor import PeriodicMonitor
from hi.apps.monitor.monitor_mixin import SensorMonitorMixin
from hi.apps.monitor.transient_models import SensorResponse
from hi.apps.sense.enums import SensorValue

from .zm_manager import ZoneMinderManager

logger = logging.getLogger(__name__)


class ZoneMinderMonitor( PeriodicMonitor, SensorMonitorMixin ):

    # TODO: MOve this into the integrations attributes for users to setAllCameraStatus
    ZONEMINDER_SERVER_TIMEZONE = 'America/Chicago'
    
    def __init__( self ):
        super().__init__(
            id = 'zm-monitor',
            interval_secs = 10,
        )
        self._manager = ZoneMinderManager()
        self._last_event_datetime = datetimeproxy.now( self.ZONEMINDER_SERVER_TIMEZONE )
        return

    async def do_work(self):
        options = {
            'from': self._last_event_datetime.isoformat(),
            'tz': self.ZONEMINDER_SERVER_TIMEZONE,
        }



        
        print( f'FROM: {options}' )



            
        response = self._manager.zm_client.events( options )
        events = response.list()
        if self.TRACE:
            logger.debug( f"Found {len(events)} new ZM events" )

        sensor_response_list = list()
        for zm_event in events:
            if self.TRACE:
                logger.debug( f'ZM Event: {zm_event.get()}' )

            event_id = zm_event.id()
            monitor_id = zm_event.monitor_id()
            # Currently unused values:
            #
            # event_image_url = '{}/index.php?view=image&eid={}&fid=snapshot'.format(
            #     self._manager.zm_client.get_portalbase(),
            #     event_id,
            # )
            # event_cause = zm_event.cause()
            # event_duration_secs = zm_event.duration()
            # total_frame_count = zm_event.total_frames()
            # alarm_frame_count = zm_event.alarmed_frames()
            # score = zm_event.score()
            # notes = zm_event.notes()
            # max_score_frame_id = zm_event.get()['MaxScoreFrameId']
            
            event_video_url = '{}/index.php?view=event&eid={}'.format(
                self._manager.zm_client.get_portalbase(),
                event_id,
            )
            stream_response = SensorResponse(
                integration_key = self._manager._sensor_to_integration_key(
                    sensor_prefix = self._manager.VIDEO_STREAM_SENSOR_PREFIX,
                    zm_monitor_id = monitor_id,
                ),
                timestamp = self._last_event_datetime,
                value = event_video_url,
            )
            sensor_response_list.append( stream_response )

            start_datetime = self.zm_response_to_datetime( zm_event.get()['StartTime'] )
            event_start_response = SensorResponse(
                integration_key = self._manager._sensor_to_integration_key(
                    sensor_prefix = self._manager.MOVEMENT_SENSOR_PREFIX,
                    zm_monitor_id = monitor_id,
                ),
                value = str(SensorValue.MOVEMENT_ACTIVE),
                timestamp = start_datetime,
            )
            sensor_response_list.append( event_start_response )



            #self.add_to_sensor_response_history( event_start_response )



            
            end_datetime = self.zm_response_to_datetime( zm_event.get()['EndTime'] )
            if end_datetime:
                event_end_response = SensorResponse(
                    integration_key = self._manager._sensor_to_integration_key(
                        sensor_prefix = self._manager.MOVEMENT_SENSOR_PREFIX,
                        zm_monitor_id = monitor_id,
                    ),
                    value = str(SensorValue.MOVEMENT_IDLE),
                    timestamp = end_datetime,
                )
                sensor_response_list.append( event_end_response )

                
                # self.add_to_sensor_response_history( event_end_response )


                
            self._last_event_datetime = max( self._last_event_datetime, start_datetime )
            continue

        return

    def zm_response_to_datetime( self, zm_response_time : str ):
        if not zm_response_time:
            return None
        return datetimeproxy.iso_naive_to_datetime_utc(
            zm_response_time,
            self.ZONEMINDER_SERVER_TIMEZONE,
        )
    
