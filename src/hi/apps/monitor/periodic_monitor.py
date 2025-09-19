import asyncio
import logging
import threading
import time
from datetime import datetime
from typing import Dict, Optional

import hi.apps.common.datetimeproxy as datetimeproxy
from .transient_models import MonitorHealthStatus, ApiSourceHealth
from .enums import MonitorHealthStatusType, ApiSourceHealthStatusType

# For backwards compatibility
HealthStatusType = ApiSourceHealthStatusType


class PeriodicMonitor:
    """
    Base class for any content/information that should be automatically,
    and periodically updated from some external source.
    """

    def __init__( self, id: str, interval_secs: int ) -> None:
        self._id = id
        self._query_interval_secs = interval_secs
        self._query_counter = 0
        self._is_running = False
        self._logger = logging.getLogger(__name__)

        # Health tracking infrastructure
        self._health_lock = threading.Lock()
        self._health_status = MonitorHealthStatus(
            status=MonitorHealthStatusType.HEALTHY,  # Start optimistic
            last_check=datetimeproxy.now(),
        )

        self._logger.debug(f"Initialized: {self.__class__.__name__} with health tracking")
        return

    @property
    def id(self):
        return self._id

    @property
    def is_running(self):
        return self._is_running

    @property
    def health_status(self) -> MonitorHealthStatus:
        """Get current health status (thread-safe)."""
        with self._health_lock:
            # Return a copy to prevent external modification
            import copy
            return copy.deepcopy(self._health_status)
    
    async def start(self) -> None:
        self._is_running = True
        self._logger.info(f"{self.__class__.__name__} async task starting (interval: {self._query_interval_secs}s)")

        try:
            await self.initialize()
            self._update_health_status(MonitorHealthStatusType.HEALTHY, "Monitor initialized successfully")
            self._logger.info(f"{self.__class__.__name__} initialized successfully, entering monitoring loop")

            while self._is_running:
                try:
                    await self.run_query()
                    # Update heartbeat on successful cycle completion
                    self._update_monitor_heartbeat()
                except Exception as e:
                    self._logger.exception(f"Query execution failed in {self.__class__.__name__}: {e}")
                    self._record_error(f"Query execution failed: {str(e)}")
                    # Continue running despite individual query failures

                # Log sleep phase for debugging hanging issues
                self._logger.debug(f"{self.__class__.__name__} sleeping for {self._query_interval_secs}s")
                await asyncio.sleep(self._query_interval_secs)
                self._logger.debug(f"{self.__class__.__name__} woke up, checking if still running: {self._is_running}")

        except asyncio.CancelledError as ce:
            self._logger.info(f"{self.__class__.__name__} async task cancelled: {ce}")
            self._update_health_status(MonitorHealthStatusType.ERROR, "Monitor was cancelled")
            raise  # Re-raise to properly handle cancellation
        except Exception as e:
            self._logger.exception(f"{self.__class__.__name__} async task failed unexpectedly: {e}")
            self._update_health_status(MonitorHealthStatusType.ERROR, f"Monitor failed to start: {str(e)}")
            raise
        finally:
            self._logger.info(f"{self.__class__.__name__} async task cleaning up")
            await self.cleanup()
            self._logger.info(f"{self.__class__.__name__} async task stopped")
        return

    def stop(self) -> None:
        """Stops the monitor."""
        self._is_running = False
        self._logger.info(f"Stopping {self.__class__.__name__}...")
        return

    async def initialize(self) -> None:
        """
        Optional initialization logic to be implemented by subclasses.
        """
        self._logger.info(f"{self.__class__.__name__} initialized.")
        return
    
    async def run_query(self) -> None:
        self._query_counter += 1
        self._logger.debug(f"Running query {self._query_counter} for {self.__class__.__name__}")

        import hi.apps.common.datetimeproxy as datetimeproxy
        query_start_time = datetimeproxy.now()

        try:
            await self.do_work()
            query_duration = (datetimeproxy.now() - query_start_time).total_seconds()
            self._logger.debug(f"Query {self._query_counter} completed successfully in {query_duration:.2f}s")

            # Log warning if query is taking too long relative to interval
            if query_duration > (self._query_interval_secs * 0.5):
                self._logger.warning(f"Query {self._query_counter} took {query_duration:.2f}s, "
                                     f"which is over 50% of the {self._query_interval_secs}s interval")

        except Exception as e:
            query_duration = (datetimeproxy.now() - query_start_time).total_seconds()
            self._logger.exception(f"Query {self._query_counter} failed after {query_duration:.2f}s: {e}")
            # Don't re-raise - the monitor loop in start() will continue despite failures
        return

    async def do_work(self) -> None:
        """
        Abstract method for subclasses to implement specific periodic logic.
        """
        raise NotImplementedError("Subclasses must implement do_work()")

    async def cleanup(self) -> None:
        """
        Optional cleanup logic to be implemented by subclasses.
        """
        self._logger.info(f"{self.__class__.__name__} cleaned up.")
        return

    async def force_wake(self) -> None:
        self._logger.debug(f"Forcing immediate execution of {self.__class__.__name__}")
        await self.run_query()
        return

    # Health Status Management Methods

    def _update_health_status(self, status: MonitorHealthStatusType, error_message: Optional[str] = None) -> None:
        """Update the monitor's health status (thread-safe)."""
        with self._health_lock:
            self._health_status.status = status
            self._health_status.last_check = datetimeproxy.now()
            self._health_status.error_message = error_message

            if status.is_error:
                self._health_status.error_count += 1
            else:
                # Reset error count on successful status
                self._health_status.error_count = 0

        self._logger.debug(f"Health status updated to {status.label}: {error_message or 'No error'}")

    def _record_error(self, error_message: str) -> None:
        """Record an error and update health status accordingly."""
        # For now, all errors are treated as generic errors with the simplified enum
        # Future enhancement could add logic to determine WARNING vs ERROR severity
        if any(keyword in error_message.lower() for keyword in ['temporary', 'timeout', 'network']):
            status = MonitorHealthStatusType.WARNING
        else:
            status = MonitorHealthStatusType.ERROR

        self._update_health_status(status, error_message)

    def _update_monitor_heartbeat(self) -> None:
        """Update the monitor heartbeat timestamp (thread-safe)."""
        with self._health_lock:
            self._health_status.monitor_heartbeat = datetimeproxy.now()

        self._logger.debug(f"Monitor heartbeat updated")

    def register_api_source(self, source_id: str, source_name: str) -> None:
        """Register a new API source for health tracking."""
        api_source = ApiSourceHealth(
            source_id=source_id,
            source_name=source_name,
            status=ApiSourceHealthStatusType.HEALTHY  # Start optimistic
        )

        with self._health_lock:
            self._health_status.add_or_update_api_source(api_source)

        self._logger.debug(f"API source registered: {source_name} ({source_id})")

    def track_api_call(self, source_id: str, success: bool, response_time: Optional[float] = None, error_message: Optional[str] = None) -> None:
        """Track an API call result for health monitoring."""
        with self._health_lock:
            api_source = self._health_status.get_api_source(source_id)
            if not api_source:
                self._logger.warning(f"Attempted to track API call for unknown source: {source_id}")
                return

            # Update call statistics
            api_source.total_calls += 1
            if success:
                api_source.last_success = datetimeproxy.now()
                api_source.consecutive_failures = 0
                api_source.status = ApiSourceHealthStatusType.HEALTHY
            else:
                api_source.total_failures += 1
                api_source.consecutive_failures += 1

                # Use the enhanced enum logic to determine status based on metrics
                api_source.status = ApiSourceHealthStatusType.from_metrics(
                    consecutive_failures=api_source.consecutive_failures,
                    total_failures=api_source.total_failures,
                    total_requests=api_source.total_calls,
                    avg_response_time=api_source.average_response_time
                )

            # Update response time tracking
            if response_time is not None:
                api_source.last_response_time = response_time
                if api_source.average_response_time is None:
                    api_source.average_response_time = response_time
                else:
                    # Simple moving average (can be enhanced with more sophisticated algorithms)
                    api_source.average_response_time = (api_source.average_response_time * 0.8) + (response_time * 0.2)

        self._logger.debug(f"API call tracked - Source: {source_id}, Success: {success}, Response Time: {response_time}s")

    def get_api_source_health(self, source_id: str) -> Optional[ApiSourceHealth]:
        """Get health status for a specific API source."""
        with self._health_lock:
            return self._health_status.get_api_source(source_id)

    def get_all_api_sources_health(self) -> Dict[str, ApiSourceHealth]:
        """Get health status for all API sources."""
        with self._health_lock:
            return {api_source.source_id: api_source for api_source in self._health_status.api_sources}

    def mark_monitor_healthy(self, message: str = "Monitor operating normally") -> None:
        """Mark the monitor as healthy."""
        self._update_health_status(MonitorHealthStatusType.HEALTHY, message)

    def mark_monitor_error(self, error_type: MonitorHealthStatusType, error_message: str) -> None:
        """Mark the monitor as having an error."""
        if error_type not in (MonitorHealthStatusType.WARNING, MonitorHealthStatusType.ERROR):
            self._logger.warning(f"Attempted to mark monitor as error with non-error status: {error_type}")
            return
        self._update_health_status(error_type, error_message)
