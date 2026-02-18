import logging

from hi.apps.monitor.periodic_monitor import PeriodicMonitor
from hi.apps.system.provider_info import ProviderInfo

from .hb_mixins import HomeBoxMixin

logger = logging.getLogger(__name__)


class HomeBoxMonitor( PeriodicMonitor, HomeBoxMixin ):

	MONITOR_ID = 'hi.services.homebox.monitor'
	HOMEBOX_POLLING_INTERVAL_SECS = 30
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

		item_list = await hb_manager.fetch_hb_items_from_api_async( verbose = False )
		message = f'Processed {len(item_list)} HomeBox items.'
		self.record_healthy( message )
		hb_manager.record_healthy( message )
		return
