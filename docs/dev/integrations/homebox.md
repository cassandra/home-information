# HomeBox

## Overview

The HomeBox integration follows the standard pattern in
`integration-guidelines.md`, but with a narrower runtime footprint
than HA or ZM: there are no per-item sensors or controllers and no
real-time state changes to track. Items imported from HomeBox are
read-only by design — they exist for placement and reference. As a
result, `HomeBoxMonitor` does only a periodic reachability probe;
all entity churn happens via user-initiated sync.

User-facing setup and troubleshooting live in
[`docs/integrations/homebox.md`](../../integrations/homebox.md).

## Key modules

HomeBox declares both CONNECT and IMPORT capabilities, so its code
is split across two peer sub-packages with capability-agnostic
facilities at the integration top level:

- `services/homebox/integration.py` — `HomeBoxGateway`, framework
  entry point; returns both a synchronizer and an importer.
- `services/homebox/hb_*.py` — `HbClient` (REST + login flow),
  `HbClientFactory`, `HbConverter`, `HomeBoxManager`,
  `HbEntityFactory`, `HbItem`. Reused by both capabilities.
- `services/homebox/connector/` — `HomeBoxConnector`,
  `HomeBoxExternalViewResolver` (live entity-detail view), attachment proxy.
- `services/homebox/importer/` — `HomeBoxImporter` and attribute-
  population helpers.
- `services/homebox/monitors.py`, `hb_controller.py` — periodic
  reachability probe and no-op controller (no state polling, no
  controllable items).

## API patterns

HomeBox exposes a versioned REST API under `/api/v1/...`.
Authentication is username/password to `/api/v1/users/login`,
returning a session token used as a Bearer header for subsequent
requests. Token refresh is handled inside `HbClient`.

The user supplies the API root URL up to `/api` (without the version
suffix); the client appends the version internally. This is
documented in the user-facing doc and reinforced by an explicit
error message in `HbClient` when responses are not JSON.

## IntegrationImporter

`HomeBoxImporter` (`services/homebox/importer/`) is the Import-side
parallel of `HomeBoxConnector`. Both call into shared facilities
(`HbEntityFactory`, `HbConverter`) so only the orchestration differs.
See [`data-import.md`](data-import.md) for the framework-level
IMPORT capability documentation.

## Implementation notes

- **No live state.** HomeBox's data model is inventory metadata, not
  device state. There is no polling cadence to tune, no sensor
  responses to emit. The monitor exists purely for the integration
  health-status surface.
- **Read-only items.** Items imported from HomeBox cannot be edited
  in HI; their HomeBox-sourced fields appear as read-only attributes.
  The integration metadata sets `can_add_custom_attributes = False`
  on the metadata to prevent users from adding HI-side attributes
  that would not survive a sync; see `hb_metadata.py`.
- **Attachment downloads.** Files attached to a HomeBox item
  (manuals, receipts, photos) are downloaded into HI's media storage
  at sync time. Updates to the file in HomeBox propagate only on
  the next sync.

## Testing approach

Tests live in `src/hi/services/homebox/tests/`. Coverage is
straightforward — client, factory, converter, manager, models, sync.

Manual end-to-end testing uses the simulator; HomeBox simulator
support lives at `src/hi/simulator/services/homebox/`. For the
operator workflow and profile descriptions, see
[`docs/dev/testing/test-simulator.md`](../testing/test-simulator.md).

## References

- [HomeBox documentation](https://homebox.software/)
- User-facing setup: [`docs/integrations/homebox.md`](../../integrations/homebox.md)
