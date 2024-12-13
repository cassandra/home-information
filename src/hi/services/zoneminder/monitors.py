from asgiref.sync import sync_to_async
from cachetools import TTLCache
from datetime import datetime
import logging
from pyzm.helpers.Monitor import Monitor as ZmMonitor

import hi.apps.common.datetimeproxy as datetimeproxy
from hi.apps.entity.enums import EntityStateValue
from hi.apps.monitor.periodic_monitor import PeriodicMonitor
from hi.apps.sense.sensor_response_manager import SensorResponseMixin
from hi.apps.sense.transient_models import SensorResponse

from .zm_models import ZmEvent
from .zm_manager import ZoneMinderManager
from .zm_mixins import ZoneMinderMixin

logger = logging.getLogger(__name__)


class ZoneMinderMonitor( PeriodicMonitor, ZoneMinderMixin, SensorResponseMixin ):

    # TODO: Move this into the integrations attributes for users to set
    ZONEMINDER_SERVER_TIMEZONE = 'America/Chicago'
    ZONEMINDER_POLLING_INTERVAL_SECS = 10
    
    def __init__( self ):
        super().__init__(
            id = 'zm-monitor',
            interval_secs = self.ZONEMINDER_POLLING_INTERVAL_SECS,
        )
        self._fully_processed_event_ids = TTLCache( maxsize = 1000, ttl = 100000 )
        self._start_processed_event_ids = TTLCache( maxsize = 1000, ttl = 100000 )
        self._zm_tzname = None

        # pyzm parses the "from" time as a naive time and applies the
        # timezone separately. It will parse an ISO time with a timezone,
        # but ignores it ignores its encoded timezone.  Thus, it is
        # important that we have this in the same TZ as the ZoneMinder
        # server and also pass in the TZ when filtering events.
        #
        self._poll_from_datetime = None
        self._was_initialized = False
        return

    async def _initialized(self):
        zm_manager = await self.zm_manager_async()
        _ = await self.sensor_response_manager_async()  # Allows async use of self.sensor_response_manager()
        self._zm_tzname = await sync_to_async( zm_manager.get_zm_tzname )()
        self._poll_from_datetime = datetimeproxy.now( self._zm_tzname )
        zm_manager.register_change_listener( self.refresh )
        self._was_initialized = True
        return
    
    def refresh( self ):
        """ Should be called when integration settings are changed. """
        new_tzname = self.zm_manager().get_zm_tzname()
        if new_tzname == self._zm_tzname:
            return

        logger.info( f'Refreshing ZoneMinder monitor timezone: {self._zm_tzname} -> {new_tzname}' )
        self._poll_from_datetime = datetimeproxy.change_timezone(
            original_datetime = self._poll_from_datetime,
            new_tzname = new_tzname,
        )
        self._zm_tzname = new_tzname
        return

    async def do_work(self):
        if not self._was_initialized:
            await self._initialized()
        
        sensor_response_map = dict()
        sensor_response_map.update( await self._process_events( ) )
        sensor_response_map.update( self._process_monitors() )
        sensor_response_map.update( self._process_states() )

        await self.sensor_response_manager().update_with_latest_sensor_responses(
            sensor_response_map = sensor_response_map,
        )
        return
    
    async def _process_events(self):
        current_poll_datetime = datetimeproxy.now()
        options = {
            'from': self._poll_from_datetime.isoformat(),  # This "from" only looks at event start time
            'tz': self._zm_tzname,
        }
        events = self.zm_manager().get_zm_events( options = options )
        if self.TRACE:
            logger.debug( f'Found {len(events)} new ZM events' )

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
        zm_monitor_ids_seen = set()
        for zm_api_event in events:
            if self.TRACE:
                logger.debug( f'ZM Api Event: {zm_api_event.get()}' )
            zm_event = ZmEvent( zm_api_event = zm_api_event,
                                zm_tzname = self._zm_tzname )

            if zm_event.event_id in self._fully_processed_event_ids:
                continue

            zm_monitor_ids_seen.add( zm_event.monitor_id )
            if zm_event.is_open:
                open_zm_event_list.append( zm_event )
            else:
                closed_zm_event_list.append( zm_event )
            continue

        sensor_response_map = dict()

        for zm_event in open_zm_event_list:
            if zm_event.event_id not in self._start_processed_event_ids:
                active_sensor_response = self._create_movement_active_sensor_response( zm_event )
                sensor_response_map[active_sensor_response.integration_key] = active_sensor_response
                self._start_processed_event_ids[zm_event.event_id] = True
            continue
        
        for zm_event in closed_zm_event_list:
            if zm_event.event_id not in self._start_processed_event_ids:
                active_sensor_response = self._create_movement_active_sensor_response( zm_event )
                sensor_response_map[active_sensor_response.integration_key] = active_sensor_response
                
            idle_sensor_response = self._create_movement_idle_sensor_response( zm_event )
            sensor_response_map[idle_sensor_response.integration_key] = idle_sensor_response
            self._fully_processed_event_ids[zm_event.event_id] = True
            continue

        # If there are no events for monitors/states, we still want to emit the
        # sensor response of it being idle.
        #
        for zm_monitor in self.zm_manager().get_zm_monitors():
            if zm_monitor.id() not in zm_monitor_ids_seen:
                idle_sensor_response = self._create_idle_sensor_response(
                    zm_monitor = zm_monitor,
                    timestamp = current_poll_datetime,
                )
                sensor_response_map[idle_sensor_response.integration_key] = idle_sensor_response
            continue
        
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
        
        return sensor_response_map

    def _process_monitors(self):
        current_poll_datetime = datetimeproxy.now()
        sensor_response_map = dict()

        for zm_monitor in self.zm_manager().get_zm_monitors():

            video_stream_sensor_response = self._create_video_stream_sensor_response(
                zm_monitor = zm_monitor,
                timestamp = current_poll_datetime,
            )
            sensor_response_map[video_stream_sensor_response.integration_key] = video_stream_sensor_response
            
            function_sensor_response = self._create_monitor_function_sensor_response(
                zm_monitor = zm_monitor,
                timestamp = current_poll_datetime,
            )
            sensor_response_map[function_sensor_response.integration_key] = function_sensor_response
            continue
        
        return sensor_response_map
    
    def _process_states(self):
        current_poll_datetime = datetimeproxy.now()
        sensor_response_map = dict()

        active_run_state_name = None
        for zm_state in self.zm_manager().get_zm_states():
            if zm_state.active():
                active_run_state_name = zm_state.name()
                break
            continue

        if active_run_state_name:
            run_state_sensor_response = self._create_run_state_sensor_response(
                run_state_name = active_run_state_name,
                timestamp = current_poll_datetime,
            )
            sensor_response_map[run_state_sensor_response.integration_key] = run_state_sensor_response
        
        return sensor_response_map
      
    def _create_movement_active_sensor_response( self, zm_event : ZmEvent ):
        return SensorResponse(
            integration_key = self.zm_manager()._to_integration_key(
                prefix = ZoneMinderManager.MOVEMENT_SENSOR_PREFIX,
                zm_monitor_id = zm_event.monitor_id,
            ),
            value = str(EntityStateValue.ACTIVE),
            timestamp = zm_event.start_datetime,
            detail_attrs = zm_event.to_detail_attrs(),
            image_url = self.zm_manager().get_event_video_stream_url( event_id = zm_event.event_id ),
        )

    def _create_movement_idle_sensor_response( self, zm_event : ZmEvent ):
        return SensorResponse(
            integration_key = self.zm_manager()._to_integration_key(
                prefix = ZoneMinderManager.MOVEMENT_SENSOR_PREFIX,
                zm_monitor_id = zm_event.monitor_id,
            ),
            value = str(EntityStateValue.IDLE),
            timestamp = zm_event.end_datetime,
        )

    def _create_idle_sensor_response( self, zm_monitor : ZmMonitor, timestamp : datetime ):
        return SensorResponse(
            integration_key = self.zm_manager()._to_integration_key(
                prefix = ZoneMinderManager.MOVEMENT_SENSOR_PREFIX,
                zm_monitor_id = zm_monitor.id(),
            ),
            value = str(EntityStateValue.IDLE),
            timestamp = timestamp,
        )

    def _create_video_stream_sensor_response( self, zm_monitor : ZmMonitor, timestamp : datetime ):
        return SensorResponse(
            integration_key = self.zm_manager()._to_integration_key(
                prefix = ZoneMinderManager.VIDEO_STREAM_SENSOR_PREFIX,
                zm_monitor_id = zm_monitor.id(),
            ),
            value = self.zm_manager().get_video_stream_url( monitor_id = zm_monitor.id() ),
            timestamp = timestamp,
        )

    def _create_monitor_function_sensor_response( self, zm_monitor : ZmMonitor, timestamp : datetime ):
        
        return SensorResponse(
            integration_key = self.zm_manager()._to_integration_key(
                prefix = ZoneMinderManager.MONITOR_FUNCTION_SENSOR_PREFIX,
                zm_monitor_id = zm_monitor.id(),
            ),
            value = str( zm_monitor.function() ),
            timestamp = timestamp,
        )

    def _create_run_state_sensor_response( self, run_state_name : str, timestamp : datetime ):
        return SensorResponse(
            integration_key = self.zm_manager()._zm_run_state_integration_key(),
            value = run_state_name,
            timestamp = timestamp,
        )
    
