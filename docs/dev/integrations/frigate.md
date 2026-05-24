# Frigate

## Overview

The Frigate integration follows the standard pattern in
`integration-guidelines.md`: a `FrigateGateway` exposes the
framework surface; a singleton `FrigateManager` owns shared client
state and the active `FrigateClient` instance; the synchronizer
imports each Frigate camera as a HI camera entity with a single
object-presence sensor; `FrigateMonitor` polls in the background for
event changes.

Frigate communicates over plain HTTP only — there is no MQTT path
(HI doesn't have MQTT plumbing); the API surface is small enough
that HTTP polling delivers a usable experience without sub-second
latency.

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
  `FrigateSynchronizer`. Drives sync; per-camera entity
  creation in `_create_camera_entity`.
- `src/hi/services/frigate/frigate_converter.py` —
  `FrigateConverter`. Wire-format ↔ HI model translation. Owns the
  canonical OBJECT_PRESENCE mapping (Frigate's raw object class →
  one of `person` / `car` / `animal` / `package` / `other` / `none`).
- `src/hi/services/frigate/monitors.py` — `FrigateMonitor`.
  Periodic poll for camera events; emits `SensorResponse` updates
  for the object-presence sensor.
- `src/hi/services/frigate/frigate_controller.py` —
  `FrigateController`. v1 stub: returns "no control mapping" for
  every input. Frigate's only HTTP-reachable operator-toggle
  (`PUT /api/config/set` on `cameras.<name>.detect.enabled`) is a
  config edit rather than transient state, so no control surface is
  exposed in v1.

## API patterns

Frigate's REST API is the only command/query protocol; live snapshots
are JPEG bytes from `/api/<camera>/latest.jpg`. The integration was
validated only against installs with Frigate's authentication
disabled. An optional verbatim `Authorization` header field is
plumbed through but untested. No login flow, token refresh, or JWT
handling exists.

Per-request timeouts and the polling cadence are defined in
`constants.py` (`FrigateTimeouts`).

## Event polling model

The polling pipeline is the load-bearing complexity of this
integration. Frigate's `/api/events?after=T` filters strictly on
`start_time > T`, which means **once the polling cursor advances
past an event's `start_time`, that event is invisible to cursor
scans forever — even after it closes**. A ZM-style cursor-hold
approach (hold the cursor back at the open event's `start_time`)
is incompatible: with strict `>` semantics, the held cursor
excludes the very event being held for.

The monitor instead runs three phases per cycle:

1. **Cursor scan** (`?after=cursor`): for each event whose
   `start_time` is past the cursor, emit a START transition. If the
   event was already closed when first seen (lifetime shorter than
   the poll interval), also emit an END. Otherwise add the event to
   `_tracked_events`, keyed by id. Advance cursor to the latest
   `start_time` observed.
2. **Per-id refresh** (`GET /api/events/<id>`): for each id in
   `_tracked_events`, fetch its canonical state.
   - Closed → emit END, drop from tracking.
   - 404 (Frigate cleared the event) → force-close, drop.
   - Aged past `MAX_OPEN_EVENT_AGE_SECS` → force-close, drop.
   - Still open → refresh snapshot, keep tracking.
3. **Heartbeat**: emit OBJECT_NONE for cameras with no activity
   this cycle and no event currently in `_tracked_events`. Without
   this, a quiet camera's state goes stale.

The cursor never moves backward; the tracked-event set is the only
state that can grow during a cycle. API budget per cycle is `1 + N`
calls where `N` is the count of currently-open events (typically 0
or 1 in normal home use).

`FrigateMonitor._initialize` seeds the cursor at `datetimeproxy.now()`
on startup. Events open at the moment HI starts are not seeded —
the v1 posture is "HI's detection window begins when HI starts."

## Implementation notes

- **Object detection mapping.** Frigate's raw object class set is
  model-dependent (default YOLO has ~80 classes; custom models can
  have arbitrary classes). HI maps these onto a canonical 6-value
  `OBJECT_PRESENCE` range — see `FrigateConverter`. Classes that
  don't map to a named bucket land in `other`. The integration is
  the only place this mapping lives; do not duplicate it elsewhere.
- **Single sensor per camera.** Frigate couples motion to object
  detection — there is no motion-without-class signal on the events
  API — so OBJECT_PRESENCE subsumes the "is motion happening"
  signal and a separate MOVEMENT sensor would always mirror it.
- **MQTT is intentionally not supported.** HI doesn't have an MQTT
  client and Frigate's HTTP API is sufficient for the use cases
  HI's spatial-display model requires.
- **Zones and sub-labels travel as event metadata.** Frigate emits
  zone-enter / zone-leave events and rich sub-label data
  (face recognition, LPR); HI surfaces both as `detail_attrs` on the
  event without promoting them to typed states. Revisit if/when a
  use case needs rule-based branching on zones.
- **Force-close timeout.** `MAX_OPEN_EVENT_AGE_SECS` (1 hour) caps
  how long an event may stay in `_tracked_events` before HI synthesizes
  an END row. Intended for orphaned events (Frigate restart,
  dropped detection). No equivalent to ZM's auto-close-on-no-update
  behavior — Frigate is consulted by id on every cycle, so a stuck
  event surfaces directly rather than via timeout heuristics.

## Testing approach

Tests live in `src/hi/services/frigate/tests/`. The monitor's
phase-by-phase invariants and the open→closed transition that
motivated the rewrite are covered in `test_frigate_monitor.py`.

Manual end-to-end testing uses the simulator; Frigate simulator
support lives at `src/hi/simulator/services/frigate/`. The
simulator's `get_events_after` mirrors Frigate's strict `>`
semantics so monitor behavior validated against the simulator
matches real Frigate. For the operator workflow and profile
descriptions, see
[`docs/dev/testing/test-simulator.md`](../testing/test-simulator.md).

## References

- [Frigate HTTP API documentation](https://docs.frigate.video/integrations/api/frigate-http-api/)
- User-facing setup: [`docs/integrations/frigate.md`](../../integrations/frigate.md)
- Tracking issue: <https://github.com/cassandra/home-information/issues/233>
