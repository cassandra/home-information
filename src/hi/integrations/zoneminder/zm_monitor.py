from cachetools import TTLCache
import logging

import hi.apps.common.datetimeproxy as datetimeproxy
from hi.apps.monitor.periodic_monitor import PeriodicMonitor
from hi.apps.sense.enums import SensorValue
from hi.apps.sense.sensor_history_manager import SensorHistoryManager
from hi.apps.sense.sensor_response_manager import SensorResponseManager
from hi.apps.sense.transient_models import SensorResponse

from .zm_models import ZmEvent
from .zm_manager import ZoneMinderManager

logger = logging.getLogger(__name__)


class ZoneMinderMonitor( PeriodicMonitor ):

    # TODO: Move this into the integrations attributes for users to set
    ZONEMINDER_SERVER_TIMEZONE = 'America/Chicago'
    
    def __init__( self ):
        super().__init__(
            id = 'zm-monitor',
            interval_secs = 10,
        )
        self._zm_manager = ZoneMinderManager()
        self._sensor_history_manager = SensorHistoryManager()
        self._sensor_response_manager = SensorResponseManager()
        self._fully_processed_event_ids = TTLCache( maxsize = 1000, ttl = 100000 )
        self._start_processed_event_ids = TTLCache( maxsize = 1000, ttl = 100000 )

        # pyzm parses the "from" time as a naive time and applies thje
        # timezone separately. It will parse an ISO time with a timezone,
        # but ignores it ignores its encoded timezone.  Thus, it is
        # important that we have this in the same TZ as the ZoneMinder
        # server and also pass in the TZ when filtering events.
        #
        self._poll_from_datetime = datetimeproxy.now( self.ZONEMINDER_SERVER_TIMEZONE )
        return

    async def do_work(self):
        options = {
            'from': self._poll_from_datetime.isoformat(),  # This "from" only looks at event start time
            'tz': self.ZONEMINDER_SERVER_TIMEZONE,
        }
        response = self._zm_manager.zm_client.events( options )
        events = response.list()
        if self.TRACE:
            logger.debug( f"Found {len(events)} new ZM events" )

        # Sensor readings and state value transitions are points in time,
        # but ZoneMinder events are intervals.  Thus, one ZoneMinder event
        # really represents two sensor reading: one when the event (motion)
        # started and one when it ended.
        #
        # However, we may be seeing a ZM event in progress where there is
        # no end time (a.k.a., an "open" event). Open events are trickier
        # since we need to make sure that future polling will also pick up
        # these events so we can know when they become closed.  However,
        # needing to see the same event more than once during polling means
        # there is a risk of double counting.  The tension this creates
        # is what complicated the logic here.
        
        # First collate events into open and closed.
        #
        open_zm_event_list = list()
        closed_zm_event_list = list()
        for zm_api_event in events:
            if self.TRACE:
                logger.debug( f'ZM Api Event: {zm_api_event.get()}' )
            zm_event = ZmEvent( zm_api_event = zm_api_event,
                                zm_tzname = self.ZONEMINDER_SERVER_TIMEZONE )

            if zm_event.event_id in self._fully_processed_event_ids:
                continue
            
            if zm_event.is_open:
                open_zm_event_list.append( zm_event )
            else:
                closed_zm_event_list.append( zm_event )
            continue

        sensor_response_history_list = list()
        sensor_response_latest_list = list()

        for zm_event in closed_zm_event_list:
            if zm_event.event_id not in self._start_processed_event_ids:
                active_sensor_response = self._create_movement_active_sensor_response( zm_event )
                sensor_response_history_list.append( active_sensor_response )
                
            idle_sensor_response = self._create_movement_idle_sensor_response( zm_event )
            sensor_response_history_list.append( idle_sensor_response )
            sensor_response_latest_list.append( idle_sensor_response )
            self._fully_processed_event_ids[zm_event.event_id] = True
            continue
        
        for zm_event in open_zm_event_list:
            if zm_event.event_id not in self._start_processed_event_ids:
                active_sensor_response = self._create_movement_active_sensor_response( zm_event )
                sensor_response_latest_list.append( active_sensor_response )
                self._start_processed_event_ids[zm_event.event_id] = True
            continue

        self._sensor_history_manager.add_to_sensor_response_history(
            sensor_response_list = sensor_response_history_list,
        )
        self._sensor_response_manager.add_latest_sensor_responses(
            sensor_response_list = sensor_response_latest_list,
        )

        if open_zm_event_list:
            # Ensure that we will continue to poll for all the open events we
            # currently see.
            #
            open_zm_event_list.sort( key = lambda zm_event : zm_event.start_datetime )
            self._poll_from_datetime = open_zm_event_list[0].start_datetime

        elif closed_zm_event_list:
            # Maximum end time from ZM server (via events) ensures there are no
            # events starting earlier than this time that we will not have
            # already seen.
            #
            closed_zm_event_list.sort( key = lambda zm_event : zm_event.end_datetime )
            self._poll_from_datetime = closed_zm_event_list[-1].end_datetime
            
        else:
            # N.B. When there are no events, we do not advance the polling
            # base time. We do not know whether an event might have started
            # right after this poll attempt. Thus, any attempt to increment
            # the polling base time would risk missing an event that
            # started in less than that chosen increment.
            #
            pass
        
        return

    def _create_movement_active_sensor_response( self, zm_event : ZmEvent ):
        return SensorResponse(
            integration_key = self._zm_manager._sensor_to_integration_key(
                sensor_prefix = self._zm_manager.MOVEMENT_SENSOR_PREFIX,
                zm_monitor_id = zm_event.monitor_id,
            ),
            value = str(SensorValue.MOVEMENT_ACTIVE),
            timestamp = zm_event.start_datetime,
        )

    def _create_movement_idle_sensor_response( self, zm_event : ZmEvent ):
        return SensorResponse(
            integration_key = self._zm_manager._sensor_to_integration_key(
                sensor_prefix = self._zm_manager.MOVEMENT_SENSOR_PREFIX,
                zm_monitor_id = zm_event.monitor_id,
            ),
            value = str(SensorValue.MOVEMENT_IDLE),
            timestamp = zm_event.end_datetime,
        )
