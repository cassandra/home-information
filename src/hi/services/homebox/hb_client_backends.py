"""HomeBox API client backends.

Both major HomeBox API versions expose the same logical read
surface (list items, get one item, download an attachment) under
different URL paths and slightly different response shapes:

  - v0.25 and earlier: ``/v1/items/*``
  - v0.26+: ``/v1/entities/*`` (the "entity merge")

Each version is implemented as a concrete subclass of
``_HbBackendBase``; the ``HbClient`` facade selects between them
(today: legacy only; #373 Phase 3 adds the entities backend and a
version probe). Backend output is normalized to the legacy
``HbItem`` shape so downstream code is version-agnostic.
"""

import logging
from typing import Any, Dict, List, Optional, Protocol, Union

from requests import Response, Session

from .hb_models import HbItem


logger = logging.getLogger(__name__)


# Keys into the ``api_options`` dict passed to a backend's
# constructor. The factory and the public ``HbClient`` facade use
# the same names; the backend is the consumer that actually reads
# them, so the canonical definition lives here.
API_URL_OPTION = 'apiurl'
API_USER_OPTION = 'user'
API_PASSWORD_OPTION = 'password'


DEFAULT_TIMEOUT_SECS = 25.0
API_VERSION = 'v1'


class _HbBackend(Protocol):
    """Read-only HomeBox API surface. Both versions normalize to
    legacy-shaped ``HbItem`` dicts on the way out so downstream
    code is version-agnostic."""

    def get_items_summary(self) -> List[Dict[str, Any]]:
        ...

    def get_item(self, item_id: str) -> HbItem:
        ...

    def get_items(self) -> List[HbItem]:
        ...

    def download_attachment(self,
                            item_id: str,
                            attachment_id: str) -> Optional[Dict[str, Any]]:
        ...


