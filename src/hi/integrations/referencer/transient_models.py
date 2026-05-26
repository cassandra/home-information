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
    """Form field names exchanged between the picker template and
    the picker view. Centralized so template + view can't drift
    on field names. Any rename here is a breaking change for the
    picker template."""
    # Routing fields (carried in GET query / POST body)
    ITEM_TYPE        = 'item_type'
    ITEM_ID          = 'item_id'
    # Which referencer integration drives the current search.
    # Hidden input on POST; defaults to the first configured
    # integration on initial GET.
    INTEGRATION_ID   = 'integration_id'
    # Search controls
    QUERY            = 'query'
    LIMIT            = 'limit'
    # Action discriminator (submit-button ``name=action`` values)
    ACTION           = 'action'
    ACTION_ATTACH    = 'attach'
    # Multi-select state
    SELECTIONS_JSON  = 'selections_json'   # canonical list, hidden input
    VISIBLE_URL      = 'visible_url'       # hidden input per visible result
    RESULT_URL       = 'result_url'        # checkbox value per visible result
    REMOVE_URL       = 'remove_url'        # chip-X button value
    # Per-selection record keys (inside SELECTIONS_JSON)
    SELECTION_TITLE  = 'title'
    SELECTION_URL    = 'source_url'
