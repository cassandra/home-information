"""HomeBox API client facade.

Delegates to a version-specific backend (``_HbLegacyBackend`` for
``/v1/items/*`` on HomeBox v0.25 and earlier; ``_HbEntitiesBackend``
for ``/v1/entities/*`` on v0.26+). Backend selection is a runtime
probe — performed lazily on the first method call so construction
remains free of network I/O. Downstream code keeps calling the
same four read methods and receives ``HbItem``-shaped data with the
legacy field names regardless of which backend served the request.
"""

from typing import Any, Dict, List, Optional

from .hb_client_backends import (
    API_PASSWORD_OPTION,
    API_URL_OPTION,
    API_USER_OPTION,
    _HbBackend,
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
        # Construction stays free of network I/O: the probe that
        # selects the right backend happens lazily on the first
        # method call. This matches the deferred-login pattern
        # that lets a transient upstream failure self-heal on the
        # next operator-initiated sync without requiring a manager
        # reload.
        self._api_options = api_options
        self._timeout_secs = timeout_secs
        self._backend : Optional[ _HbBackend ] = None
        # Normalize the configured API URL once at construction so
        # the (no-network) ``api_url`` accessor below matches what
        # the backends use internally — the deep-link builder reads
        # this without needing to trigger the lazy backend resolve.
        raw_url = api_options.get( API_URL_OPTION ) or ''
        self.api_url = raw_url.rstrip( '/' )

    def _get_backend(self) -> _HbBackend:
        if self._backend is None:
            # Local import to avoid circular import: the factory
            # imports the facade for its public-API construction
            # path.
            from .hb_client_factory import HbClientFactory
            self._backend = HbClientFactory.resolve_backend(
                api_options=self._api_options,
                timeout_secs=self._timeout_secs,
            )
        return self._backend

    def get_items_summary(self) -> List[ Dict[str, Any] ]:
        return self._get_backend().get_items_summary()

    def get_item(self, item_id: str) -> HbItem:
        return self._get_backend().get_item( item_id )

    def get_items(self) -> List[ HbItem ]:
        return self._get_backend().get_items()

    def download_attachment(
            self, item_id: str, attachment_id: str,
    ) -> Optional[ Dict[str, Any] ]:
        return self._get_backend().download_attachment( item_id, attachment_id )
