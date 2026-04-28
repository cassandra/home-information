import logging

from hi.apps.alert.enums import AlarmLevel
from hi.apps.monitor.periodic_monitor import PeriodicMonitor
from hi.apps.system.provider_info import ProviderInfo

from .hb_mixins import HomeBoxMixin

logger = logging.getLogger(__name__)


class HomeBoxMonitor( PeriodicMonitor, HomeBoxMixin ):
    """
    HomeBox does not have real-time per-item state to poll. The monitor's
    only job is a periodic reachability/health probe so the integration's
    health status reflects whether the API is currently reachable. Entity
    creation/update/removal happens only via user-initiated SYNC.
    """

    MONITOR_ID = 'hi.services.homebox.monitor'
    HOMEBOX_POLLING_INTERVAL_SECS = 300
    HOMEBOX_API_TIMEOUT_SECS = 20.0

    def __init__( self ):
        super().__init__(
            id = self.MONITOR_ID,
            interval_secs = self.HOMEBOX_POLLING_INTERVAL_SECS,
        )
        self._was_initialized = False
        return

    def get_api_timeout(self) -> float:
        return self.HOMEBOX_API_TIMEOUT_SECS

    def alarm_max_level(self):
        # HomeBox tracks inventory data — degraded availability is
        # informational, not safety-critical, so cap at INFO.
        return AlarmLevel.INFO

    async def _initialize(self):
        hb_manager = await self.hb_manager_async()
        if not hb_manager:
            return
        hb_manager.register_change_listener( self.refresh )
        self._was_initialized = True
        return

    def refresh( self ):
        self._was_initialized = False
        logger.info( 'HomeBoxMonitor refreshed - will reinitialize with new settings on next cycle' )
        return

    @classmethod
    def get_provider_info(cls) -> ProviderInfo:
        return ProviderInfo(
            provider_id = cls.MONITOR_ID,
            provider_name = 'HomeBox Monitor',
            description = 'HomeBox integration health monitor',
            expected_heartbeat_interval_secs = cls.HOMEBOX_POLLING_INTERVAL_SECS,
        )

    async def do_work(self):
        if not self._was_initialized:
            await self._initialize()

        if not self._was_initialized:
            logger.warning( 'HomeBox monitor failed to initialize. Skipping work cycle.' )
            self.record_warning( 'Was not initialized.' )
            return

        hb_manager = await self.hb_manager_async()
        if not hb_manager:
            self.record_error( 'No manager found.' )
            return

        try:
            item_count = await self._check_api_reachable( hb_manager )
        except Exception as e:
            # The probe failed (client unavailable, upstream unreachable,
            # bad response, etc.). Record the actual reason on BOTH the
            # monitor and the manager so the integration's user-visible
            # health surfaces the real cause instead of the last-known
            # success message.
            message = f'HomeBox API probe failed: {e}'
            logger.warning( message )
            self.record_warning( message )
            hb_manager.record_warning( message )
            return

        message = f'HomeBox API reachable. items={item_count}'
        self.record_healthy( message )
        hb_manager.record_healthy( message )
        return

    async def _check_api_reachable(self, hb_manager) -> int:
        """
        Lightweight reachability probe: hits the items summary endpoint
        (one API call, no per-item detail fetches) and returns the count.
        The count is informational; the probe's purpose is to confirm
        the API is up and authentication is still valid.
        """
        item_list = await hb_manager.fetch_hb_items_summary_from_api_async()
        return len(item_list)
