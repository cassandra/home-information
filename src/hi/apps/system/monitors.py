from asgiref.sync import sync_to_async
import logging

from hi.apps.common.history_table_manager import CleanupResultType
from hi.apps.monitor.periodic_monitor import PeriodicMonitor
from hi.apps.system.history_cleanup.manager import HistoryCleanupManager
from hi.apps.system.provider_info import ProviderInfo

logger = logging.getLogger(__name__)


class SystemMonitor( PeriodicMonitor ):
    """
    Monitor for automated background system maintenance tasks.

    This monitor handles various system-level maintenance operations that need to
    run periodically in the background, such as database cleanup, cache management,
    and other housekeeping tasks.
    """

    MONITOR_ID = 'hi.apps.system.monitor'
    SYSTEM_MAINTENANCE_INTERVAL_SECS = 8 * 60 * 60  # 8 hours

    def __init__(self):
        super().__init__(
            id = self.MONITOR_ID,
            interval_secs = self.SYSTEM_MAINTENANCE_INTERVAL_SECS,
        )
        return

    @classmethod
    def get_provider_info(cls) -> ProviderInfo:
        return ProviderInfo(
            provider_id = cls.MONITOR_ID,
            provider_name = 'System Monitor',
            description = 'Automated system maintenance tasks',
            expected_heartbeat_interval_secs = cls.SYSTEM_MAINTENANCE_INTERVAL_SECS,
        )

    async def do_work(self):
        logger.debug('Running system maintenance tasks')
        try:
            await self.do_history_table_maintenance()
        except Exception as e:
            logger.exception(f'Failed to run history cleanup: {e}')
            error_message = f"Cleanup failed: {str(e)[:30]}{'...' if len(str(e)) > 30 else ''}"
            self.record_error(error_message)

        logger.debug('System maintenance tasks completed')
        return

    async def do_history_table_maintenance(self):

        # Run the cleanup in a sync context since it uses Django ORM
        @sync_to_async
        def run_cleanup():
            history_manager = HistoryCleanupManager()
            return history_manager.cleanup_next_batch()

        cleanup_result = await run_cleanup()

        logger.debug( f'History cleanup completed: {cleanup_result.deleted_count}'
                      f' records deleted' )

        message = f'History cleanup: {cleanup_result.reason}'
        if cleanup_result.result_type == CleanupResultType.ALL_TABLES_FAILED:
            self.record_error( message )
        elif cleanup_result.result_type == CleanupResultType.PARTIAL_ERRORS:
            self.record_warning( message )
        else:
            # Success cases: CLEANUP_PERFORMED, UNDER_LIMIT, NO_OLD_RECORDS
            self.record_healthy( message )
        return
    
