"""
Transient (non-persisted) models for the ATTRIBUTE_REFERENCE
capability.

``AttributeReferenceResult`` is the picker-only view of an upstream
document or other linkable resource: shown in the search modal,
selected by the operator, and discarded once the resulting
``EntityAttribute`` / ``LocationAttribute`` row is created. Only
``title`` and ``source_url`` survive into persistent storage; the
remaining fields exist solely for picker UX.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class AttributeReferenceResult:
    """One row in the picker's result list.

    ``title`` and ``source_url`` are the only fields that survive
    the attach step — they become the attribute's ``name`` and
    ``value`` respectively. Everything else is picker chrome.
    """
    title: str
    source_url: str
    thumbnail_url: Optional[str] = None
    mime_type: Optional[str] = None
    snippet: Optional[str] = None


class WireField:
    """Request and response field names for the picker's REST
    endpoints. Centralized so the wire-shape is grep-able from one
    place and the search + attach views can't drift apart on
    field names. Any rename here is a breaking change for the
    picker JS."""
    # Search request
    QUERY            = 'query'
    LIMIT            = 'limit'
    # Attach request
    ITEM_TYPE        = 'item_type'
    ITEM_ID          = 'item_id'
    SELECTIONS       = 'selections'
    SELECTION_TITLE  = 'title'
    SELECTION_URL    = 'source_url'
    # Search response
    RESULTS          = 'results'
    ERROR            = 'error'
    # Attach response
    CREATED_COUNT    = 'created_count'
    CREATED_IDS      = 'created_attribute_ids'
