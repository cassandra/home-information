from cachetools import TTLCache
from collections import defaultdict
from datetime import datetime
import logging
from typing import Dict, List
from .pyzm_client.helpers.Monitor import Monitor as ZmMonitor

from django.conf import settings

import hi.apps.common.datetimeproxy as datetimeproxy
from hi.apps.alert.enums import AlarmLevel
from hi.apps.entity.enums import EntityStateValue
from hi.apps.monitor.periodic_monitor import PeriodicMonitor
from hi.apps.sense.sensor_response_manager import SensorResponseMixin
from hi.apps.sense.transient_models import SensorResponse
from hi.apps.sense.enums import CorrelationRole
from hi.apps.system.provider_info import ProviderInfo
from hi.integrations.transient_models import IntegrationKey
from hi.testing.dev_overrides import DevOverrideManager

from .constants import ZmDetailKeys, ZmTimeouts
from .zm_models import ZmEvent
from .zm_manager import ZoneMinderManager
from .zm_mixins import ZoneMinderMixin

logger = logging.getLogger(__name__)


class ZoneMinderMonitor( PeriodicMonitor, ZoneMinderMixin, SensorResponseMixin ):

    MONITOR_ID = 'hi.services.zoneminder.monitor'
    
    # TODO: Move this into the integrations attributes for users to set
    ZONEMINDER_SERVER_TIMEZONE = 'America/Chicago'

    # Use centralized timeout constants
    ZONEMINDER_POLLING_INTERVAL_SECS = ZmTimeouts.POLLING_INTERVAL_SECS
    ZONEMINDER_API_TIMEOUT_SECS = ZmTimeouts.API_TIMEOUT_SECS

    DEBUG_STATES_AND_MONITORS = False
    
    def __init__( self ):
        super().__init__(
            id = self.MONITOR_ID,
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

    def alarm_ceiling(self):
        # ZM outage in the background masks security camera events.
        # Treat health failures here as serious.
        return AlarmLevel.CRITICAL

    async def _initialize(self):
        zm_manager = await self.zm_manager_async()  # Allows sync use elsewhere in module
        if not zm_manager:
            return
        _ = await self.sensor_response_manager_async()  # Allows sync use elsewhere in module

        self._zm_tzname = await zm_manager.get_zm_tzname_async()
        self._poll_from_datetime = datetimeproxy.now()
        zm_manager.register_change_listener( self.refresh )
        # See HassMonitor._initialize for the rationale behind subordinate
        # registration: aggregated manager health pulls monitor status on
        # demand, so a healthy reload cannot mask a failing monitor.
        zm_manager.add_subordinate_health_status_provider( self )
        self._was_initialized = True
        return
    
    @classmethod
    def get_provider_info(cls) -> ProviderInfo:
        return ProviderInfo(
            provider_id = cls.MONITOR_ID,
            provider_name = 'ZoneMinder Monitor',
            description = 'ZoneMinder camera motion detection',
            expected_heartbeat_interval_secs = cls.ZONEMINDER_POLLING_INTERVAL_SECS,
        )
    
    def refresh( self ):
        """
        Called when integration settings are changed (via listener callback).

        Note: ZoneMinderManager.reload() is already called BEFORE this callback is triggered,
        so we should NOT call manager.reload() here to avoid redundant reloads.
        The monitor should just reset its own state to pick up fresh manager state.
        """
        # Reset monitor state so next cycle reinitializes with updated manager
        self._was_initialized = False
        self._zm_tzname = None
        logger.debug( 'ZoneMinderMonitor refreshed - will reinitialize with new settings on next cycle' )
        return

    async def do_work(self):
        if not self._was_initialized:
            await self._initialize()

        if not self._was_initialized:
            # Timing issues when first enabling could fail initialization.
            logger.warning( 'ZoneMinder monitor failed to initialize. Skipping work cycle.' )
            self.record_warning( 'Was not initialized.' )
            return

        # Events flow through the list-form path because a single
        # poll window can carry multiple transitions for the same
        # monitor (see #351). Monitor function and run-state are
        # single-response-by-domain — wrap each in a one-element list
        # at the merge boundary so everything submits through the
        # same manager entry point.
        sensor_response_list_map : Dict[ IntegrationKey, List[ SensorResponse ] ] = (
            defaultdict( list )
        )
        for key, response_list in ( await self._process_events() ).items():
            sensor_response_list_map[ key ].extend( response_list )
        for key, response in ( await self._process_monitors() ).items():
            sensor_response_list_map[ key ].append( response )
        for key, response in ( await self._process_states() ).items():
            sensor_response_list_map[ key ].append( response )

        await self.sensor_response_manager().update_with_latest_sensor_response_lists(
            sensor_response_list_map = dict( sensor_response_list_map ),
        )
        response_count = sum( len( v ) for v in sensor_response_list_map.values() )
        message = f'Processed {response_count} ZoneMinder responses.'
        self.record_healthy( message )
        # Manager picks up our status via add_subordinate_health_status_provider
        # registration; no explicit push needed here.
        return
    
    async def _process_events(self) -> Dict[ IntegrationKey, List[ SensorResponse ] ]:
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
        try:
            zm_events = await self.zm_manager().get_zm_events_async( options = options )
        except Exception as e:
            logger.error(f'ZoneMinder events API call failed: {e}')
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

        # Emit per-transition. SensorResponseManager records each as
        # its own history row + entity_state_transition, so events
        # that previously got collapsed under the single-response
        # contract (Scenarios A and B in #351) now propagate fully.
        responses : List[ SensorResponse ] = []
        for zm_event in open_zm_event_list:
            if zm_event.event_id in self._start_processed_event_ids:
                # START already emitted on a prior cursor-hold poll;
                # event is still open, nothing new to record.
                continue
            responses.append( self._create_movement_active_sensor_response( zm_event ))
            self._start_processed_event_ids[ zm_event.event_id ] = True
        for zm_event in closed_zm_event_list:
            if zm_event.event_id not in self._start_processed_event_ids:
                # Opened-and-closed within this single poll — emit
                # both halves so the active interval is recorded.
                responses.append( self._create_movement_active_sensor_response( zm_event ))
                self._start_processed_event_ids[ zm_event.event_id ] = True
            responses.append( self._create_movement_idle_sensor_response( zm_event ))
            self._fully_processed_event_ids[ zm_event.event_id ] = True

        sensor_response_list_map : Dict[ IntegrationKey, List[ SensorResponse ] ] = (
            defaultdict( list )
        )
        for response in responses:
            sensor_response_list_map[ response.integration_key ].append( response )

            if settings.DEBUG and settings.DEBUG_TRACE_STATE:
                DevOverrideManager.trace_state(
                    'hi.zm_poll.events',
                    integration_name = response.integration_key.integration_name,
                    integration_value = response.value,
                    correlation_role = str( response.correlation_role ),
                    correlation_id = response.correlation_id,
                )

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
                sensor_response_list_map[
                    idle_sensor_response.integration_key
                ].append( idle_sensor_response )

                if settings.DEBUG and settings.DEBUG_TRACE_STATE:
                    DevOverrideManager.trace_state(
                        'hi.zm_poll.no_events',
                        integration_name = idle_sensor_response.integration_key.integration_name,
                        integration_value = idle_sensor_response.value,
                        monitor_id = zm_monitor.id(),
                    )
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

        return dict( sensor_response_list_map )

    async def _process_monitors(self):
        current_poll_datetime = datetimeproxy.now()
        sensor_response_map = dict()

        zm_monitors = await self.zm_manager().get_zm_monitors_async( force_load = self.DEBUG_STATES_AND_MONITORS )
        for zm_monitor in zm_monitors:
            function_sensor_response = self._create_monitor_function_sensor_response(
                zm_monitor = zm_monitor,
                timestamp = current_poll_datetime,
            )
            sensor_response_map[function_sensor_response.integration_key] = function_sensor_response

            if settings.DEBUG and settings.DEBUG_TRACE_STATE:
                DevOverrideManager.trace_state(
                    'hi.zm_poll.function',
                    integration_name = function_sensor_response.integration_key.integration_name,
                    integration_value = str( zm_monitor.function() ),
                    monitor_id = zm_monitor.id(),
                )
            continue

        return sensor_response_map

    async def _process_states(self):
        current_poll_datetime = datetimeproxy.now()
        sensor_response_map = dict()

        active_run_state_name = None
        zm_states = await self.zm_manager().get_zm_states_async( force_load = self.DEBUG_STATES_AND_MONITORS )
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

            if settings.DEBUG and settings.DEBUG_TRACE_STATE:
                DevOverrideManager.trace_state(
                    'hi.zm_poll.run_state',
                    integration_name = run_state_sensor_response.integration_key.integration_name,
                    integration_value = active_run_state_name,
                )

        return sensor_response_map
      
    def _has_event_video_clip_capability(self, detail_attrs: dict = None) -> bool:
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
        has_event_id = self._has_event_video_clip_capability(detail_attrs)
        return SensorResponse(
            integration_key = self.zm_manager()._to_integration_key(
                prefix = ZoneMinderManager.MOVEMENT_SENSOR_PREFIX,
                zm_monitor_id = zm_event.monitor_id,
            ),
            value = str(EntityStateValue.ACTIVE),
            timestamp = zm_event.start_datetime,
            detail_attrs = detail_attrs,
            has_event_video_clip = has_event_id,
            has_event_video_snapshot = has_event_id,
            correlation_role = CorrelationRole.START,
            correlation_id = all_detail_attrs.get(ZmDetailKeys.EVENT_ID_ATTR_NAME),
        )

    def _create_movement_idle_sensor_response( self, zm_event : ZmEvent ):
        all_detail_attrs = zm_event.to_detail_attrs()
        # For idle (end) events, include all detail attributes
        detail_attrs = all_detail_attrs

        has_event_id = self._has_event_video_clip_capability(detail_attrs)
        return SensorResponse(
            integration_key = self.zm_manager()._to_integration_key(
                prefix = ZoneMinderManager.MOVEMENT_SENSOR_PREFIX,
                zm_monitor_id = zm_event.monitor_id,
            ),
            value = str(EntityStateValue.IDLE),
            timestamp = zm_event.end_datetime,
            detail_attrs = detail_attrs,
            has_event_video_clip = has_event_id,
            has_event_video_snapshot = has_event_id,
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
            has_event_video_clip = False,
        )

    def _create_monitor_function_sensor_response( self, zm_monitor : ZmMonitor, timestamp : datetime ):
        
        return SensorResponse(
            integration_key = self.zm_manager()._to_integration_key(
                prefix = ZoneMinderManager.MONITOR_FUNCTION_SENSOR_PREFIX,
                zm_monitor_id = zm_monitor.id(),
            ),
            value = str( zm_monitor.function() ),
            timestamp = timestamp,
            has_event_video_clip = False,
        )

    def _create_run_state_sensor_response( self, run_state_name : str, timestamp : datetime ):
        return SensorResponse(
            integration_key = self.zm_manager()._zm_run_state_integration_key(),
            value = run_state_name,
            timestamp = timestamp,
            has_event_video_clip = False,
        )
    
