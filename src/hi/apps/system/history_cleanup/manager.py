"""
History Cleanup Manager - Coordinates cleanup across all application history tables

This module is responsible for coordinating database history table cleanup
across the entire application. It knows about all history tables that need
cleanup and manages the process transparently.
"""

import logging
from typing import List, Dict, Any

from hi.apps.common.history_table_manager import HistoryTableManager, CleanupResult, CleanupResultType
from hi.apps.control.models import ControllerHistory
from hi.apps.event.models import EventHistory
from hi.apps.sense.models import SensorHistory

logger = logging.getLogger(__name__)


class HistoryCleanupManager:
    """
    Coordinates cleanup across all application history tables.

    This manager knows about all the history tables in the application
    that need periodic cleanup and coordinates the cleanup process
    across all of them using the generic HistoryTableManager.

    It's responsible for:
    - Knowing which tables need cleanup
    - Configuring appropriate limits for each table type
    - Coordinating cleanup across all tables
    - Aggregating results and logging
    """

    def __init__(self):
        """Initialize the history cleanup manager with table configurations."""
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        # Configure each history table with appropriate settings
        self._table_managers = [
            {
                'name': 'SensorHistory',
                'manager': HistoryTableManager(
                    queryset=SensorHistory.objects.all(),
                    date_field_name='response_datetime',
                    min_days_retention=30,      # Keep 30 days minimum
                    max_records_limit=100000,   # 100K record limit
                    deletion_batch_size=1000    # Delete 1K per cycle
                ),
            },
            {
                'name': 'ControllerHistory',
                'manager': HistoryTableManager(
                    queryset=ControllerHistory.objects.all(),
                    date_field_name='created_datetime',
                    min_days_retention=30,      # Keep 30 days minimum
                    max_records_limit=100000,   # 100K record limit
                    deletion_batch_size=1000    # Delete 1K per cycle
                ),
            },
            {
                'name': 'EventHistory',
                'manager': HistoryTableManager(
                    queryset=EventHistory.objects.all(),
                    date_field_name='event_datetime',
                    min_days_retention=30,      # Keep 30 days minimum
                    max_records_limit=100000,   # 100K record limit
                    deletion_batch_size=1000    # Delete 1K per cycle
                ),
            },
        ]

    def cleanup_next_batch(self) -> CleanupResult:
        """
        Perform cleanup on the next batch across all history tables.

        This method calls cleanup_next_batch() on each configured history
        table manager and aggregates the results.

        Returns:
            CleanupResult: Aggregated cleanup results across all tables
        """
        import hi.apps.common.datetimeproxy as datetimeproxy
        start_time = datetimeproxy.now()

        self._logger.info("Starting history cleanup across all tables")

        total_deleted = 0
        error_count = 0
        tables_with_cleanup = 0

        for table_config in self._table_managers:
            table_name = table_config['name']
            manager = table_config['manager']

            try:
                self._logger.debug(f"Running cleanup for {table_name}")
                result = manager.cleanup_next_batch()

                total_deleted += result.deleted_count

                if result.deleted_count > 0:
                    tables_with_cleanup += 1
                    self._logger.info(
                        f"{table_name}: deleted {result.deleted_count} records "
                        f"in {result.duration_seconds:.3f}s"
                    )
                else:
                    self._logger.debug(
                        f"{table_name}: {result.reason} "
                        f"(duration: {result.duration_seconds:.3f}s)"
                    )

            except Exception as e:
                error_count += 1
                error_msg = f"Error cleaning up {table_name}: {e}"
                self._logger.exception(error_msg)

        # Calculate total duration
        total_duration = (datetimeproxy.now() - start_time).total_seconds()

        # Determine aggregate result type and reason
        if error_count > 0:
            if error_count == len(self._table_managers):
                result_type = CleanupResultType.ALL_TABLES_FAILED
                reason = "All tables failed cleanup"
            else:
                result_type = CleanupResultType.PARTIAL_ERRORS
                reason = f"Cleaned {total_deleted} records, {error_count} table error{'s' if error_count > 1 else ''}"
        elif total_deleted > 0:
            result_type = CleanupResultType.CLEANUP_PERFORMED
            reason = f"Cleaned {total_deleted} records in {total_duration:.1f}s"
        else:
            result_type = CleanupResultType.UNDER_LIMIT
            reason = "All tables under limits"

        # Log final summary
        if error_count > 0:
            self._logger.warning(
                f"History cleanup completed with {error_count} errors. "
                f"Total deleted: {total_deleted} records"
            )
        else:
            self._logger.info(
                f"History cleanup completed successfully. "
                f"Total deleted: {total_deleted} records across {len(self._table_managers)} tables"
            )

        return CleanupResult(
            deleted_count=total_deleted,
            result_type=result_type,
            reason=reason,
            duration_seconds=total_duration
        )

    def get_table_summaries(self) -> Dict[str, Dict[str, Any]]:
        """
        Get summary information about all configured history tables.

        Returns:
            Dict[str, Dict[str, Any]]: Summary for each table including record counts
        """
        summaries = {}

        for table_config in self._table_managers:
            table_name = table_config['name']
            manager = table_config['manager']

            try:
                record_count = manager._get_record_count()
                summaries[table_name] = {
                    'record_count': record_count,
                    'max_limit': manager.max_records_limit,
                    'retention_days': manager.min_days_retention,
                    'batch_size': manager.deletion_batch_size,
                    'over_limit': record_count > manager.max_records_limit
                }
            except Exception as e:
                summaries[table_name] = {
                    'error': str(e)
                }

        return summaries