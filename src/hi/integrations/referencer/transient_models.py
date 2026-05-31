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
between the picker views, templates, and ``attr-picker.js`` live in
``hi.constants.DIVID`` (mirrored in ``static/js/main.js``). See the
``ATTR_PICKER_*`` entries there.
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