class _HbBackendBase:
    """Transport layer shared by every version-specific backend:
    session ownership, lazy login, the request helper. URL paths
    and response normalization are the subclass's concern.
    """

    @classmethod
    def _share_transport(cls, source: '_HbBackendBase') -> '_HbBackendBase':
        """Construct an instance reusing another backend's
        session, credentials, and auth state. Used by the factory
        version probe so the chosen backend doesn't re-login after
        the probe has already authenticated."""
        instance = cls.__new__( cls )
        instance.api_url = source.api_url
        instance._user = source._user
        instance._password = source._password
        instance._timeout_secs = source._timeout_secs
        instance._session = source._session
        instance._authenticated = source._authenticated
        return instance

    def __init__(
            self,
            api_options : Dict[str, str],
            timeout_secs : Optional[float] = None,
    ):
        self.api_url = api_options.get( API_URL_OPTION )
        assert self.api_url is not None
        if self.api_url.endswith( '/' ):
            self.api_url = self.api_url[:-1]

        self._user = api_options.get( API_USER_OPTION )
        assert self._user is not None
        self._password = api_options.get( API_PASSWORD_OPTION )
        assert self._password is not None

        # Per-instance timeout. Defaults when not specified; the
        # connection-test path passes a tighter bound for
        # interactive save-time validation.
        self._timeout_secs = (
            timeout_secs if timeout_secs is not None else DEFAULT_TIMEOUT_SECS
        )

        self._session = Session()

        # Login is deferred to first request rather than performed
        # in __init__. This keeps construction free of network I/O
        # so transient upstream problems do not leave the manager
        # with a permanently-null client. ``_make_request`` lazily
        # logs in on first use and re-logs on a 401, so both the
        # periodic monitor and operator-initiated sync naturally
        # self-heal once the upstream recovers.
        self._authenticated = False

    def _login(self):
        url = f"{self.api_url}/{API_VERSION}/users/login"
        data = {
            'username': self._user,
            'password': self._password,
            'stayLoggedIn': True,
        }
        try:
            response = self._session.post(
                url, json=data, timeout=self._timeout_secs,
            )
        except Exception as e:
            raise ConnectionError(
                f'Cannot connect to HomeBox at {self.api_url}. '
                f'Verify the API URL is correct and the server is running.'
            ) from e

        response.raise_for_status()

        content_type = response.headers.get( 'content-type', '' )
        if 'json' not in content_type:
            raise ValueError(
                f'HomeBox API URL may be incorrect. Expected JSON response but received '
                f'{content_type or "unknown content type"}. '
                f'Ensure the URL includes the API path (e.g., http://host:port/api).'
            )

        token = response.json().get( 'token' )
        if token:
            self._session.headers.update( { 'Authorization': token } )
        else:
            logger.warning(
                'HomeBox login succeeded but response did not contain a token.'
            )

        self._authenticated = True

    def _make_request(
            self, method: str, url: str, **kwargs,
    ) -> Union[ dict, Response ]:
        """Make a request with lazy login + retry-on-401 semantics."""

        kwargs.setdefault( 'timeout', self._timeout_secs )

        # Lazy first login. Failures (connection refused, NON_JSON
        # upstream, etc.) propagate to the caller, who will retry
        # on the next monitor cycle / sync attempt — naturally
        # self-healing once the upstream comes back.
        if not self._authenticated and self._user:
            self._login()

        response = self._session.request( method, url, **kwargs )

        if response.status_code == 401 and self._user:
            self._authenticated = False
            self._login()
            response = self._session.request( method, url, **kwargs )

        response.raise_for_status()

        content_type = response.headers.get( 'content-type', '' )
        if content_type.startswith( 'application/json' ):
            return response.json()
        return response

    # ---- shared read methods -------------------------------------
    #
    # ``get_items_summary`` and ``get_item`` differ enough between
    # versions to warrant version-specific implementations (paths,
    # pagination, response normalization). ``get_items`` and
    # ``download_attachment`` are version-agnostic apart from URL
    # construction, so they live here with a small per-version URL
    # hook below.

    def get_items(self) -> List[ HbItem ]:
        """Fetch the list of items and, for each one, fetch the
        full details. Returns a list of fully populated ``HbItem``
        objects.

        A failed detail fetch propagates rather than being
        swallowed per-item: a partial-success outcome here is more
        dangerous than a clean failure (it silently drops items,
        which the sync layer then misinterprets as upstream
        removals or a clean 'nothing to import'). The sync flow's
        outer try/except converts the propagated error into an
        operator-visible ``error_list`` entry."""
        items_summary = self.get_items_summary()
        full_items = []
        for summary in items_summary:
            item_id = summary.get( 'id' )
            if item_id:
                full_items.append( self.get_item( item_id ) )
        return full_items

    def download_attachment(
            self, item_id: str, attachment_id: str,
    ) -> Optional[ Dict[str, Any] ]:
        """Downloads an attachment. The URL path differs between
        versions; subclasses supply it via ``_attachment_url``."""
        url = self._attachment_url(
            item_id=item_id, attachment_id=attachment_id,
        )
        response = self._make_request( 'GET', url )

        if not isinstance( response, Response ):
            logger.warning(
                f"Expected a Response object for attachment download, "
                f"got {type(response)}"
            )
            return None

        return {
            'content': response.content,
            'mime_type': response.headers.get( 'content-type' ),
        }

    def _attachment_url(self, item_id: str, attachment_id: str) -> str:
        raise NotImplementedError(
            'Subclasses must override ``_attachment_url`` to build the '
            'version-specific attachment-download URL.'
        )


