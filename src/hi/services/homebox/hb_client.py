"""HomeBox API client facade.

Delegates to a version-specific backend (``_HbLegacyBackend`` for
``/v1/items/*``, ``_HbEntitiesBackend`` for ``/v1/entities/*``).
Today's wiring is legacy-only; #373 Phase 3 adds the entities
backend and a version probe at construction time so HI works
against either HomeBox API version transparently.

Downstream code keeps calling the same four read methods —
``get_items_summary``, ``get_item``, ``get_items``,
``download_attachment`` — and receives ``HbItem``-shaped data
with the legacy field names regardless of which backend served
the request.
"""

from typing import Any, Dict, List, Optional

from .hb_client_backends import (
    API_PASSWORD_OPTION,
    API_URL_OPTION,
    API_USER_OPTION,
    _HbLegacyBackend,
)
from .hb_models import HbItem


class HbClient:
    """Thin facade over a version-specific backend. The class
    attributes below are the canonical keys into the
    ``api_options`` dict that callers (factory, tests) populate
    when constructing the client."""

    API_URL = API_URL_OPTION
    API_USER = API_USER_OPTION
    API_PASSWORD = API_PASSWORD_OPTION

    def __init__(
            self,
            api_options : Dict[str, str],
            timeout_secs : Optional[float] = None,
    ):
        # Today only the legacy backend is wired in. #373 Phase 3
        # replaces this construction with a factory that probes the
        # upstream HomeBox version and selects the right backend.
        self._backend = _HbLegacyBackend(
            api_options=api_options,
            timeout_secs=timeout_secs,
        )

    def get_items_summary(self) -> List[ Dict[str, Any] ]:
        return self._backend.get_items_summary()

    def get_item(self, item_id: str) -> HbItem:
        return self._backend.get_item( item_id )

    def get_items(self) -> List[ HbItem ]:
        return self._backend.get_items()

    def download_attachment(
            self, item_id: str, attachment_id: str,
    ) -> Optional[ Dict[str, Any] ]:
        return self._backend.download_attachment( item_id, attachment_id )
