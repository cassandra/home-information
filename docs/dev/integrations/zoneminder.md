# ZoneMinder

## Overview

The ZoneMinder integration follows the standard pattern in
`integration-guidelines.md`: a `ZoneMinderGateway` exposes the
framework surface; a singleton `ZoneMinderManager` owns shared client
state and the active `ZMApi` instance; the synchronizer imports each
ZM monitor as an HI camera item with a movement sensor and a function
controller; `ZoneMinderMonitor` polls in the background for monitor
state and event changes.

ZoneMinder ships a vendored Python client (`pyzm`) under
`src/hi/services/zoneminder/pyzm_client/`. We use it directly rather
than depending on the unmaintained PyPI package.

User-facing setup, CORS, and SSL troubleshooting live in
[`docs/integrations/zoneminder.md`](../../integrations/zoneminder.md).

## Key modules

- `src/hi/services/zoneminder/integration.py` — `ZoneMinderGateway`.
  Framework entry point.
- `src/hi/services/zoneminder/zm_manager.py` — `ZoneMinderManager`.
  Singleton holding the `ZMApi` client and integration attributes;
  also constructs the live-stream URLs from the configured
  `PORTAL_URL`.
- `src/hi/services/zoneminder/zm_client_factory.py` — builds and
  validates the `ZMApi` from the integration attributes.
- `src/hi/services/zoneminder/pyzm_client/` — vendored Python client
  for ZM's REST API and `cgi-bin/nph-zms` streaming endpoints.
- `src/hi/services/zoneminder/zm_sync.py` — `ZoneMinderSynchronizer`.
  Drives Import / Refresh; per-monitor entity creation in
  `_create_monitor_entity` (this is also the entry point used by the
  auto-reconnect path on Refresh).
- `src/hi/services/zoneminder/monitors.py` — `ZoneMinderMonitor`.
  Periodic poll for monitor state, function changes, and events;
  emits `SensorResponse` updates for movement sensor state changes.
- `src/hi/services/zoneminder/zm_controller.py` —
  `ZoneMinderController`. Maps HI control actions onto ZM monitor
  function changes (Modect, Monitor, Record, etc.).

## API patterns

ZoneMinder's REST API is the only command/query protocol; live video
streams use the separate `cgi-bin/nph-zms` MJPEG endpoint. Both are
served from the user-configured `PORTAL_URL` host.

Authentication is username/password via ZM's session cookie flow,
handled by `pyzm`. There is no separate API token mechanism in
ZoneMinder.

The monitor poll cadence and per-request timeouts are defined in
`constants.py` (`ZmTimeouts`).

## Implementation notes

- **Vendored `pyzm`.** The upstream `pyzm` PyPI package is not
  actively maintained. We carry a copy of the relevant pieces under
  `pyzm_client/` and modify it as needed. Treat that directory as a
  third-party dependency, not as project code — keep it minimally
  modified and document any patches inline.
- **API URL vs. Portal URL.** ZM exposes its REST API and its web
  portal at related but distinct paths (`.../zm/api` vs `.../zm`).
  Both must be configured because stream URLs are built off
  `PORTAL_URL`, not `API_URL`. See `zm_manager._stream_url(...)`
  builders.
- **Timezone handling.** ZM event timestamps are stored in the ZM
  server's local time, not UTC. The configured `TIMEZONE` integration
  attribute is used to convert them; see `zm_models.ZmEvent` /
  `zm_manager`.
- **Movement event lifecycle.** ZM emits motion events with start /
  end timestamps that arrive asynchronously. The monitor correlates
  these into HI sensor responses; see the correlation logic in
  `monitors.py`.
- **CORS / SSL infrastructure quirks.** The user-facing doc
  documents the operator-side workarounds (`HI_EXTRA_CSP_URLS`
  environment variable, nginx reverse proxy for SSL → plain HTTP).
  These are infrastructure issues, not code-level ones, so they
  belong in the user-facing troubleshooting section, not here.

## Testing approach

Tests live in `src/hi/services/zoneminder/tests/`. Sync flow,
controller behavior, and monitor state correlation each have their
own modules; `test_zm_sync.py` is the largest. Synthetic monitor
data lives in `tests/synthetic_data.py` and `tests/data/`.

Manual end-to-end testing uses the simulator; ZM simulator support
lives at `src/hi/simulator/services/zoneminder/`. For the operator
workflow and profile descriptions, see
[`docs/dev/testing/test-simulator.md`](../testing/test-simulator.md).

## References

- [ZoneMinder API documentation](https://zoneminder.readthedocs.io/en/latest/api.html)
- Upstream `pyzm` (vendored): <https://github.com/ZoneMinder/pyzm>
- User-facing setup: [`docs/integrations/zoneminder.md`](../../integrations/zoneminder.md)
