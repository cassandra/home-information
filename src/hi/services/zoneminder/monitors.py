from cachetools import TTLCache
from datetime import datetime
import logging
from .pyzm_client.helpers.Monitor import Monitor as ZmMonitor

import hi.apps.common.datetimeproxy as datetimeproxy
from hi.apps.entity.enums import EntityStateValue
from hi.apps.monitor.periodic_monitor import PeriodicMonitor
from hi.apps.sense.sensor_response_manager import SensorResponseMixin
from hi.apps.sense.transient_models import SensorResponse
from hi.apps.sense.enums import CorrelationRole

from .constants import ZmDetailKeys, ZmTimeouts
from .zm_models import ZmEvent, AggregatedMonitorState
from .zm_manager import ZoneMinderManager
from .zm_mixins import ZoneMinderMixin

logger = logging.getLogger(__name__)


class ZoneMinderMonitor( PeriodicMonitor, ZoneMinderMixin, SensorResponseMixin ):

    # TODO: Move this into the integrations attributes for users to set
    ZONEMINDER_SERVER_TIMEZONE = 'America/Chicago'

    # Use centralized timeout constants
    ZONEMINDER_POLLING_INTERVAL_SECS = ZmTimeouts.POLLING_INTERVAL_SECS
    ZONEMINDER_API_TIMEOUT_SECS = ZmTimeouts.API_TIMEOUT_SECS

    CACHING_DISABLED = True
    
    def __init__( self ):
        super().__init__(
            id = 'zm-monitor',
            interval_secs = self.ZONEMINDER_POLLING_INTERVAL_SECS,
        )
        self._fully_processed_event_ids = TTLCache( maxsize = 1000, ttl = 100000 )
        self._start_processed_event_ids = TTLCache( maxsize = 1000, ttl = 100000 )
        self._zm_tzname = None

        self._poll_from_datetime = None
        self._was_initialized = False
        return
    
    def get_api_timeout(self) -> float:
        return self.ZONEMINDER_API_TIMEOUT_SECS

    async def _initialize(self):
        zm_manager = await self.zm_manager_async()
        if not zm_manager:
            return
        _ = await self.sensor_response_manager_async()  # Allows async use of self.sensor_response_manager()
        self._zm_tzname = await zm_manager.get_zm_tzname_async()
        self._poll_from_datetime = datetimeproxy.now()
        zm_manager.register_change_listener( self.refresh )
        self._was_initialized = True
        return
    
    def refresh( self ):
        """ 
        Called when integration settings are changed (via listener callback).
        
        Note: ZoneMinderManager.reload() is already called BEFORE this callback is triggered,
        so we should NOT call manager.reload() here to avoid redundant reloads.
        The monitor should just reset its own state to pick up fresh manager state.
        """
        # Reset monitor state so next cycle reinitializes with updated manager
        self._was_initialized = False
        self._zm_tzname = None  # Clear cached timezone
        logger.info( 'ZoneMinderMonitor refreshed - will reinitialize with new settings on next cycle' )
        return

    async def do_work(self):
        cycle_start_time = datetimeproxy.now()
        logger.debug('ZoneMinder monitor cycle starting')

        if not self._was_initialized:
            logger.debug('Monitor not initialized, attempting initialization')
            await self._initialize()

        if not self._was_initialized:
            # Timing issues when first enabling could fail initialization.
            logger.warning( 'ZoneMinder monitor failed to initialize. Skipping work cycle.' )
            return

        try:
            # Update heartbeat to indicate monitor is alive and working
            zm_manager = await self.zm_manager_async()
            if zm_manager:
                zm_manager.update_monitor_heartbeat()

            sensor_response_map = dict()

            # Process events with timing
            events_start = datetimeproxy.now()
            logger.debug('Processing ZoneMinder events')
            sensor_response_map.update( await self._process_events( ) )
            events_duration = (datetimeproxy.now() - events_start).total_seconds()
            logger.debug(f'Event processing completed in {events_duration:.2f}s, found {len([k for k in sensor_response_map.keys() if "motion" in k])} motion sensors')

            # Process monitors with timing
            monitors_start = datetimeproxy.now()
            logger.debug('Processing ZoneMinder monitors')
            sensor_response_map.update( await self._process_monitors() )
            monitors_duration = (datetimeproxy.now() - monitors_start).total_seconds()
            logger.debug(f'Monitor processing completed in {monitors_duration:.2f}s')

            # Process states with timing
            states_start = datetimeproxy.now()
            logger.debug('Processing ZoneMinder states')
            sensor_response_map.update( await self._process_states() )
            states_duration = (datetimeproxy.now() - states_start).total_seconds()
            logger.debug(f'State processing completed in {states_duration:.2f}s')

            # Update sensor responses
            update_start = datetimeproxy.now()
            await self.sensor_response_manager().update_with_latest_sensor_responses(
                sensor_response_map = sensor_response_map,
            )
            update_duration = (datetimeproxy.now() - update_start).total_seconds()

            # Log cycle completion with comprehensive timing
            total_duration = (datetimeproxy.now() - cycle_start_time).total_seconds()
            logger.info(f'ZoneMinder monitor cycle completed successfully in {total_duration:.2f}s '
                        f'(events: {events_duration:.2f}s, monitors: {monitors_duration:.2f}s, '
                        f'states: {states_duration:.2f}s, update: {update_duration:.2f}s) '
                        f'- {len(sensor_response_map)} sensor responses')

            # Log warning if cycle is taking too long
            if total_duration > (self.ZONEMINDER_POLLING_INTERVAL_SECS * 0.8):
                logger.warning(f'ZoneMinder monitor cycle took {total_duration:.2f}s, '
                               f'approaching polling interval of {self.ZONEMINDER_POLLING_INTERVAL_SECS}s')

        except Exception as e:
            cycle_duration = (datetimeproxy.now() - cycle_start_time).total_seconds()
            logger.exception(f'ZoneMinder monitor cycle failed after {cycle_duration:.2f}s: {e}')
            raise

        return
    
    async def _process_events(self):
        current_poll_datetime = datetimeproxy.now()

        # The pyzm ZM client library parses the "from" time as a naive time
        # and applies the timezone separately. pyzm will parse an ISO time
        # with a timezone, but pyzm ignores ignores the ISO time's encoded
        # timezone.  Thus, it is important that we have thisn "poll from"
        # in the same TZ as the ZoneMinder server and that we also pass
        # the TZ when filtering events.
        #
        tz_adjusted_poll_from_datetime = datetimeproxy.change_timezone(
            original_datetime = self._poll_from_datetime,
            new_tzname = self._zm_tzname,
        )            
        options = {
            'from': tz_adjusted_poll_from_datetime.isoformat(),  # "from" only looks at event start time
            'tz': self._zm_tzname,
        }
        # Log the API call details for debugging
        logger.debug(f'Querying ZoneMinder events from {tz_adjusted_poll_from_datetime.isoformat()} with options: {options}')
        api_call_start = datetimeproxy.now()

        try:
            zm_events = await self.zm_manager().get_zm_events_async( options = options )
            api_call_duration = (datetimeproxy.now() - api_call_start).total_seconds()
            logger.debug( f'Found {len(zm_events)} new ZM events in {api_call_duration:.2f}s' )

            # Log performance warning if API call is slow
            if api_call_duration > ZmTimeouts.API_RESPONSE_WARNING_THRESHOLD_SECS:
                logger.warning(f'ZoneMinder events API call took {api_call_duration:.2f}s '
                               f'(warning threshold: {ZmTimeouts.API_RESPONSE_WARNING_THRESHOLD_SECS}s)')

        except Exception as e:
            api_call_duration = (datetimeproxy.now() - api_call_start).total_seconds()
            logger.error(f'ZoneMinder events API call failed after {api_call_duration:.2f}s: {e}')
            raise

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
        for zm_api_event in zm_events:
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

        # NEW: Use two-phase approach to aggregate monitor states from event history
        # This fixes the core bug where multiple events per monitor would overwrite each other
        aggregated_states = self._aggregate_monitor_states(open_zm_event_list, closed_zm_event_list)
        sensor_response_map = self._generate_sensor_responses_from_states(aggregated_states)

        # If there are no events for monitors/states, we still want to emit the
        # sensor response of it being idle.
        #
        zm_monitors = await self.zm_manager().get_zm_monitors_async()
        for zm_monitor in zm_monitors:
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

    def _aggregate_monitor_states(self, open_zm_event_list, closed_zm_event_list):
        """
        Aggregate all events by monitor to determine the current state of each monitor.
        
        Returns dict mapping monitor_id -> AggregatedMonitorState
        """
        from collections import defaultdict
        
        # Group all events by monitor ID
        monitor_events = defaultdict(lambda: {'open_events': [], 'closed_events': []})
        
        for zm_event in open_zm_event_list:
            monitor_events[zm_event.monitor_id]['open_events'].append(zm_event)
        
        for zm_event in closed_zm_event_list:
            monitor_events[zm_event.monitor_id]['closed_events'].append(zm_event)
        
        aggregated_states = {}
        
        for monitor_id, events in monitor_events.items():
            open_events = events['open_events']
            closed_events = events['closed_events']
            all_events = open_events + closed_events
            
            # Sort all events chronologically for proper processing
            all_events.sort(key=lambda e: e.start_datetime)
            
            if open_events:
                # Monitor is currently ACTIVE - any open event means active
                # Use earliest open event start time as the effective timestamp
                open_events.sort(key=lambda e: e.start_datetime)
                earliest_open_event = open_events[0]
                
                aggregated_states[monitor_id] = AggregatedMonitorState(
                    monitor_id=monitor_id,
                    current_state=EntityStateValue.ACTIVE,
                    effective_timestamp=earliest_open_event.start_datetime,
                    canonical_event=earliest_open_event,
                    all_events=all_events
                )
            else:
                # Monitor is currently IDLE - all events are closed
                # Use latest closed event end time as the effective timestamp
                closed_events.sort(key=lambda e: e.end_datetime)
                latest_closed_event = closed_events[-1]
                
                aggregated_states[monitor_id] = AggregatedMonitorState(
                    monitor_id=monitor_id,
                    current_state=EntityStateValue.IDLE,
                    effective_timestamp=latest_closed_event.end_datetime,
                    canonical_event=latest_closed_event,
                    all_events=all_events
                )
        
        return aggregated_states
    
    def _generate_sensor_responses_from_states(self, aggregated_states):
        """
        Generate single SensorResponse per monitor based on aggregated state.
        Always emit current state - downstream components handle change detection.
        """
        sensor_response_map = {}
        
        for monitor_id, state in aggregated_states.items():
            # Create sensor response for this monitor's current state
            if state.is_active:
                sensor_response = self._create_movement_active_sensor_response(state.canonical_event)
            else:  # state.is_idle
                sensor_response = self._create_movement_idle_sensor_response(state.canonical_event)
                
            # Use our calculated effective timestamp
            sensor_response.timestamp = state.effective_timestamp
            
            sensor_response_map[sensor_response.integration_key] = sensor_response
            
            # Update event processing caches to avoid reprocessing from ZM API
            for zm_event in state.all_events:
                if zm_event.is_open:
                    self._start_processed_event_ids[zm_event.event_id] = True
                else:
                    self._start_processed_event_ids[zm_event.event_id] = True
                    self._fully_processed_event_ids[zm_event.event_id] = True
        
        return sensor_response_map

    async def _process_monitors(self):
        current_poll_datetime = datetimeproxy.now()
        sensor_response_map = dict()

        zm_monitors = await self.zm_manager().get_zm_monitors_async( force_load = self.CACHING_DISABLED )
        for zm_monitor in zm_monitors:
            function_sensor_response = self._create_monitor_function_sensor_response(
                zm_monitor = zm_monitor,
                timestamp = current_poll_datetime,
            )
            sensor_response_map[function_sensor_response.integration_key] = function_sensor_response
            continue
        
        return sensor_response_map
    
    async def _process_states(self):
        current_poll_datetime = datetimeproxy.now()
        sensor_response_map = dict()

        active_run_state_name = None
        zm_states = await self.zm_manager().get_zm_states_async( force_load = self.CACHING_DISABLED )
        for zm_state in zm_states:
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
      
    def _has_video_stream_capability(self, detail_attrs: dict = None) -> bool:
        """
        Determine if a SensorResponse should have video stream capability.
        For ZoneMinder, this means the response contains an Event ID.
        """
        return detail_attrs is not None and ZmDetailKeys.EVENT_ID_ATTR_NAME in detail_attrs
    
    def _create_movement_active_sensor_response( self, zm_event : ZmEvent ):
        all_detail_attrs = zm_event.to_detail_attrs()
        # For active (start) events, only include basic event info
        detail_attrs = {
            ZmDetailKeys.EVENT_ID_ATTR_NAME: all_detail_attrs.get(ZmDetailKeys.EVENT_ID_ATTR_NAME),
            ZmDetailKeys.START_TIME: all_detail_attrs.get(ZmDetailKeys.START_TIME),
            ZmDetailKeys.NOTES: all_detail_attrs.get(ZmDetailKeys.NOTES),
        }
        return SensorResponse(
            integration_key = self.zm_manager()._to_integration_key(
                prefix = ZoneMinderManager.MOVEMENT_SENSOR_PREFIX,
                zm_monitor_id = zm_event.monitor_id,
            ),
            value = str(EntityStateValue.ACTIVE),
            timestamp = zm_event.start_datetime,
            detail_attrs = detail_attrs,
            source_image_url = zm_event.image_url( self.zm_manager() ),
            has_video_stream = self._has_video_stream_capability(detail_attrs),
            correlation_role = CorrelationRole.START,
            correlation_id = all_detail_attrs.get(ZmDetailKeys.EVENT_ID_ATTR_NAME),
        )

    def _create_movement_idle_sensor_response( self, zm_event : ZmEvent ):
        all_detail_attrs = zm_event.to_detail_attrs()
        # For idle (end) events, include all detail attributes
        detail_attrs = all_detail_attrs

        return SensorResponse(
            integration_key = self.zm_manager()._to_integration_key(
                prefix = ZoneMinderManager.MOVEMENT_SENSOR_PREFIX,
                zm_monitor_id = zm_event.monitor_id,
            ),
            value = str(EntityStateValue.IDLE),
            timestamp = zm_event.end_datetime,
            detail_attrs = detail_attrs,
            has_video_stream = self._has_video_stream_capability(detail_attrs),
            correlation_role = CorrelationRole.END,
            correlation_id = all_detail_attrs.get(ZmDetailKeys.EVENT_ID_ATTR_NAME),
        )

    def _create_idle_sensor_response( self, zm_monitor : ZmMonitor, timestamp : datetime ):
        return SensorResponse(
            integration_key = self.zm_manager()._to_integration_key(
                prefix = ZoneMinderManager.MOVEMENT_SENSOR_PREFIX,
                zm_monitor_id = zm_monitor.id(),
            ),
            value = str(EntityStateValue.IDLE),
            timestamp = timestamp,
            has_video_stream = False,
        )

    def _create_monitor_function_sensor_response( self, zm_monitor : ZmMonitor, timestamp : datetime ):
        
        return SensorResponse(
            integration_key = self.zm_manager()._to_integration_key(
                prefix = ZoneMinderManager.MONITOR_FUNCTION_SENSOR_PREFIX,
                zm_monitor_id = zm_monitor.id(),
            ),
            value = str( zm_monitor.function() ),
            timestamp = timestamp,
            has_video_stream = False,
        )

    def _create_run_state_sensor_response( self, run_state_name : str, timestamp : datetime ):
        return SensorResponse(
            integration_key = self.zm_manager()._zm_run_state_integration_key(),
            value = run_state_name,
            timestamp = timestamp,
            has_video_stream = False,
        )
    
