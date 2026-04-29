"""
Per-integration synchronizer base class.

The general integration framework owns the sync workflow (pre-sync
confirmation modal, sync execution view, post-sync dispatcher modal).
The synchronizer is the per-integration participant that the framework
hands off to for the integration-specific work plus a small amount of
peripheral metadata the framework surfaces alongside.

Each integration that supports sync provides a concrete subclass and
returns an instance of it from `IntegrationGateway.get_synchronizer()`.
Sync is opt-in: a gateway whose integration does not support sync
returns None.
"""
import logging
from typing import Optional

from hi.apps.common.database_lock import ExclusionLockContext
from hi.apps.common.processing_result import ProcessingResult

logger = logging.getLogger(__name__)


class IntegrationSynchronizer:
    """
    Base class for per-integration synchronizers.

    The framework calls `sync()`. The base implementation acquires a
    process-wide synchronization lock, delegates to the subclass's
    `_sync_impl()`, and converts unexpected RuntimeError into a result
    object. Subclasses implement the integration-specific work in
    `_sync_impl()` and the small metadata accessors below.

    Synchronization is process-wide rather than per-integration: at
    most one integration sync runs at a time. Concurrent syncs across
    integrations could race over shared infrastructure (entity tables,
    location-view bookkeeping in later phases) and the user is unlikely
    to need parallelism here. Override at a subclass level if a future
    integration genuinely needs concurrent sync.
    """

    # Single shared lock name across all integration syncs. See class
    # docstring above for the rationale.
    SYNCHRONIZATION_LOCK_NAME = 'integrations_sync'

    def get_description(self, is_initial_import: bool) -> Optional[str]:
        """
        Optional copy describing what this integration's sync will do,
        surfaced to the operator in the framework's pre-sync
        confirmation modal alongside a generic lead message.

        `is_initial_import` distinguishes the first-time IMPORT (no
        entities have been imported yet) from subsequent REFRESH
        operations. The two contexts mean different things to the
        operator and integrations are encouraged to provide tailored
        copy for each. Return None to render only the generic lead
        text.
        """
        return None

    def get_result_title(self) -> str:
        """
        Human-readable title for the sync result (used in the result
        modal header). Subclasses must override.
        """
        raise NotImplementedError('Subclasses must override this method')

    def sync(self) -> ProcessingResult:
        """
        Public entry point used by the framework. Wraps `_sync_impl`
        with the sync lock and standard error handling. Subclasses
        override `_sync_impl` rather than this method.
        """
        try:
            with ExclusionLockContext(name=self.SYNCHRONIZATION_LOCK_NAME):
                logger.debug(f'{self.__class__.__name__} sync started.')
                return self._sync_impl()
        except RuntimeError as e:
            logger.exception(e)
            return ProcessingResult(
                title=self.get_result_title(),
                error_list=[str(e)],
            )
        finally:
            logger.debug(f'{self.__class__.__name__} sync ended.')

    def _sync_impl(self) -> ProcessingResult:
        """
        Integration-specific sync work. Subclasses must override.
        Called with the synchronization lock held.
        """
        raise NotImplementedError('Subclasses must override this method')
