# Home Assistant

## Overview

The Home Assistant integration follows the standard pattern in
`integration-guidelines.md`: a `HassGateway` exposes the framework
surface (manage view, monitor, controller, synchronizer); a singleton
`HassManager` owns shared client state; `HassConverter` translates
upstream HA states into HI items at import time; `HassMonitor` runs
in the background to poll for state changes; and `HassController`
dispatches HI control actions back to HA.

User-facing setup and troubleshooting live in
[`docs/integrations/home-assistant.md`](../../integrations/home-assistant.md).

## Key modules

- `src/hi/services/hass/integration.py` — `HassGateway`. Framework
  entry point.
- `src/hi/services/hass/hass_manager.py` — `HassManager`. Singleton
  holding the active `HassClient` and the integration attribute map.
- `src/hi/services/hass/hass_client.py` — `HassClient`. Thin REST
  wrapper over HA's `/api/states` and `/api/services/...`. Built on
  top of the standard `requests` library.
- `src/hi/services/hass/hass_converter.py` — `HassConverter`.
  Heuristic mapping of upstream HA states to HI items. The bulk of
  integration-specific complexity lives here. Aggregates multi-state
  HA devices into a single HI item where it can.
- `src/hi/services/hass/hass_sync.py` — `HassSynchronizer`. Drives
  the Import / Refresh flow; delegates to the converter for the
  per-item shape.
- `src/hi/services/hass/monitors.py` — `HassMonitor`. Periodic poll
  against `/api/states`; produces `SensorResponse` events for state
  changes.
- `src/hi/services/hass/hass_controller.py` — `HassController`.
  Translates HI control actions back into HA service calls.

## API patterns

HA's REST API is the only protocol used today. Authentication is via
a long-lived access token sent as a Bearer header, configured by the
user. The integration polls `/api/states` (interval defined as
`HASS_POLLING_INTERVAL_SECS` in `monitors.py`) and posts to
`/api/services/<domain>/<service>` for control actions. There is no
WebSocket or push-notification path — see Known limitations in the
user-facing doc.

Upstream API reference: <https://developers.home-assistant.io/docs/api/rest/>.

## Implementation notes

- **Capability detection is heuristic.** HA's API does not directly
  declare what an entity can do. `HassConverter` infers state type
  and controllability from `domain`, `device_class`, and supported
  feature flags via the `HASS_STATE_TO_ENTITY_STATE_TYPE_MAPPING`
  table. Read that table in `hass_converter.py` before changing
  capability logic — it captures every mapping in one place
  intentionally.
- **Multi-state device aggregation.** A single physical device (e.g.,
  a light with both `light.kitchen` and `switch.kitchen` HA entities)
  is collapsed into one HI item where the converter can identify the
  pairing — by Insteon address, by full-name match, or by suffix
  rules. The grouping logic is non-trivial; see the converter's
  device-aggregation section.
- **Allowlist filtering.** Only HA domains and device classes named
  in the `IMPORT_ALLOWLIST` integration attribute are imported. The
  default list is set in `enums.py` (`HassAttributeType`).

## Testing approach

Tests live in `src/hi/services/hass/tests/`. The converter's mapping
behavior is the largest test surface
(`test_hass_converter_create.py`, `test_hass_converter_mapping.py`,
`test_import_allowlist.py`); sync flow is exercised in
`test_hass_sync.py`.

Manual end-to-end testing uses the simulator; HA simulator support
lives at `src/hi/simulator/services/hass/`. For the operator
workflow and profile descriptions, see
[`docs/dev/testing/test-simulator.md`](../testing/test-simulator.md).

## References

- [Home Assistant REST API](https://developers.home-assistant.io/docs/api/rest/)
- [Long-lived access tokens (HA)](https://www.home-assistant.io/docs/authentication/#your-account-profile)
- User-facing setup: [`docs/integrations/home-assistant.md`](../../integrations/home-assistant.md)
