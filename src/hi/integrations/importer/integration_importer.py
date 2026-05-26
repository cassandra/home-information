"""
Per-integration importer base class.

Parallel to IntegrationConnector (Connect-capability). Each
IMPORT-capable integration provides a concrete subclass and returns
an instance from IntegrationGateway.get_importer(). The framework
owns the import workflow (Data Import page, configure modal,
preview, confirm, result modal, post-import placement); the
importer participates by supplying the integration-specific
candidate-listing, item ingest, and discard operations.
"""
from typing import List

from hi.integrations.models import IntegrationAttribute
from hi.integrations.transient_models import (
    IntegrationMetaData,
    IntegrationValidationResult,
)

from .transient_models import (
    CandidateItem,
    IntegrationDiscardResult,
    IntegrationImportResult,
)


class IntegrationImporter:

    def get_metadata(self) -> IntegrationMetaData:
        raise NotImplementedError('Subclasses must override this method')

    def validate_configuration(
            self,
            integration_attributes: List[IntegrationAttribute],
    ) -> IntegrationValidationResult:
        """Schema-only validation of the proposed configuration. Must
        NOT perform network operations. Mirrors IntegrationGateway's
        contract for the same operation on the Connect side."""
        raise NotImplementedError('Subclasses must override this method')

    def get_candidate_items(self) -> List[CandidateItem]:
        """Synchronously fetch the upstream items that would be
        candidates for import. Used for the preview-step count
        ("would import N, would skip M"). Implementations filter out
        items already present in HI (by integration_name match)."""
        raise NotImplementedError('Subclasses must override this method')

    def run_import(self) -> IntegrationImportResult:
        """Execute the import. Re-fetches upstream detail per
        candidate, creates HI entities + attributes, populates
        attachments. Per-entity transaction so a single-item failure
        does not abort the batch."""
        raise NotImplementedError('Subclasses must override this method')

    def discard_imported_data(self, integration_id: str) -> IntegrationDiscardResult:
        """Remove all entities previously imported under this
        integration_id. Filters by data_source=INTERNAL so that
        Connect-mode entities (if somehow coexisting) stay
        untouched."""
        raise NotImplementedError('Subclasses must override this method')
