"""
Wrapper utility to convert BackgroundTaskMonitor status to HealthStatus.

This provides a bridge between hi.apps.common.asyncio_utils.BackgroundTaskMonitor
and hi.apps.system.health_status.HealthStatus without creating circular dependencies.
"""

import logging

import hi.apps.common.datetimeproxy as datetimeproxy
from hi.apps.common.asyncio_utils import BackgroundTaskMonitor
from .enums import HealthStatusType
from .health_status import HealthStatus
from .provider_info import ProviderInfo


logger = logging.getLogger(__name__)


class AsyncioHealthStatusProvider:
    """Provides HealthStatus for background tasks and async operations."""

    @staticmethod
    def get_provider_info() -> ProviderInfo:
        """Get provider information for background task monitoring."""
        return ProviderInfo(
            provider_id='hi.apps.system.background_tasks',
            provider_name='Background Task Monitor',
            description='System background tasks and async operations'
        )

    @staticmethod
    def get_health_status() -> HealthStatus:
        """Convert BackgroundTaskMonitor status to HealthStatus.

        Returns:
            HealthStatus representing the health of background tasks.
        """
        try:
            async_diagnostics = BackgroundTaskMonitor.get_background_task_status()

            # Determine overall health status
            status_type = HealthStatusType.HEALTHY
            error_message = None

            if not async_diagnostics:
                status_type = HealthStatusType.UNKNOWN
                error_message = "Unable to retrieve background task status"
            else:
                # Check main thread health
                main_thread = async_diagnostics.get('main_thread', {})
                if not main_thread.get('is_alive'):
                    status_type = HealthStatusType.ERROR
                    error_message = "Main thread is not alive"

                # Check background task health if main thread is OK
                if status_type == HealthStatusType.HEALTHY:
                    background_tasks = async_diagnostics.get('background_tasks', {})
                    dead_tasks = []
                    stopped_loops = []

                    for task_name, task_info in background_tasks.items():
                        thread = task_info.get('thread', {})
                        if not thread.get('is_alive'):
                            dead_tasks.append(task_name)

                        event_loop = task_info.get('event_loop', {})
                        if event_loop.get('exists') and not event_loop.get('is_running'):
                            stopped_loops.append(task_name)

                    if dead_tasks:
                        status_type = HealthStatusType.ERROR
                        error_message = f"Dead threads: {', '.join(dead_tasks)}"
                    elif stopped_loops:
                        status_type = HealthStatusType.WARNING
                        error_message = f"Stopped event loops: {', '.join(stopped_loops)}"

            # Create HealthStatus instance
            provider_info = AsyncioHealthStatusProvider.get_provider_info()
            health_status = HealthStatus(
                provider_id=provider_info.provider_id,
                provider_name=provider_info.provider_name,
                status=status_type,
                last_check=datetimeproxy.now(),
                error_message=error_message
            )

            # Set heartbeat to now since we just checked
            health_status.heartbeat = datetimeproxy.now()

            return health_status

        except Exception as e:
            logger.exception("Failed to get background task health status")
            # Return error status on exception
            provider_info = AsyncioHealthStatusProvider.get_provider_info()
            return HealthStatus(
                provider_id=provider_info.provider_id,
                provider_name=provider_info.provider_name,
                status=HealthStatusType.ERROR,
                last_check=datetimeproxy.now(),
                error_message=f"Failed to retrieve status: {str(e)}"
            )