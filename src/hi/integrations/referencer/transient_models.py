"""
Transient (non-persisted) models for the ATTRIBUTE_REFERENCE
capability.

``AttributeReferenceResult`` is the picker-only view of an upstream
document or other linkable resource: shown in the search modal,
selected by the operator, and discarded once the resulting
``EntityAttribute`` / ``LocationAttribute`` row is created. Only
``title`` and ``source_url`` survive into persistent storage; the
remaining fields exist solely for picker UX.

Wire-format strings (form field names, JSON record keys) shared
between the picker views, templates, and ``attr-picker.js`` live in
``hi.constants.DIVID`` (mirrored in ``static/js/main.js``). See the
``ATTR_PICKER_*`` entries there.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class AttributeReferenceResult:
    """One row in the picker's result list.

    ``title`` and ``source_url`` are the only fields that survive
    the attach step -- they become the attribute's ``name`` and
    ``value`` respectively. Everything else is picker chrome.
    """
    title: str
    source_url: str
    thumbnail_url: Optional[str] = None
    mime_type: Optional[str] = None
    snippet: Optional[str] = None
