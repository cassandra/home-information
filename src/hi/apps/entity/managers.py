from django.db.models import Q

from hi.integrations.managers import IntegrationDetailsModelManager


class EntityModelManager( IntegrationDetailsModelManager ):

    def with_live_view( self ):
        """Entities that have *any* current visual — native stream or
        snapshot. Mirrors the ``has_live_view`` property in queryset
        form for filter sites."""
        return self.filter(
            Q( has_video_stream = True ) | Q( has_video_snapshot = True )
        )

    def external_for( self, integration_id, integration_name = None ):
        """Entities currently attached to ``integration_id`` (i.e.,
        data_source=EXTERNAL — live Connect mode). Optional
        ``integration_name`` narrows to a specific upstream item."""
        queryset = self.filter( integration_id = integration_id )
        if integration_name is not None:
            queryset = queryset.filter( integration_name = integration_name )
        return queryset

    # Imported and detached entities currently share the same column
    # shape — both are HI-owned rows that carry upstream provenance
    # on previous_integration_*. The two predicates below resolve to
    # the same query today, but each call site asks for what it
    # *semantically* needs:
    #
    #   * ``imported_for``: "Import-side wants rows it created or
    #     would skip on re-import."
    #   * ``detached_for``: "the auto-reconnect path wants rows that
    #     used to be Connect-attached."
    #
    # Keeping them as distinct methods documents intent at every call
    # site, and lets a future discriminator (e.g., a provenance flag)
    # be added in one place without changing readers.

    def imported_for( self, integration_id, integration_name = None ):
        """Entities created by IMPORT mode for this integration (HI-
        owned, carrying upstream provenance). Optional
        ``integration_name`` narrows by the previous-pair name."""
        return self._with_provenance_to( integration_id, integration_name )

    def detached_for( self, integration_id, integration_name = None ):
        """Entities detached from this integration via SAFE-disable
        (HI-owned, carrying upstream provenance — auto-reconnect
        candidates). Optional ``integration_name`` narrows by the
        previous-pair name."""
        return self._with_provenance_to( integration_id, integration_name )

    def _with_provenance_to( self, integration_id, integration_name ):
        queryset = self.filter(
            integration_id__isnull = True,
            previous_integration_id = integration_id,
        )
        if integration_name is not None:
            queryset = queryset.filter(
                previous_integration_name = integration_name,
            )
        return queryset

    def with_integration_provenance( self, integration_id ):
        """Entities associated with ``integration_id`` in any state
        (EXTERNAL, imported, or detached). Use when the data-source
        distinction is irrelevant — e.g., 'does this integration
        have any entities at all?'"""
        return self.filter(
            Q( integration_id = integration_id )
            | Q( previous_integration_id = integration_id )
        )
