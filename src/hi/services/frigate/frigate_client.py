import logging
from typing import Dict, List, Optional

from .constants import FrigateApi, FrigateTimeouts

logger = logging.getLogger(__name__)


class FrigateClient:
    """Encapsulated HTTP client for Frigate's REST API.

    Modeled on ``HassClient``: per-instance base URL and headers,
    explicit per-method endpoint wrappers, status-code / content-type
    checks at the boundary. Frigate's v1 auth model is "behind a
    reverse proxy" with an optional verbatim ``Authorization`` header
    the operator pastes in (no JWT login flow in v1).

    Scaffolding stub. Methods raise ``NotImplementedError`` until
    feature work fills them in.
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
        """Lightweight reachability probe against Frigate's ``/api/config``
        endpoint. Confirms the base URL points at a Frigate instance (or
        whatever is fronting it) and that the response is JSON-shaped —
        a 200 with HTML usually means the URL is fronting the Frigate
        web UI, not the API."""
        # Scaffolding stub — fills in during feature work.
        raise NotImplementedError( 'FrigateClient.ping not yet implemented' )

    # ---- Inbound (query) endpoints -------------------------------------

    def get_events( self,
                    after   : Optional[ float ] = None,
                    limit   : Optional[ int ]   = None ) -> List[ Dict ]:
        """``GET /api/events`` — list events; ``after`` filters by
        start_time epoch seconds."""
        _ = FrigateApi.EVENTS_PATH  # placeholder reference so the import isn't unused
        raise NotImplementedError( 'FrigateClient.get_events not yet implemented' )

    def get_event( self, event_id : str ) -> Dict:
        """``GET /api/events/<id>`` — single event detail."""
        raise NotImplementedError( 'FrigateClient.get_event not yet implemented' )

    def get_cameras( self ) -> List[ Dict ]:
        """Cameras as reported by ``/api/config`` (Frigate doesn't have
        a dedicated ``/api/cameras`` endpoint; the camera set is read
        from the live config)."""
        raise NotImplementedError( 'FrigateClient.get_cameras not yet implemented' )

    # ---- Outbound (control) endpoints ----------------------------------

    def set_camera_detect( self, camera_name : str, enabled : bool ) -> None:
        """Toggle object detection for a camera (Frigate's
        ``/api/<camera>/detect/<set|on|off>`` family)."""
        raise NotImplementedError(
            'FrigateClient.set_camera_detect not yet implemented'
        )
