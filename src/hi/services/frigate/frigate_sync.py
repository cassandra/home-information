import logging
from typing import Optional

from hi.integrations.integration_synchronizer import IntegrationSynchronizer
from hi.integrations.sync_check import SyncDelta
from hi.integrations.sync_result import IntegrationSyncResult

from .frigate_metadata import FrigateMetaData
from .frigate_mixins import FrigateMixin

logger = logging.getLogger(__name__)


class FrigateSynchronizer( IntegrationSynchronizer, FrigateMixin ):
    """Drives the Frigate Import / Refresh workflow.

    Mirrors ``ZoneMinderSynchronizer`` in role: pulls the upstream
    camera list from Frigate (via ``/api/config`` since Frigate has no
    dedicated cameras endpoint), reconciles it against existing HI
    entities by integration_key, creates / updates / removes as
    needed. Per-camera entity creation produces a
    ``Entity(CAMERA, has_video_stream, has_video_snapshot)`` with a
    ``Movement`` sensor (MOVEMENT) and an ``ObjectPresence`` sensor
    (new OBJECT_PRESENCE state — added in feature work).

    Scaffolding stub: ``_sync_impl`` returns an empty result.
    """

    def get_integration_metadata(self):
        return FrigateMetaData

    def get_description(self, is_initial_import: bool) -> Optional[str]:
        if is_initial_import:
            return (
                'Each Frigate camera becomes a HI camera entity with motion'
                ' and object-presence sensors.'
            )
        return None

    async def check_needs_sync(self) -> Optional[ SyncDelta ]:
        """Sync-check probe (Issue #283 protocol). Scaffolding stub
        returns ``None`` (= "no drift"); feature work fetches the
        camera list and computes the delta against existing HI
        entities by integration_key."""
        return None

    def _sync_impl( self, is_initial_import : bool ) -> IntegrationSyncResult:
        result = IntegrationSyncResult(
            title = self.get_result_title( is_initial_import = is_initial_import ),
        )
        result.info_list.append(
            'Frigate sync not yet implemented (scaffolding).'
        )
        return result
