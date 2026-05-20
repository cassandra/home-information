from cachetools import TTLCache
from collections import defaultdict
from datetime import datetime
import logging
from typing import Dict, List

import hi.apps.common.datetimeproxy as datetimeproxy
from hi.apps.alert.enums import AlarmLevel
from hi.apps.entity.enums import EntityStateValue
from hi.apps.monitor.periodic_monitor import PeriodicMonitor
from hi.apps.sense.enums import CorrelationRole
from hi.apps.sense.sensor_response_manager import SensorResponseMixin
from hi.apps.sense.transient_models import SensorResponse
from hi.apps.system.provider_info import ProviderInfo

from .constants import FrigateTimeouts
from .frigate_manager import FrigateManager
from .frigate_mixins import FrigateMixin
from .frigate_models import AggregatedCameraState, FrigateEvent

logger = logging.getLogger(__name__)


class FrigateMonitor( PeriodicMonitor, FrigateMixin, SensorResponseMixin ):
    """Periodic poll for Frigate cameras and events.

    Mirrors ``ZoneMinderMonitor`` carefully — the time-window event
    handling has known pitfalls that took several debugging rounds to
    get right on the ZM side. Preserve the order of operations:

      1. Fetch events with ``after=<polling-cursor>``.
      2. Two-phase collate: filter out fully-processed events, then
         partition the rest into open vs closed.
      3. Per-camera aggregation: pick ONE canonical event per camera
         (earliest open → ACTIVE; latest closed → IDLE).
      4. Emit SensorResponses from the aggregated states.
      5. Emit explicit IDLE for cameras that produced no events this
         cycle so their state doesn't go stale.
      6. Advance the polling cursor: hold it at the earliest open
         event's start when any open events remain; otherwise advance
         to the latest closed event's end. If there are NO events,
         do NOT advance (would risk missing an event that started
         right after the poll).

    Open events stay visible across polls until they close, so the
    ``_fully_processed_event_ids`` TTLCache only blocks closed events
    from being re-emitted.
    """

    MONITOR_ID = 'hi.services.frigate.monitor'

    POLLING_INTERVAL_SECS = FrigateTimeouts.POLLING_INTERVAL_SECS
    API_TIMEOUT_SECS = FrigateTimeouts.API_TIMEOUT_SECS

    # Cache sizing mirrors the ZM monitor — events are small dicts
    # keyed by id; 1000 entries comfortably covers a busy install over
    # the 100k-second TTL window.
    EVENT_ID_CACHE_MAXSIZE = 1000
    EVENT_ID_CACHE_TTL_SECS = 100000

    def __init__(self):
        super().__init__(
            id = self.MONITOR_ID,
            interval_secs = self.POLLING_INTERVAL_SECS,
        )
        self._fully_processed_event_ids = TTLCache(
            maxsize = self.EVENT_ID_CACHE_MAXSIZE,
            ttl = self.EVENT_ID_CACHE_TTL_SECS,
        )
        self._start_processed_event_ids = TTLCache(
            maxsize = self.EVENT_ID_CACHE_MAXSIZE,
            ttl = self.EVENT_ID_CACHE_TTL_SECS,
        )
        self._poll_from_datetime = None
        self._was_initialized = False
        return

    def get_api_timeout(self) -> float:
        return self.API_TIMEOUT_SECS

    def alarm_ceiling(self):
        # Frigate is a security-camera dependency; treat outages as
        # serious by default (same posture as the ZM monitor).
        return AlarmLevel.CRITICAL

    @classmethod
    def get_provider_info(cls) -> ProviderInfo:
        return ProviderInfo(
            provider_id = cls.MONITOR_ID,
            provider_name = 'Frigate Monitor',
            description = 'Frigate camera motion + object detection',
            expected_heartbeat_interval_secs = cls.POLLING_INTERVAL_SECS,
        )

    async def _initialize(self):
        frigate_manager = await self.frigate_manager_async()
        if not frigate_manager:
            return
        _ = await self.sensor_response_manager_async()
        self._poll_from_datetime = datetimeproxy.now()
        frigate_manager.register_change_listener( self.refresh )
        frigate_manager.add_subordinate_health_status_provider( self )
        self._was_initialized = True
        return

    def refresh(self):
        """Settings-changed callback: reset per-cycle state so the
        next ``do_work`` re-initializes against fresh manager state."""
        self._was_initialized = False
        return

    async def do_work(self):
        if not self._was_initialized:
            await self._initialize()
        if not self._was_initialized:
            logger.warning( 'Frigate monitor failed to initialize. Skipping work cycle.' )
            self.record_warning( 'Was not initialized.' )
            return

        sensor_response_map = dict()
        sensor_response_map.update( await self._process_events() )

        await self.sensor_response_manager().update_with_latest_sensor_responses(
            sensor_response_map = sensor_response_map,
        )
        self.record_healthy( f'Processed {len(sensor_response_map)} Frigate states.' )
        return

    # ---- Event processing pipeline (mirrors ZoneMinderMonitor) -------

    async def _process_events(self) -> Dict:
        current_poll_datetime = datetimeproxy.now()
        after_epoch = self._poll_from_datetime.timestamp()

        try:
            api_events = await self.frigate_manager().get_events_async(
                after = after_epoch,
            )
        except Exception as e:
            logger.error( f'Frigate events API call failed: {e}' )
            raise

        # Phase 1 — collate into open / closed, skip already-fully-processed.
        # Same shape as ZoneMinderMonitor: open events stay in scope across
        # polls (cursor is held back to keep them visible), closed events
        # get the fully-processed-cache treatment to prevent re-emission.
        open_event_list : List[ FrigateEvent ] = []
        closed_event_list : List[ FrigateEvent ] = []
        camera_names_seen = set()
        for api_event in api_events:
            try:
                event = FrigateEvent.from_api_dict( api_event )
            except ValueError as e:
                logger.warning( f'Skipping malformed Frigate event: {e}' )
                continue
            if event.event_id in self._fully_processed_event_ids:
                continue
            camera_names_seen.add( event.camera_name )
            if event.is_open:
                open_event_list.append( event )
            else:
                closed_event_list.append( event )
            continue

        # Phase 2 — per-camera aggregation. Multiple events on the same
        # camera collapse to a single canonical event so per-event
        # response generation doesn't have responses overwriting each
        # other in the sensor_response_map. (This was the core bug the
        # ZM monitor's two-phase rewrite fixed.)
        aggregated_states = self._aggregate_camera_states(
            open_event_list, closed_event_list,
        )
        sensor_response_map = self._generate_sensor_responses_from_states(
            aggregated_states,
        )

        # Phase 3 — cameras with no events in this window still need
        # an IDLE response so their state doesn't go stale. Iterate
        # the upstream camera list (not the HI Entity table) so a
        # camera that exists in Frigate but isn't yet imported still
        # gets a response — the SensorResponseManager drops responses
        # with no matching EntityState, which is the right behavior
        # for cameras that haven't been synced yet.
        try:
            cameras = await self.frigate_manager().get_cameras_async()
        except Exception as e:
            logger.warning( f'Frigate camera list fetch failed during idle pass: {e}' )
            cameras = []
        for camera in cameras:
            camera_name = camera[ 'name' ]
            if camera_name not in camera_names_seen:
                idle_response = self._create_idle_sensor_response(
                    camera_name = camera_name,
                    timestamp = current_poll_datetime,
                )
                sensor_response_map[ idle_response.integration_key ] = idle_response
            continue

        # Phase 4 — advance the polling cursor.
        #
        # Open events keep the cursor BACK so we continue to see them
        # on subsequent polls until they close. Only when every event
        # we saw is closed do we advance past them. With no events at
        # all, we don't advance — an event might have started right
        # after the API call and we have no way to know its start_time
        # is before our next cursor.
        if open_event_list:
            open_event_list.sort( key = lambda e : e.start_datetime )
            self._poll_from_datetime = open_event_list[0].start_datetime
        elif closed_event_list:
            closed_event_list.sort( key = lambda e : e.end_datetime )
            self._poll_from_datetime = closed_event_list[-1].end_datetime
        else:
            # No events — keep the cursor where it was; advancing
            # risks missing an event that started right after the
            # request and whose start_time is therefore < our next
            # 'after' filter.
            pass

        return sensor_response_map

    def _aggregate_camera_states(
            self,
            open_event_list   : List[ FrigateEvent ],
            closed_event_list : List[ FrigateEvent ],
    ) -> Dict[ str, AggregatedCameraState ]:
        """Per-camera aggregation: one ``AggregatedCameraState`` per
        camera that produced events this cycle.

        Same logic as ``ZmMonitor._aggregate_monitor_states``: any
        open event on a camera ⇒ camera is ACTIVE, canonical event
        is the earliest-start open one (so the effective timestamp
        reflects when motion actually started). All-closed ⇒ camera
        is IDLE, canonical event is the latest-end closed one (the
        most recent transition out of motion).
        """
        camera_events : Dict[ str, Dict[ str, list ] ] = defaultdict(
            lambda: { 'open': [], 'closed': [] }
        )
        for event in open_event_list:
            camera_events[ event.camera_name ][ 'open' ].append( event )
        for event in closed_event_list:
            camera_events[ event.camera_name ][ 'closed' ].append( event )

        aggregated : Dict[ str, AggregatedCameraState ] = {}
        for camera_name, events in camera_events.items():
            open_events = events[ 'open' ]
            closed_events = events[ 'closed' ]
            all_events = open_events + closed_events
            all_events.sort( key = lambda e : e.start_datetime )

            if open_events:
                open_events.sort( key = lambda e : e.start_datetime )
                canonical = open_events[ 0 ]
                aggregated[ camera_name ] = AggregatedCameraState(
                    camera_name = camera_name,
                    current_state = EntityStateValue.ACTIVE,
                    effective_timestamp = canonical.start_datetime,
                    canonical_event = canonical,
                    all_events = all_events,
                )
            else:
                closed_events.sort( key = lambda e : e.end_datetime )
                canonical = closed_events[ -1 ]
                aggregated[ camera_name ] = AggregatedCameraState(
                    camera_name = camera_name,
                    current_state = EntityStateValue.IDLE,
                    effective_timestamp = canonical.end_datetime,
                    canonical_event = canonical,
                    all_events = all_events,
                )
            continue
        return aggregated

    def _generate_sensor_responses_from_states(
            self,
            aggregated_states : Dict[ str, AggregatedCameraState ],
    ) -> Dict:
        """Emit a single MOVEMENT SensorResponse per aggregated camera
        state, with ``correlation_role`` + ``correlation_id`` set so
        downstream alarm dedup pairs ACTIVE / IDLE for the same event.

        Also updates the per-event caches: closed events are marked
        ``_fully_processed_event_ids`` so they won't be re-emitted on
        the next poll; all events are marked
        ``_start_processed_event_ids`` (kept symmetric with ZM even
        though the start-cache isn't read by the current pipeline)."""
        sensor_response_map : Dict = {}
        for state in aggregated_states.values():
            if state.is_active:
                response = self._create_movement_active_sensor_response(
                    event = state.canonical_event,
                )
            else:
                response = self._create_movement_idle_sensor_response(
                    event = state.canonical_event,
                )
            response.timestamp = state.effective_timestamp
            sensor_response_map[ response.integration_key ] = response

            for event in state.all_events:
                self._start_processed_event_ids[ event.event_id ] = True
                if event.is_closed:
                    self._fully_processed_event_ids[ event.event_id ] = True
                continue
            continue
        return sensor_response_map

    # ---- SensorResponse factory helpers ------------------------------

    def _create_movement_active_sensor_response(
            self, event : FrigateEvent,
    ) -> SensorResponse:
        return SensorResponse(
            integration_key = FrigateManager._to_integration_key(
                prefix = FrigateManager.MOVEMENT_SENSOR_PREFIX,
                camera_name = event.camera_name,
            ),
            value = str( EntityStateValue.ACTIVE ),
            timestamp = event.start_datetime,
            correlation_role = CorrelationRole.START,
            correlation_id = event.event_id,
        )

    def _create_movement_idle_sensor_response(
            self, event : FrigateEvent,
    ) -> SensorResponse:
        return SensorResponse(
            integration_key = FrigateManager._to_integration_key(
                prefix = FrigateManager.MOVEMENT_SENSOR_PREFIX,
                camera_name = event.camera_name,
            ),
            value = str( EntityStateValue.IDLE ),
            timestamp = event.end_datetime,
            correlation_role = CorrelationRole.END,
            correlation_id = event.event_id,
        )

    def _create_idle_sensor_response(
            self, camera_name : str, timestamp : datetime,
    ) -> SensorResponse:
        """No-event-this-cycle IDLE response. No correlation id
        because there's no event to pair with — this is just a
        "currently quiet" signal."""
        return SensorResponse(
            integration_key = FrigateManager._to_integration_key(
                prefix = FrigateManager.MOVEMENT_SENSOR_PREFIX,
                camera_name = camera_name,
            ),
            value = str( EntityStateValue.IDLE ),
            timestamp = timestamp,
        )
