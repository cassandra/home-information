# Frigate

## Overview

The Frigate integration follows the standard pattern in
`integration-guidelines.md`: a `FrigateGateway` exposes the
framework surface; a singleton `FrigateManager` owns shared client
state and the active `FrigateClient` instance; the synchronizer
imports each Frigate camera as a HI camera entity with a movement
sensor and an object-presence sensor; `FrigateMonitor` polls in
the background for event changes.

Frigate communicates over plain HTTP only — there is no MQTT path
(by design, given HI doesn't have MQTT plumbing); the API surface is
small enough that HTTP polling delivers a usable experience without
sub-second latency.

User-facing setup lives in
[`docs/integrations/frigate.md`](../../integrations/frigate.md).

## Key modules

- `src/hi/services/frigate/integration.py` — `FrigateGateway`.
  Framework entry point.
- `src/hi/services/frigate/frigate_manager.py` — `FrigateManager`.
  Singleton holding the active `FrigateClient`, integration
  attributes, and change-listener fan-out.
- `src/hi/services/frigate/frigate_client.py` — `FrigateClient`.
  Encapsulated HTTP client wrapping the Frigate REST API.
- `src/hi/services/frigate/frigate_sync.py` —
  `FrigateSynchronizer`. Drives Import / Refresh; per-camera entity
  creation in `_create_camera_entity`.
- `src/hi/services/frigate/frigate_converter.py` —
  `FrigateConverter`. Wire-format ↔ HI model translation. Owns the
  canonical OBJECT_PRESENCE mapping (Frigate's raw object class →
  one of `person` / `car` / `animal` / `package` / `other` / `none`).
- `src/hi/services/frigate/monitors.py` — `FrigateMonitor`.
  Periodic poll for camera events; emits `SensorResponse` updates
  for movement and object-presence sensors.
- `src/hi/services/frigate/frigate_controller.py` —
  `FrigateController`. Maps HI control actions onto Frigate API
  calls.

## API patterns

Frigate's REST API is the only command/query protocol; live snapshots
are JPEG bytes from `/api/<camera>/latest.jpg`. Authentication in v1
is "behind a reverse proxy" with an optional verbatim
`Authorization` header field; JWT login is deferred.

The monitor poll cadence and per-request timeouts are defined in
`constants.py` (`FrigateTimeouts`).

## Implementation notes

- **Object detection mapping.** Frigate's raw object class set is
  model-dependent (default YOLO has ~80 classes; custom models can
  have arbitrary classes). HI maps these onto a canonical 6-value
  `OBJECT_PRESENCE` range — see `FrigateConverter`. Classes that
  don't map to a named bucket land in `other`. The integration is
  the only place this mapping lives; do not duplicate it elsewhere.
- **Polling cadence.** Inherited from the ZM defaults
  (`FrigateTimeouts.POLLING_INTERVAL_SECS`). Tune once we have
  real-install signal.
- **MQTT is intentionally not supported.** HI doesn't have an MQTT
  client and Frigate's HTTP API is sufficient for the use cases
  HI's spatial-display model requires.
- **Zones and sub-labels travel as event metadata.** Frigate emits
  zone-enter / zone-leave events and rich sub-label data
  (face recognition, LPR); HI surfaces both as `detail_attrs` on the
  event without promoting them to typed states. Revisit if/when a
  use case needs rule-based branching on zones.

## Testing approach

Tests live in `src/hi/services/frigate/tests/`.

Manual end-to-end testing uses the simulator; Frigate simulator
support lives at `src/hi/simulator/services/frigate/`. For the
operator workflow and profile descriptions, see
[`docs/dev/testing/test-simulator.md`](../testing/test-simulator.md).

## References

- [Frigate HTTP API documentation](https://docs.frigate.video/integrations/api/frigate-http-api/)
- User-facing setup: [`docs/integrations/frigate.md`](../../integrations/frigate.md)
- Tracking issue: <https://github.com/cassandra/home-information/issues/233>
