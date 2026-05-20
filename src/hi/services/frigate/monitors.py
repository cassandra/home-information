import logging

from hi.apps.alert.enums import AlarmLevel
from hi.apps.monitor.periodic_monitor import PeriodicMonitor
from hi.apps.sense.sensor_response_manager import SensorResponseMixin
from hi.apps.system.provider_info import ProviderInfo

from .constants import FrigateTimeouts
from .frigate_mixins import FrigateMixin

logger = logging.getLogger(__name__)


class FrigateMonitor( PeriodicMonitor, FrigateMixin, SensorResponseMixin ):
    """Periodic poll for Frigate cameras and events.

    Mirrors ``ZoneMinderMonitor``: pulls ``/api/events`` since the
    last cursor, aggregates per-camera state (open events keep the
    camera ACTIVE; cursor held back to the earliest open event),
    emits ``SensorResponse`` updates for the Movement sensor +
    ObjectPresence sensor. Scaffolding stub: ``do_work`` records a
    healthy heartbeat without polling anything yet.
    """

    MONITOR_ID = 'hi.services.frigate.monitor'

    POLLING_INTERVAL_SECS = FrigateTimeouts.POLLING_INTERVAL_SECS
    API_TIMEOUT_SECS = FrigateTimeouts.API_TIMEOUT_SECS

    def __init__(self):
        super().__init__(
            id = self.MONITOR_ID,
            interval_secs = self.POLLING_INTERVAL_SECS,
        )
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
            self.record_warning( 'Was not initialized.' )
            return
        # Scaffolding stub: real work (event polling, sensor-response
        # emission) lands in feature work.
        self.record_healthy( 'Frigate monitor scaffolding heartbeat.' )
        return
