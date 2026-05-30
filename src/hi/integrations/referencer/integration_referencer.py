"""
Per-integration ATTRIBUTE_REFERENCE base class.

Each integration that advertises
``IntegrationCapability.ATTRIBUTE_REFERENCE`` provides a concrete
subclass and returns an instance from
``IntegrationGateway.get_attribute_referencer()``. The framework
owns the picker UI, attach lifecycle, and TEXT-attribute creation;
the integration participates by translating a search query into a
list of ``AttributeReferenceResult`` candidates.
"""

from typing import List, Optional

from hi.integrations.capability_gateway import CapabilityGateway
from hi.integrations.enums import IntegrationCapability
from hi.integrations.models import IntegrationAttribute
from hi.integrations.transient_models import IntegrationValidationResult

from .transient_models import AttributeReferenceSearchResult


class IntegrationAttributeReferencer( CapabilityGateway ):

    """Search-and-attach surface contributed by integrations that
    expose a queryable corpus of linkable resources (documents,
    pages, files in an external CMS, etc.). The framework calls
    ``search_references`` from the picker view and presents the
    returned candidates to the operator for multi-select attach."""

    capability = IntegrationCapability.ATTRIBUTE_REFERENCE

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
    ) -> AttributeReferenceSearchResult:
        """Query the upstream corpus and return up to ``limit``
        candidates wrapped in an
        ``AttributeReferenceSearchResult``. Operators see the
        returned list rendered as cards (thumbnail/mime-icon +
        title + snippet + clickable source URL); multi-selecting
        any subset attaches them as TEXT attributes on the host
        Entity or Location.

        Implementations should:
          - Return ``AttributeReferenceSearchResult(results=[])``
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
            ``AttributeReferenceSearchResult(results=[])``.
        """
        raise NotImplementedError('Subclasses must override this method')

    def get_attribute_actions_template_name(self) -> Optional[str]:
        """Per-capability template fragment to render in the
        integration attribute form's action bar. ATTRIBUTE_REFERENCE
        contributes the enabled/disabled status badge plus the
        Disable button. Individual integrations can override to
        substitute their own fragment."""
        return 'integrations/referencer/panes/attribute_actions.html'