class _HbLegacyBackend( _HbBackendBase ):
    """HomeBox v0.25 and earlier — ``/v1/items/*`` endpoints."""

    def get_items_summary(self) -> List[ Dict[str, Any] ]:
        """Fetch the items summary list (one API call). Suitable
        for lightweight reachability / health-check probes where
        only the count or IDs are needed.

        The items endpoint is always JSON in HomeBox; if we got
        back a raw Response (because ``_make_request`` fell through
        to the binary-attachment path on a non-JSON content type),
        the configured API URL is pointing at the wrong place.
        Surface that as a clear ValueError instead of letting
        downstream callers iterate the response as bytes."""
        url_list = f"{self.api_url}/{API_VERSION}/items"
        data = self._make_request( 'GET', url_list )
        if not isinstance( data, dict ):
            raise ValueError(
                f'HomeBox API URL may be incorrect. Expected JSON response '
                f'from {url_list} but did not receive one. Ensure the URL '
                f'points at the HomeBox API root (e.g., http://host:port/api).'
            )
        return data.get( 'items', [] )

    def get_item(self, item_id: str) -> HbItem:
        """Fetch a single item's full detail. Used by the
        Connect-mode on-demand resolver (each entity-detail modal
        open triggers one call).

        Errors propagate to the caller (auth/network/HTTP errors).
        The Connect resolver wraps this call and degrades to a
        deep-link-only placeholder on failure rather than crashing
        the modal render."""
        url = f"{self.api_url}/{API_VERSION}/items/{item_id}"
        item_detail = self._make_request( 'GET', url )
        if not isinstance( item_detail, dict ):
            raise ValueError(
                f'HomeBox returned non-JSON response for item {item_id}.'
            )
        return HbItem( api_dict=item_detail, client=self )

    def _attachment_url(self, item_id: str, attachment_id: str) -> str:
        return (
            f"{self.api_url}/{API_VERSION}/items/{item_id}"
            f"/attachments/{attachment_id}"
        )


# Page size we request from /v1/entities. Real HomeBox's default
# pagination behavior when no params are passed isn't formally
# specified; we always pass an explicit page size and loop on
# ``total`` to be robust against either default.
_ENTITIES_PAGE_SIZE = 200


class _HbEntitiesBackend( _HbBackendBase ):
    """HomeBox v0.26+ — ``/v1/entities/*`` endpoints.

    Normalizes responses to the legacy ``HbItem`` shape on the
    way out so downstream code stays version-agnostic: the v0.26
    ``parent`` field is renamed to ``location``, the new
    ``entityType`` discriminator is dropped, and the paginated
    list response is collapsed to a flat items list."""

    def get_items_summary(self) -> List[ Dict[str, Any] ]:
        """Fetch the entities list. Pages explicitly and loops
        on ``total`` until the accumulated items match — robust
        against either pagination default."""
        url = f"{self.api_url}/{API_VERSION}/entities"
        all_items: List[ Dict[str, Any] ] = []
        page = 1
        while True:
            params = { 'page': page, 'pageSize': _ENTITIES_PAGE_SIZE }
            data = self._make_request( 'GET', url, params=params )
            if not isinstance( data, dict ):
                raise ValueError(
                    f'HomeBox API URL may be incorrect. Expected JSON response '
                    f'from {url} but did not receive one. Ensure the URL '
                    f'points at the HomeBox API root (e.g., http://host:port/api).'
                )
            page_items = data.get( 'items', [] ) or []
            for entity in page_items:
                all_items.append( _normalize_entity( entity ) )
            total = data.get( 'total' )
            # ``-1`` is HomeBox's sentinel for "no pagination, all
            # returned in one shot" (real installs and the simulator
            # both use this). Treat it as a one-page reply.
            if not isinstance( total, int ) or total < 0:
                break
            if len( all_items ) >= total:
                break
            if not page_items:
                # Defensive: the server promised more items but
                # gave us an empty page. Avoid an infinite loop.
                break
            page += 1
        return all_items

    def get_item(self, item_id: str) -> HbItem:
        url = f"{self.api_url}/{API_VERSION}/entities/{item_id}"
        entity = self._make_request( 'GET', url )
        if not isinstance( entity, dict ):
            raise ValueError(
                f'HomeBox returned non-JSON response for entity {item_id}.'
            )
        return HbItem( api_dict=_normalize_entity( entity ), client=self )

    def _attachment_url(self, item_id: str, attachment_id: str) -> str:
        return (
            f"{self.api_url}/{API_VERSION}/entities/{item_id}"
            f"/attachments/{attachment_id}"
        )


def _normalize_entity( entity: Dict[str, Any] ) -> Dict[str, Any]:
    """Translate a v0.26 entity dict to the legacy item shape so
    downstream code consumes a single internal vocabulary:
    ``parent`` becomes ``location``; the new ``entityType``
    discriminator is dropped (HI doesn't need it). The input dict
    is not mutated."""
    normalized = dict( entity )
    if 'parent' in normalized:
        normalized['location'] = normalized.pop( 'parent' )
    normalized.pop( 'entityType', None )
    return normalized

