"""
History Table Manager - Generic Database History Table Cleanup

This module provides a generic, reusable class for managing history table
cleanup operations. It implements configurable size limits and safe,
rate-limited deletion with comprehensive transaction management.

This module is app-independent and can be used in any Django application
by providing the appropriate configuration.

Usage:
    manager = HistoryTableManager(
        queryset=MyHistoryModel.objects.all(),
        date_field_name='created_datetime',
        min_days_retention=30,
        max_records_limit=100000,
        deletion_batch_size=1000
    )
    result = manager.cleanup_next_batch()
"""

import logging
from dataclasses import dataclass
from datetime import timedelta
from typing import List

from django.db import transaction
from django.db.models import QuerySet

import hi.apps.common.datetimeproxy as datetimeproxy
from hi.apps.common.enums import LabeledEnum


class CleanupResultType(LabeledEnum):
    """Types of cleanup operation results."""

    UNDER_LIMIT = ('Under Limit', 'Table is under the record limit, no cleanup needed')
    NO_OLD_RECORDS = ('No Old Records', 'No records old enough to delete within retention period')
    CLEANUP_PERFORMED = ('Cleanup Performed', 'Successfully deleted old records')
    PARTIAL_ERRORS = ('Partial Errors', 'Some tables cleaned successfully, others had errors')
    ALL_TABLES_FAILED = ('All Failed', 'All table cleanup operations failed')
    CLEANUP_FAILED = ('Failed', 'Cleanup operation failed due to error')

logger = logging.getLogger(__name__)


@dataclass
class CleanupResult:
    """Result of a cleanup operation."""
    deleted_count: int
    result_type: CleanupResultType
    reason: str  # Human-readable message for health status
    duration_seconds: float = 0.0


class HistoryTableManager:
    """
    Generic manager for history table cleanup operations.

    This class provides configurable history table cleanup with:
    - Configurable retention limits (days and record count)
    - Rate-limited deletion to prevent performance impacts
    - Transaction management for database operations
    - Comprehensive logging and monitoring

    The cleanup algorithm:
    1. If total records <= max_records_limit, do nothing
    2. If no records older than min_days_retention, do nothing
    3. Otherwise, delete up to deletion_batch_size oldest records
       that are older than min_days_retention

    Rate limiting is achieved by only deleting deletion_batch_size records
    per call, spreading the load across multiple cleanup cycles.
    """

    def __init__(self, queryset: QuerySet, date_field_name: str,
                 min_days_retention: int = 30,
                 max_records_limit: int = 100000,
                 deletion_batch_size: int = 1000):
        """
        Initialize the history table manager with configuration.

        Args:
            queryset: Django QuerySet for the history table
            date_field_name: Name of the datetime field for age-based cleanup
            min_days_retention: Minimum days to retain records (default: 30)
            max_records_limit: Maximum records to retain (default: 100000)
            deletion_batch_size: Records to delete per cycle (default: 1000)
        """
        self.queryset = queryset
        self.date_field_name = date_field_name
        self.min_days_retention = min_days_retention
        self.max_records_limit = max_records_limit
        self.deletion_batch_size = deletion_batch_size

        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def cleanup_next_batch(self) -> CleanupResult:
        """
        Clean up the next batch of old records if needed.

        This method implements rate-limited cleanup by only processing
        a single batch per call. It follows this algorithm:

        1. Check if total records <= max_records_limit (do nothing if under limit)
        2. Check if any records older than min_days_retention exist
        3. Delete up to deletion_batch_size of the oldest records that are
           older than min_days_retention

        This ensures:
        - Records within min_days_retention are NEVER deleted regardless of count
        - Cleanup load is spread across multiple cycles (rate limiting)
        - Maximum history is retained while respecting limits

        Returns:
            CleanupResult: Result containing deletion count, reason, and performance metrics
        """
        start_time = datetimeproxy.now()
        table_name = self.queryset.model._meta.db_table
        self._logger.debug(f"Starting cleanup batch for table '{table_name}'")

        try:
            # Check if we're over the total record limit
            total_count = self._get_record_count()

            if total_count <= self.max_records_limit:
                self._logger.debug(
                    f"Under limit: {total_count} records <= {self.max_records_limit} limit "
                    f"for table '{table_name}'"
                )
                return CleanupResult(
                    deleted_count=0,
                    result_type=CleanupResultType.UNDER_LIMIT,
                    reason="All tables under limits",
                    duration_seconds=(datetimeproxy.now() - start_time).total_seconds()
                )

            # Find records older than retention period
            cutoff_date = datetimeproxy.now() - timedelta(days=self.min_days_retention)

            old_records_qs = self.queryset.filter(
                **{f"{self.date_field_name}__lt": cutoff_date}
            ).order_by(self.date_field_name)

            # Check if there are any old records eligible for deletion
            if not old_records_qs.exists():
                self._logger.debug(
                    f"No records older than {cutoff_date} ({self.min_days_retention} days) "
                    f"for table '{table_name}'"
                )
                return CleanupResult(
                    deleted_count=0,
                    result_type=CleanupResultType.NO_OLD_RECORDS,
                    reason="No old records to clean",
                    duration_seconds=(datetimeproxy.now() - start_time).total_seconds()
                )

            # Get IDs of next batch to delete (oldest first)
            ids_to_delete = list(old_records_qs.values_list('pk', flat=True)[:self.deletion_batch_size])

            if not ids_to_delete:
                self._logger.debug(f"No record IDs found for deletion in table '{table_name}'")
                return CleanupResult(
                    deleted_count=0,
                    result_type=CleanupResultType.NO_OLD_RECORDS,
                    reason="No old records to clean",
                    duration_seconds=(datetimeproxy.now() - start_time).total_seconds()
                )

            # Delete the batch
            deleted_count = self._delete_records(ids_to_delete)
            duration = (datetimeproxy.now() - start_time).total_seconds()

            self._logger.debug(
                f"Deleted {deleted_count} records in {duration:.3f}s "
                f"from table '{table_name}' (had {total_count} records, batch size {self.deletion_batch_size})"
            )

            return CleanupResult(
                deleted_count=deleted_count,
                result_type=CleanupResultType.CLEANUP_PERFORMED,
                reason=f"Cleaned {deleted_count} records in {duration:.1f}s",
                duration_seconds=duration
            )

        except Exception as e:
            duration = (datetimeproxy.now() - start_time).total_seconds()
            self._logger.exception(f"Error during cleanup batch for table '{table_name}': {e}")
            # Re-raise to let caller handle the error
            raise

    def _get_record_count(self) -> int:
        """
        Get the total number of records in the history table.

        Returns:
            int: Total record count
        """
        return self.queryset.count()

    def _delete_records(self, ids: List[int]) -> int:
        """
        Delete records with the given IDs in a single transaction.

        Args:
            ids: List of primary keys to delete

        Returns:
            int: Number of records actually deleted
        """
        if not ids:
            return 0

        table_name = self.queryset.model._meta.db_table

        with transaction.atomic():
            deleted_info = self.queryset.filter(pk__in=ids).delete()
            # Django's delete() returns a tuple: (total_deleted, {model: count_deleted})
            deleted_count = deleted_info[0] if deleted_info else 0

            self._logger.debug(
                f"Deleted {deleted_count} records from table '{table_name}' "
                f"with IDs: {ids[:5]}{'...' if len(ids) > 5 else ''}"
            )
            return deleted_count