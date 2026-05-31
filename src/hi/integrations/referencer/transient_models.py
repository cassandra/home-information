"""
Transient (non-persisted) models for the EXTERNAL_REFERENCE
capability.

``ExternalReferenceResult`` is the picker-only view of an upstream
document or other linkable resource: shown in the search modal,
selected by the operator, and discarded once the resulting
``EntityAttribute`` / ``LocationAttribute`` row is created. Only
``title`` and ``source_url`` survive into persistent storage; the
remaining fields exist solely for picker UX.

``ExternalReferenceSearchResult`` is the wrapper returned by
``IntegrationExternalReferencer.search_references``. It carries the
result list plus an optional ``error_message`` so the picker can
distinguish a legitimately-empty search from an upstream failure
(auth rejected, unreachable, etc.) and surface a banner instead of
the "No results." string.

Wire-format strings (form field names, JSON record keys) shared
between the picker views, templates, and ``external-reference-picker.js`` live in
``hi.constants.DIVID`` (mirrored in ``static/js/main.js``). See the
``REF_PICKER_*`` entries there.
"""

from dataclasses import dataclass, field
from typing import List, Optional

from hi.integrations.transient_models import IntegrationKey


@dataclass(frozen=True)
class ExternalReferenceResult:
    """One upstream item, carried from search through attach.

    Surfaces in the picker's result list (rendered as a card with
    ``thumbnail_url`` + ``title`` + ``snippet`` + clickable
    ``source_url``); operator selection turns it into the input to
    the integration's ``attach_references``, which persists a row
    using ``integration_key``, ``title``, ``source_url``, and
    ``mime_type``. ``thumbnail_url`` and ``snippet`` are picker
    chrome and unused at attach time.
    """
    integration_key: IntegrationKey
    title: str
    source_url: str
    thumbnail_url: Optional[str] = None
    mime_type: Optional[str] = None
    snippet: Optional[str] = None


@dataclass(frozen=True)
class ExternalReferenceSearchResult:
    """``error_message`` is None on success, including the legitimate
    empty-results case. A non-None value signals upstream failure
    even when ``results`` is empty."""
    results: List[ExternalReferenceResult] = field(default_factory=list)
    error_message: Optional[str] = None


@dataclass(frozen=True)
class ExternalReferenceAttachOutcome:
    """One operator-selection's attach outcome.

    ``success=False`` means the row did not persist; the operator's
    intent for this selection was not fulfilled. ``error_message``
    explains why. Identity fields (integration_key, title) aren't
    carried -- the error modal shows aggregate counts and per-failure
    messages only, not per-item identification.
    """
    success: bool
    error_message: Optional[str] = None


@dataclass(frozen=True)
class ExternalReferenceAttachBatchOutcome:
    """Composite result of one attach submission: every selection
    contributes exactly one outcome, regardless of which integration
    processed it. Returned from ``attach_references`` for a single
    integration, and from the dispatcher's merged result across all
    integrations in one operator submission."""
    outcomes: List[ExternalReferenceAttachOutcome] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.outcomes)

    @property
    def success_count(self) -> int:
        return sum(1 for o in self.outcomes if o.success)

    @property
    def failure_count(self) -> int:
        return self.total - self.success_count

    @property
    def has_failures(self) -> bool:
        return self.failure_count > 0

    @property
    def error_messages(self) -> List[str]:
        return [o.error_message for o in self.outcomes
                if not o.success and o.error_message]
