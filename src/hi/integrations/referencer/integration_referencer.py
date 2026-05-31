"""
Per-integration EXTERNAL_REFERENCE base class.

Each integration that advertises
``IntegrationCapability.EXTERNAL_REFERENCE`` provides a concrete
subclass and returns an instance from
``IntegrationGateway.get_external_referencer()``. The framework
owns the picker UI, attach dispatcher, and the
EntityExternalReference / LocationExternalReference tables; the
integration participates by (a) translating a search query into
``ExternalReferenceResult`` candidates and (b) attaching selected
candidates as rows on those tables, fetching thumbnail bytes from
upstream as part of attach.
"""

from typing import List, Optional

from hi.integrations.capability_gateway import CapabilityGateway
from hi.integrations.enums import IntegrationCapability
from hi.integrations.models import IntegrationAttribute
from hi.integrations.transient_models import IntegrationValidationResult

from .transient_models import (
    ExternalReferenceAttachBatchOutcome,
    ExternalReferenceResult,
    ExternalReferenceSearchResult,
)


class IntegrationExternalReferencer( CapabilityGateway ):

    """Search-and-attach surface contributed by integrations that
    expose a queryable corpus of linkable resources (documents,
    pages, files in an external CMS, etc.). The framework calls
    ``search_references`` from the picker view and presents the
    returned candidates to the operator for multi-select attach."""

    capability = IntegrationCapability.EXTERNAL_REFERENCE

    def validate_configuration(
            self,
            integration_attributes: List[IntegrationAttribute],
    ) -> IntegrationValidationResult:
        """Schema-only validation of the proposed configuration.
        Must NOT perform network operations."""
        raise NotImplementedError('Subclasses must override this method')

    def search_references(
            self,
            query: str,
            limit: int = 20,
    ) -> ExternalReferenceSearchResult:
        """Query the upstream corpus and return up to ``limit``
        candidates wrapped in an
        ``ExternalReferenceSearchResult``. Operators see the
        returned list rendered as cards (thumbnail/mime-icon +
        title + snippet + clickable source URL); multi-selecting
        any subset attaches them via ``attach_references`` on the
        host Entity or Location.

        Implementations should:
          - Return ``ExternalReferenceSearchResult(results=[])``
            when the query yields no matches (no ``error_message``).
          - Populate ``error_message`` when the upstream call fails
            (auth rejected, unreachable, etc.) so the picker
            surfaces a banner instead of "No results.". The picker
            stays usable across failures; do not raise.
          - Honor ``limit`` as an upper bound (the picker uses a
            user-selectable page-size 20/50/100).
          - Order results by upstream relevance (most-relevant
            first); the picker preserves this order.
          - Not raise on empty/whitespace queries; return
            ``ExternalReferenceSearchResult(results=[])``.
        """
        raise NotImplementedError('Subclasses must override this method')

    def attach_references(
            self,
            owner,
            selections: List[ExternalReferenceResult],
    ) -> ExternalReferenceAttachBatchOutcome:
        """Attach the operator-selected upstream items as
        ExternalReference rows on the given owner (Entity or
        Location). Each ``selection`` carries an ``integration_key``
        identifying the upstream item, plus the title / source_url /
        mime_type needed for the row.

        Returns one ``ExternalReferenceAttachOutcome`` per selection
        wrapped in an ``ExternalReferenceAttachBatchOutcome``. The
        framework dispatcher merges these across integrations into
        a single composite for the view; the view chooses the next
        modal (entity/location edit on full success, error modal
        otherwise) from the aggregate counts.

        Implementations should:
          - Fetch thumbnail bytes from upstream where available;
            on failure fall through to an HI-generated thumbnail
            from upstream original bytes (when the integration can
            expose them and the mime type is supported); on full
            failure, attach the row anyway with no thumbnail. The
            row attach is the primary user goal -- placeholder
            rendering covers the no-thumbnail case. A missing
            thumbnail is NOT a failure outcome.
          - Use ``self._manager_for_owner(owner).create_or_update(...)``
            to perform the per-row upsert via the framework manager.
          - Tolerate individual selection failures: per-selection
            exceptions become ``success=False`` outcomes with an
            operator-readable ``error_message``; they must not abort
            the rest of the batch.
        """
        raise NotImplementedError('Subclasses must override this method')

    @staticmethod
    def _manager_for_owner(owner):
        """Resolve the framework external-reference manager for the
        given owner type. Imported lazily to avoid pulling the
        Entity / Location models into framework module-load order
        prematurely."""
        from hi.apps.entity.models import Entity
        from hi.integrations.models import (
            EntityExternalReference,
            LocationExternalReference,
        )
        if isinstance(owner, Entity):
            return EntityExternalReference.objects
        return LocationExternalReference.objects

    def get_attribute_actions_template_name(self) -> Optional[str]:
        """Per-capability template fragment to render in the
        integration attribute form's action bar. EXTERNAL_REFERENCE
        contributes the enabled/disabled status badge plus the
        Disable button. Individual integrations can override to
        substitute their own fragment."""
        return 'integrations/referencer/panes/attribute_actions.html'
