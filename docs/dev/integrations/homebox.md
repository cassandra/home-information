# HomeBox

## Overview

The HomeBox integration follows the standard pattern in
`integration-guidelines.md`, but with a narrower runtime footprint
than HA or ZM: there are no per-item sensors or controllers and no
real-time state changes to track. Items imported from HomeBox are
read-only by design — they exist for placement and reference. As a
result, `HomeBoxMonitor` does only a periodic reachability probe;
all entity churn happens via user-initiated Import / Refresh.

User-facing setup and troubleshooting live in
[`docs/integrations/homebox.md`](../../integrations/homebox.md).

## Key modules

- `src/hi/services/homebox/integration.py` — `HomeBoxGateway`.
  Framework entry point.
- `src/hi/services/homebox/hb_manager.py` — `HomeBoxManager`.
  Singleton holding the active `HbClient` and integration attributes.
- `src/hi/services/homebox/hb_client.py` — `HbClient`. REST wrapper
  around HomeBox's `/api/v1/...` endpoints, plus the
  username/password → session-token login flow.
- `src/hi/services/homebox/hb_converter.py` — `HbConverter`. Maps
  HomeBox items into HI items, including custom field expansion as
  read-only attributes.
- `src/hi/services/homebox/hb_sync.py` — `HomeBoxSynchronizer`.
  Drives Import / Refresh.
- `src/hi/services/homebox/monitors.py` — `HomeBoxMonitor`. Periodic
  reachability probe only; no state polling.
- `src/hi/services/homebox/hb_controller.py` — `HomeBoxController`.
  No-op controller; HomeBox items are not controllable.

## API patterns

HomeBox exposes a versioned REST API under `/api/v1/...`.
Authentication is username/password to `/api/v1/users/login`,
returning a session token used as a Bearer header for subsequent
requests. Token refresh is handled inside `HbClient`.

The user supplies the API root URL up to `/api` (without the version
suffix); the client appends the version internally. This is
documented in the user-facing doc and reinforced by an explicit
error message in `HbClient` when responses are not JSON.

## Implementation notes

- **No live state.** HomeBox's data model is inventory metadata, not
  device state. There is no polling cadence to tune, no sensor
  responses to emit. The monitor exists purely for the integration
  health-status surface.
- **Read-only items.** Items imported from HomeBox cannot be edited
  in HI; their HomeBox-sourced fields appear as read-only attributes.
  The integration metadata sets `can_add_custom_attributes = False`
  on the metadata to prevent users from adding HI-side attributes
  that would not survive a Refresh; see `hb_metadata.py`.
- **Attachment downloads.** Files attached to a HomeBox item
  (manuals, receipts, photos) are downloaded into HI's media storage
  at Import / Refresh time. Updates to the file in HomeBox propagate
  only on the next Refresh.

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
