from collections import defaultdict
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Optional, Set, Tuple

from django.conf import settings
from django.http import Http404

import hi.apps.common.datetimeproxy as datetimeproxy
from hi.apps.alert.enums import AlarmLevel
from hi.apps.monitor.periodic_monitor import PeriodicMonitor
from hi.apps.sense.enums import CorrelationRole
from hi.apps.sense.sensor_response_manager import SensorResponseMixin
from hi.apps.sense.transient_models import SensorResponse
from hi.integrations.transient_models import IntegrationKey
from hi.apps.system.provider_info import ProviderInfo
from hi.testing.dev_overrides import DevOverrideManager

from .constants import FrigateDetailKeys, FrigateTimeouts
from .frigate_converter import FrigateConverter
from .frigate_manager import FrigateManager
from .frigate_mixins import FrigateMixin
from .frigate_models import FrigateEvent, TrackedFrigateEvent

logger = logging.getLogger(__name__)


class FrigateMonitor( PeriodicMonitor, FrigateMixin, SensorResponseMixin ):
    """Periodic poll for Frigate cameras and events.

    Frigate's ``/api/events?after=T`` filters strictly on
    ``start_time > T``: once the cursor advances past an event's
    start_time, that event is invisible to cursor scans forever, even
    after it closes. So the pipeline doesn't pin the cursor to keep
    open events visible (the ZM-style approach is incompatible with
    Frigate's filter). Instead:

      Phase 1 — cursor scan (``?after=cursor``): emit START for each
        new event; emit END too if it was already closed when seen;
        track open ones in ``_tracked_events`` by id. Cursor advances
        monotonically to the latest start_time of any event observed.

      Phase 2 — per-id refresh (``GET /api/events/<id>``): for each
        tracked id, fetch its canonical state. Closed → emit END,
        drop from tracking. 404 → force-close, drop. Aged past
        ``MAX_OPEN_EVENT_AGE_SECS`` → force-close, drop.

      Phase 3 — heartbeat: emit OBJECT_NONE for cameras with no
        activity this cycle and no event currently tracked, so quiet
        cameras don't go stale.
    """

    MONITOR_ID = 'hi.services.frigate.monitor'

    # Force-close an open event whose age in HI's tracking set
    # exceeds this. Pulled into a class attribute so tests can shrink
    # the threshold to exercise the timeout path.
    MAX_OPEN_EVENT_AGE_SECS = FrigateTimeouts.MAX_OPEN_EVENT_AGE_SECS

    def __init__(self):
        super().__init__( id = self.MONITOR_ID )
        self._poll_cursor_datetime : Optional[ datetime ] = None
        self._tracked_events : Dict[ str, TrackedFrigateEvent ] = {}
        self._was_initialized = False
        return

    def get_polling_interval_secs(self) -> int:
        # The framework calls this at sort time (before _initialize
        # has run ``await self.frigate_manager_async()`` and cached
        # the manager reference on this instance), and on every tick
        # after that. Use the manager's reloaded value when the
        # mixin's cached ``_frigate_manager`` attribute exists; fall
        # back to the static constant before then -- avoids
        # triggering the manager mixin's sync ``ensure_initialized``
        # from the async event-loop thread.
        if hasattr( self, '_frigate_manager' ):
            return self._frigate_manager.polling_interval_secs
        return FrigateTimeouts.POLLING_INTERVAL_SECS

    def get_api_timeout(self) -> float:
        return FrigateTimeouts.API_TIMEOUT_SECS

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
        )

    async def _initialize(self):
        frigate_manager = await self.frigate_manager_async()
        if not frigate_manager:
            return
        _ = await self.sensor_response_manager_async()
        self._poll_cursor_datetime = datetimeproxy.now()
        self._tracked_events = {}
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

        sensor_response_list_map = await self._process_events()

        await self.sensor_response_manager().update_with_latest_sensor_response_lists(
            sensor_response_list_map = sensor_response_list_map,
        )
        response_count = sum( len( v ) for v in sensor_response_list_map.values() )
        self.record_healthy( f'Processed {response_count} Frigate states.' )
        return

    # ---- SensorResponse factory helpers ------------------------------

    def _create_object_presence_sensor_response(
            self,
            camera_name                  : str,
            value                        : str,
            timestamp                    : datetime,
            correlation_role             : 'CorrelationRole' = None,
            correlation_id               : str = None,
            has_event_video_clip         : bool = False,
            has_event_video_snapshot     : bool = False,
            detail_attrs                 : Dict = None,
    ) -> SensorResponse:
        """OBJECT_PRESENCE SensorResponse. ``value`` is one of the
        canonical bucket strings produced by
        ``FrigateConverter.to_canonical_object_class`` or
        ``OBJECT_NONE_VALUE`` for no-detection cycles."""
        return SensorResponse(
            integration_key = FrigateManager._to_integration_key(
                prefix = FrigateManager.OBJECT_PRESENCE_SENSOR_PREFIX,
                camera_name = camera_name,
            ),
            value = value,
            timestamp = timestamp,
            correlation_role = correlation_role,
            correlation_id = correlation_id,
            has_event_video_clip = has_event_video_clip,
            has_event_video_snapshot = has_event_video_snapshot,
            detail_attrs = detail_attrs,
        )

    def _build_event_detail_attrs( self,
                                   event      : FrigateEvent,
                                   is_closed  : bool ) -> Dict[ str, str ]:
        """Pack the event's metadata into a SensorResponse.detail_attrs
        dict so the event-detail UI surfaces the rich payload. Duration
        is omitted for open (START) responses — the value isn't known
        until the event closes."""
        attrs : Dict[ str, str ] = {
            FrigateDetailKeys.EVENT_ID: event.event_id,
            FrigateDetailKeys.START_TIME: event.start_datetime.isoformat(),
            FrigateDetailKeys.OBJECT_CLASS: event.object_class,
        }
        if event.score is not None:
            attrs[ FrigateDetailKeys.SCORE ] = f'{event.score:.2f}'
        if event.sub_label:
            attrs[ FrigateDetailKeys.SUB_LABEL ] = event.sub_label
        if event.zones:
            attrs[ FrigateDetailKeys.ZONES ] = ', '.join( event.zones )
        if is_closed and event.end_datetime is not None:
            duration = ( event.end_datetime - event.start_datetime ).total_seconds()
            attrs[ FrigateDetailKeys.DURATION_SECS ] = f'{duration:.1f}'
        return attrs

    # ---- Event processing pipeline ---------------------------------

    async def _process_events(self) -> Dict[ IntegrationKey, List[ SensorResponse ] ]:
        current_poll_datetime = datetimeproxy.now()

        scan_responses, scan_touched = await self._scan_new_events_phase()
        refresh_responses, refresh_touched = await self._refresh_tracked_events_phase(
            current_poll_datetime = current_poll_datetime,
        )
        heartbeat_responses = await self._heartbeat_idle_cameras_phase(
            current_poll_datetime = current_poll_datetime,
            cameras_touched = scan_touched | refresh_touched,
        )

        # Group all responses by integration_key, preserving multiple
        # responses per key for the same poll cycle (Person→Car within
        # one cycle yields END Person + START Car on the same sensor).
        sensor_response_list_map : Dict[ IntegrationKey, List[ SensorResponse ] ] = (
            defaultdict( list )
        )
        for response in ( scan_responses + refresh_responses + heartbeat_responses ):
            sensor_response_list_map[ response.integration_key ].append( response )
        return dict( sensor_response_list_map )

    async def _scan_new_events_phase(self) -> Tuple[ List[ SensorResponse ], Set[ str ] ]:
        """Query ``?after=cursor`` for events whose ``start_time``
        is past our watermark. Cursor is monotonic so any id returned
        here is new to us (any prior open event has ``start_time
        <= cursor`` and is tracked through phase 2 instead).

        Each new event:
          - emit START transition
          - if already closed: also emit END transition (downstream
            handles both as a multi-response sequence on the same key)
          - else: enter the open set for phase-2 tracking
        """
        after_epoch = self._poll_cursor_datetime.timestamp()
        try:
            api_events = await self.frigate_manager().get_events_async(
                after = after_epoch,
            )
        except Exception as e:
            logger.error( f'Frigate events API call failed: {e}' )
            raise

        new_events : List[ FrigateEvent ] = []
        for api_event in api_events:
            try:
                event = FrigateEvent.from_api_dict( api_event )
            except ValueError as e:
                logger.warning( f'Skipping malformed Frigate event: {e}' )
                continue
            if event.event_id in self._tracked_events:
                # Cursor is monotonic so this shouldn't happen, but
                # if Frigate ever serves the same id again, defer to
                # phase 2's canonical refresh.
                continue
            new_events.append( event )

        responses : List[ SensorResponse ] = []
        cameras_touched : Set[ str ] = set()
        now = datetimeproxy.now()
        for event in new_events:
            cameras_touched.add( event.camera_name )
            responses.append( self._build_object_presence_response(
                event = event,
                value = FrigateConverter.to_canonical_object_class(
                    raw_class = event.object_class,
                ),
                timestamp = event.start_datetime,
                correlation_role = CorrelationRole.START,
            ))
            if event.is_closed:
                responses.append( self._build_object_presence_response(
                    event = event,
                    value = FrigateConverter.OBJECT_NONE_VALUE,
                    timestamp = event.end_datetime,
                    correlation_role = CorrelationRole.END,
                ))
            else:
                self._tracked_events[ event.event_id ] = TrackedFrigateEvent(
                    event = event,
                    first_observed_at = now,
                )

        if new_events:
            # Defensive: Frigate's ``?after=`` filter is strict ``>``,
            # so all events here should already have start_time past
            # the cursor — but if upstream ever returns one that
            # doesn't (proxy replay, Frigate bug, clock skew), don't
            # let the cursor regress.
            latest_start = max( e.start_datetime for e in new_events )
            if latest_start > self._poll_cursor_datetime:
                self._poll_cursor_datetime = latest_start
        return responses, cameras_touched

    async def _refresh_tracked_events_phase(
            self,
            current_poll_datetime : datetime,
    ) -> Tuple[ List[ SensorResponse ], Set[ str ] ]:
        """Per-id refresh for every event currently in the tracked set.
        Outcomes per id:
          - 404 → force-close (vanished)
          - other failure → leave in set; force-close if aged out
          - closed → emit END, remove from set
          - still open → refresh snapshot; force-close if aged out
        """
        responses : List[ SensorResponse ] = []
        cameras_touched : Set[ str ] = set()
        tracked_ids = list( self._tracked_events.keys() )  # snapshot
        for event_id in tracked_ids:
            tracked_event = self._tracked_events.get( event_id )
            if tracked_event is None:
                continue
            try:
                api_event = await self.frigate_manager().get_event_async(
                    event_id = event_id,
                )
            except Http404:
                self._force_close(
                    tracked_event = tracked_event,
                    timestamp = current_poll_datetime,
                    reason = 'vanished',
                    responses = responses,
                    cameras_touched = cameras_touched,
                )
                continue
            except Exception as e:
                logger.warning(
                    f'Frigate refresh of open event {event_id} failed: {e}'
                )
                if self._should_force_close( tracked_event, current_poll_datetime ):
                    self._force_close(
                        tracked_event = tracked_event,
                        timestamp = current_poll_datetime,
                        reason = 'force_close_timeout',
                        responses = responses,
                        cameras_touched = cameras_touched,
                    )
                continue

            try:
                frigate_event = FrigateEvent.from_api_dict( api_event )
            except ValueError as e:
                logger.warning(
                    f'Open event {event_id} returned malformed payload: {e}'
                )
                continue

            cameras_touched.add( frigate_event.camera_name )
            if frigate_event.is_closed:
                responses.append( self._build_object_presence_response(
                    event = frigate_event,
                    value = FrigateConverter.OBJECT_NONE_VALUE,
                    timestamp = frigate_event.end_datetime,
                    correlation_role = CorrelationRole.END,
                ))
                del self._tracked_events[ event_id ]
                continue

            tracked_event.event = frigate_event
            if self._should_force_close( tracked_event, current_poll_datetime ):
                self._force_close(
                    tracked_event = tracked_event,
                    timestamp = current_poll_datetime,
                    reason = 'force_close_timeout',
                    responses = responses,
                    cameras_touched = cameras_touched,
                )
        return responses, cameras_touched

    async def _heartbeat_idle_cameras_phase(
            self,
            current_poll_datetime : datetime,
            cameras_touched       : Set[ str ],
    ) -> List[ SensorResponse ]:
        """Emit OBJECT_NONE for cameras with no event activity this
        cycle and no event currently tracked in the open set.

        Without this, a camera that's been quiet since HI started
        would never produce a SensorResponse and its state would go
        stale. Cameras with active or in-flight events are skipped —
        their state is being driven by phases 1 and 2 already."""
        try:
            cameras = await self.frigate_manager().get_cameras_async()
        except Exception as e:
            logger.warning(
                f'Frigate camera list fetch failed during heartbeat: {e}'
            )
            return []

        open_camera_names = {
            tracked_event.event.camera_name
            for tracked_event in self._tracked_events.values()
        }
        responses : List[ SensorResponse ] = []
        for camera in cameras:
            camera_name = camera[ 'name' ]
            if camera_name in cameras_touched:
                continue
            if camera_name in open_camera_names:
                continue
            idle_response = self._create_object_presence_sensor_response(
                camera_name = camera_name,
                value = FrigateConverter.OBJECT_NONE_VALUE,
                timestamp = current_poll_datetime,
            )
            responses.append( idle_response )

            if settings.DEBUG and settings.DEBUG_TRACE_STATE:
                DevOverrideManager.trace_state(
                    'hi.frigate_poll.no_events_object',
                    integration_name = idle_response.integration_key.integration_name,
                    integration_value = idle_response.value,
                    camera_name = camera_name,
                )
        return responses

    def _force_close(
            self,
            tracked_event   : TrackedFrigateEvent,
            timestamp       : datetime,
            reason          : str,
            responses       : List[ SensorResponse ],
            cameras_touched : Set[ str ],
    ) -> None:
        """Drop ``tracked_event`` from the tracked set and append a
        synthesized END response to ``responses``. Used when Frigate's
        canonical state cannot be obtained (404, persistent fetch
        failure past the age threshold)."""
        responses.append( self._build_force_close_response(
            tracked_event = tracked_event,
            timestamp = timestamp,
            reason = reason,
        ))
        cameras_touched.add( tracked_event.event.camera_name )
        del self._tracked_events[ tracked_event.event.event_id ]
        return

    def _should_force_close(
            self,
            tracked_event               : TrackedFrigateEvent,
            current_poll_datetime : datetime,
    ) -> bool:
        age = current_poll_datetime - tracked_event.first_observed_at
        return age > timedelta( seconds = self.MAX_OPEN_EVENT_AGE_SECS )

    def _build_object_presence_response(
            self,
            event             : FrigateEvent,
            value             : str,
            timestamp         : datetime,
            correlation_role  : CorrelationRole,
    ) -> SensorResponse:
        return self._create_object_presence_sensor_response(
            camera_name = event.camera_name,
            value = value,
            timestamp = timestamp,
            correlation_role = correlation_role,
            correlation_id = event.event_id,
            has_event_video_clip = event.has_clip,
            has_event_video_snapshot = event.has_snapshot,
            detail_attrs = self._build_event_detail_attrs(
                event = event,
                is_closed = ( correlation_role == CorrelationRole.END ),
            ),
        )

    def _build_force_close_response(
            self,
            tracked_event    : TrackedFrigateEvent,
            timestamp  : datetime,
            reason     : str,
    ) -> SensorResponse:
        """END response synthesized when we stop tracking an event
        without observing its actual close (404 from Frigate, or
        ``MAX_OPEN_EVENT_AGE_SECS`` exceeded). ``detail_attrs`` use
        the last-known payload — the real end_time was never seen,
        so no Duration field is included."""
        age_secs = ( timestamp - tracked_event.first_observed_at ).total_seconds()
        logger.warning(
            f'Frigate event {tracked_event.event.event_id}'
            f' (camera {tracked_event.event.camera_name})'
            f' force-closed after {age_secs:.0f}s: {reason}'
        )
        return self._create_object_presence_sensor_response(
            camera_name = tracked_event.event.camera_name,
            value = FrigateConverter.OBJECT_NONE_VALUE,
            timestamp = timestamp,
            correlation_role = CorrelationRole.END,
            correlation_id = tracked_event.event.event_id,
            has_event_video_clip = tracked_event.event.has_clip,
            has_event_video_snapshot = tracked_event.event.has_snapshot,
            detail_attrs = self._build_event_detail_attrs(
                event = tracked_event.event,
                is_closed = False,
            ),
        )
