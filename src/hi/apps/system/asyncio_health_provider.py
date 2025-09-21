"""
Wrapper utility to convert BackgroundTaskMonitor status to HealthStatusProvider.

This provides a bridge between hi.apps.common.asyncio_utils.BackgroundTaskMonitor
and hi.apps.system.health_status.HealthStatus without creating circular dependencies.
"""

import logging

from hi.apps.common.asyncio_utils import BackgroundTaskMonitor
from .enums import HealthStatusType
from .health_status_provider import HealthStatusProvider
from .provider_info import ProviderInfo


logger = logging.getLogger(__name__)


class AsyncioHealthStatusProvider( HealthStatusProvider ):

    def __init__(self):
        super().__init__()
        self._initialize_health_status()
        return
    
    @classmethod
    def get_provider_info(cls) -> ProviderInfo:
        return ProviderInfo(
            provider_id='hi.apps.system.background_tasks',
            provider_name='Background Task Monitor',
            description='System background tasks and async operations'
        )

    def _initialize_health_status(self):
        """Convert BackgroundTaskMonitor status to HealthStatus.
        """
        try:
            async_diagnostics = BackgroundTaskMonitor.get_background_task_status()

            status_type = HealthStatusType.HEALTHY
            message = None

            if not async_diagnostics:
                status_type = HealthStatusType.UNKNOWN
                message = "Unable to retrieve background task status"
            else:
                main_thread = async_diagnostics.get('main_thread', {})
                if not main_thread.get('is_alive'):
                    status_type = HealthStatusType.ERROR
                    message = "Main thread is not alive"

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
                        message = f"Dead threads: {', '.join(dead_tasks)}"
                    elif stopped_loops:
                        status_type = HealthStatusType.WARNING
                        message = f"Stopped event loops: {', '.join(stopped_loops)}"

            self.update_health_status(
                status = status_type,
                last_message = message,
            )
        except Exception as e:
            logger.exception("Failed to get background task health status")
            self.update_health_status(
                status = HealthStatusType.ERROR,
                last_message = f"Failed to retrieve status: {str(e)}",
            )
        return
