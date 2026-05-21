import json
import logging
from typing import Any, Dict, List, Optional

from django.http import Http404
from requests import get

from .constants import FrigateApi, FrigateTimeouts

logger = logging.getLogger(__name__)


class FrigateClient:
    """Encapsulated HTTP client for Frigate's REST API.

    Modeled on ``HassClient``: per-instance base URL and headers,
    explicit per-method endpoint wrappers, status-code / content-type
    checks at the boundary. Frigate's v1 auth model is "behind a
    reverse proxy" with an optional verbatim ``Authorization`` header
    the operator pastes in (no JWT login flow in v1).

    Methods raise ``ValueError`` with a descriptive message at the
    boundary so the monitor / connection-test paths can record a
    meaningful error rather than letting opaque JSON / decode errors
    bubble up to operators.
    """

    BASE_URL = 'base_url'
    AUTH_HEADER = 'auth_header'

    DEFAULT_TIMEOUT_SECS = FrigateTimeouts.API_TIMEOUT_SECS

    def __init__( self,
                  api_options    : Dict[ str, str ],
                  timeout_secs   : Optional[ float ] = None ):
        base_url = api_options.get( self.BASE_URL )
        if not base_url:
            raise ValueError( 'FrigateClient requires a base_url.' )
        self._base_url = base_url.rstrip( '/' )

        self._headers : Dict[ str, str ] = {
            'Accept': 'application/json',
        }
        auth_value = api_options.get( self.AUTH_HEADER )
        if auth_value:
            self._headers[ 'Authorization' ] = auth_value

        self._timeout_secs = (
            timeout_secs if timeout_secs is not None else self.DEFAULT_TIMEOUT_SECS
        )
        return

    @property
    def base_url(self) -> str:
        return self._base_url

    # ---- Reachability probe (used by test_connection) ------------------

    def ping(self) -> None:
        """Lightweight reachability probe against ``/api/config``.

        Confirms the base URL points at a Frigate instance (or whatever
        is fronting it) and that the response is JSON-shaped — a 200
        with HTML usually means the URL is fronting the Frigate web UI
        rather than the API, and we want ``test_connection`` to fail
        at save time instead of letting the polling path JSONDecode
        later. Returns ``None`` on success; raises ``ValueError`` with
        a diagnostic message on failure. Network errors propagate."""
        self._get_config()
        return

    # ---- Inbound (query) endpoints -------------------------------------

    def get_cameras( self ) -> List[ Dict ]:
        """Camera list, derived from the ``cameras`` map in
        ``/api/config``. Frigate exposes its camera set through the
        live config rather than a dedicated endpoint. Each returned
        dict carries ``{'name': <camera_name>, 'config': <per-camera
        config dict>}``."""
        config_data = self._get_config()
        cameras_map = config_data.get( 'cameras' )
        if not isinstance( cameras_map, dict ):
            raise ValueError(
                f'Frigate /api/config response missing or malformed "cameras"'
                f' field: got {type(cameras_map).__name__}'
            )
        return [
            { 'name': camera_name, 'config': camera_config }
            for camera_name, camera_config in cameras_map.items()
        ]

    def get_events( self,
                    after   : Optional[ float ] = None,
                    limit   : Optional[ int ]   = None ) -> List[ Dict ]:
        """``GET /api/events`` — list events.

        ``after`` (epoch seconds) is the polling cursor: only events
        whose start_time is at-or-after the cutoff are returned. The
        simulator (and real Frigate) sort newest-first by start_time.
        ``limit`` caps the returned count when set."""
        params : Dict[ str, Any ] = {}
        if after is not None:
            params[ 'after' ] = after
        if limit is not None:
            params[ 'limit' ] = limit
        data = self._get_json(
            path = FrigateApi.EVENTS_PATH,
            params = params or None,
        )
        if not isinstance( data, list ):
            raise ValueError(
                f'Frigate /api/events response was not a list:'
                f' got {type(data).__name__}'
            )
        return data

    def get_event( self, event_id : str ) -> Dict:
        """``GET /api/events/<id>`` — single event detail."""
        path = f'{FrigateApi.EVENTS_PATH}/{event_id}'
        data = self._get_json( path = path )
        if not isinstance( data, dict ):
            raise ValueError(
                f'Frigate /api/events/{event_id} response was not a JSON object:'
                f' got {type(data).__name__}'
            )
        return data

    # ---- Internal: shared request + validation -------------------------

    def _get_config(self) -> Dict:
        """Fetch ``/api/config`` and validate the response is a dict.
        Shared by ``ping()`` and ``get_cameras()``."""
        data = self._get_json( path = FrigateApi.CONFIG_PATH )
        if not isinstance( data, dict ):
            raise ValueError(
                f'Frigate /api/config response was not a JSON object:'
                f' got {type(data).__name__}'
            )
        return data

    def _get_json(
            self,
            path    : str,
            params  : Optional[ Dict[ str, Any ] ] = None,
    ) -> Any:
        """GET ``path`` against the configured base URL and return
        parsed JSON. Status code, content-type, and JSON-parse errors
        all raise ``ValueError`` with diagnostic messages that include
        the path so monitor / test_connection paths can record what
        failed."""
        url = f'{self._base_url}{path}'
        response = get(
            url,
            headers = self._headers,
            timeout = self._timeout_secs,
            params = params,
        )
        if response.status_code == 404:
            raise Http404( f'Frigate {path}: {response.text}' )
        if response.status_code not in (200, 201):
            raise ValueError(
                f'Frigate {path} request failed:'
                f' {response.status_code} {response.text}'
            )
        content_type = ( response.headers or {} ).get( 'content-type', '' )
        if 'json' not in content_type.lower():
            raise ValueError(
                f'Frigate API URL may be incorrect. Expected JSON response'
                f' from {path} but received'
                f' {content_type or "unknown content type"}.'
                f' Ensure the URL points at the Frigate API root.'
            )
        try:
            return json.loads( response.text )
        except json.JSONDecodeError as e:
            raise ValueError(
                f'Frigate {path} response was not valid JSON: {e}'
            ) from e

