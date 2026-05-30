"""
Default sync-preview construction.

The connector base class declares the interface (``sync_preview`` /
``_sync_preview_impl``); the business logic of the framework-default
preview lives here as a namespace class. Per-integration
``_sync_preview_impl`` overrides either bypass this module entirely
(for higher-fidelity previews) or call ``build_from_check`` and
post-process the result.

The default preview's fidelity is bounded by what ``check_needs_sync``
(the periodic drift probe) can return -- a set of added and removed
``IntegrationKey``s. The framework can accurately bucket removals
into ``removed_list`` / ``detached_list`` per the operator's policy
(HI-side entities are queryable and classifiable here); it cannot
predict updates or reconnects, and has no source for upstream-side
display names. ``approximation_message`` names these gaps so the
operator sees what isn't predicted.
"""
import logging

from asgiref.sync import async_to_sync

from hi.apps.entity.models import Entity

from .sync_result import IntegrationSyncPreviewResult
from .user_data_detector import EntityUserDataDetector

logger = logging.getLogger(__name__)


class IntegrationSyncPreviewer:
    """Namespace for the default preview construction. Class methods
    rather than module-level functions so call sites carry the
    ``IntegrationSyncPreviewer.`` prefix and group naturally.
    """

    APPROXIMATION_MESSAGE = (
        "This preview detects upstream additions and removals via the "
        "integration's drift check. Update and reconnect detection are "
        "not predicted by this preview."
    )
    NO_PREVIEW_MESSAGE = (
        'This integration does not provide a preview implementation.'
    )

    @classmethod
    def build_from_check( cls,
                          check_needs_sync_callable,
                          result_title       : str,
                          preserve_user_data : bool,
                          ) -> IntegrationSyncPreviewResult:
        """Run the integration's ``check_needs_sync`` probe and massage
        the returned ``SyncDelta`` into an
        ``IntegrationSyncPreviewResult``. Returns an empty result with
        the no-preview message when the integration opts out of
        ``check_needs_sync``.

        ``check_needs_sync_callable`` is the connector's bound method
        (still async); this layer crosses the async/sync boundary so
        callers stay in normal sync flow.

        Failures from the probe (upstream unreachable, auth expired,
        client unavailable) are caught and surfaced via
        ``error_list`` rather than propagated -- otherwise the
        operator would see the preview-result modal's "Nothing new"
        branch when in fact the check itself failed to run.
        """
        result = IntegrationSyncPreviewResult( title = result_title )

        try:
            delta = async_to_sync( check_needs_sync_callable )()
        except Exception as e:
            logger.exception( 'check_needs_sync raised during preview' )
            result.error_list.append( str(e) or e.__class__.__name__ )
            return result

        if delta is None:
            result.approximation_message = cls.NO_PREVIEW_MESSAGE
            return result

        cls._populate_added( result = result, delta = delta )
        cls._populate_removed(
            result = result,
            delta = delta,
            preserve_user_data = preserve_user_data,
        )
        result.approximation_message = cls.APPROXIMATION_MESSAGE
        return result

    @staticmethod
    def _populate_added( result : IntegrationSyncPreviewResult, delta ):
        """Created items: count + technical keys. Display names are not
        available from this layer -- the upstream side is opaque to the
        framework, and ``check_needs_sync`` only returns
        ``IntegrationKey`` instances. The technical names surface
        behind a collapsed debug section in the preview-result modal
        so the operator can verify what would be created without
        committing to sync; placeholder entries in ``created_list``
        keep the stat-card count consistent with the upstream count.
        """
        if not delta.added:
            return
        result.upstream_added_keys = sorted(
            k.integration_name for k in delta.added
        )
        result.created_list = [ '' ] * len( delta.added )
        return

    @staticmethod
    def _populate_removed( result             : IntegrationSyncPreviewResult,
                           delta,
                           preserve_user_data : bool ):
        """Removed items: bucket each HI-side entity per policy, matching
        what a real sync's removal pass would do for these keys.
        Entities classified by ``EntityUserDataDetector`` -- the same
        classifier the sync uses, so the bucketing is faithful to what
        Refresh would actually produce.
        """
        if not delta.removed:
            return
        removed_entities = (
            Entity.objects.filter_by_integration_keys( list( delta.removed ))
        )
        for entity in removed_entities:
            if preserve_user_data and EntityUserDataDetector.has_user_created_attributes( entity ):
                result.detached_list.append( entity.name )
            else:
                result.removed_list.append( entity.name )
        return
