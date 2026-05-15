# Entity Display — Architecture Overview

How entity state flows from sensor to pixel, and where the responsibilities live. Read this first when you're new to the frontend; reach for the focused docs (linked below) when you're authoring or modifying a specific surface.

## The flow

```
Sensor reading (HA / ZM / etc.)
         │
         ▼
EntityStateStatusData            ─ raw per-state data container
         │
         ▼
EntityStateDisplayData           ─ display projections (StatusStyle, formatted text, etc.)
         │
         ▼
StatusDisplayManager             ─ assembles entityStateStatusMap, keyed by state id
         │
         ▼  ────── /api/status response ──────►  JS dispatcher (entity_state_status.js)
                                                      │
                                                      ▼
                                         DOM elements with data-state-id
                                         (icons, paths, panels, sensor cards)
```

Server side: each `EntityState` gets one row in the status map. The row carries whatever update payloads the surfaces consuming this state might need — a status string, formatted display text, a controller widget value, an SVG style bundle. Source of truth: [`EntityStateDisplayData.to_polling_update_dict`](../../../src/hi/apps/monitor/display_data.py).

Client side: the dispatcher walks every DOM element carrying `data-state-id="<id>"`, looks up the row for that state, and writes whatever subset the element opted into via declaration attributes (`data-status`, `data-display-text`, etc.). No descendant traversal, no class-as-join — each element is self-describing.

## The four display surfaces

The same polling pipeline drives four visually distinct surfaces. Each surface has its own authoring conventions but speaks the same wire contract.

| Surface | Where it appears | Authoring doc |
|---|---|---|
| **LocationView SVG icons** | The map view's `<g>` icon elements per positioned entity | [`entity-visual-configuration.md`](entity-visual-configuration.md) |
| **LocationView SVG paths** | The map view's `<path>` elements per area-based entity | [`entity-visual-configuration.md`](entity-visual-configuration.md) |
| **Entity status modal** | Body of the per-entity status dialog | [`entity-status-panels.md`](entity-status-panels.md) |
| **Collection cards** | Per-entity cards in the list and grid layouts of a collection view | [`entity-status-panels.md`](entity-status-panels.md) |

The modal and collection-card surfaces share an `EntityStatusPanel` dispatch: a panel for a given `EntityType` provides up to three templates (`modal.html` / `list.html` / `grid.html`), with a framework fallback supplying a flat state list when no per-type panel exists.

## The polling contract is the connective tissue

All four surfaces ultimately render DOM elements whose live behavior is driven by the same per-element contract:

```html
<element data-state-id="<entity_state.id>"
         data-status                 ← optional: receive the status attribute
         data-display-text           ← optional: receive the formatted text
         data-display-magnitude      ← optional: receive the magnitude only
         data-display-unit           ← optional: receive the unit only
         data-controller-value       ← optional: receive form value updates
         data-svg-style              ← optional: receive the full SVG style bundle
         ...>
```

The full grammar, the server payload shape, and the rules about which declarations belong on which element shapes are documented in [`entity-status-display.md`](entity-status-display.md).

## Where to look next

By task:

- **Adding visual support for a new `EntityType` on the map** (icon or path) — [`entity-visual-configuration.md`](entity-visual-configuration.md).
- **Authoring a custom panel for a new `EntityType`** (modal / list / grid bodies) — [`entity-status-panels.md`](entity-status-panels.md).
- **Modifying the polling-update mechanism**, the wire format, the color palette, or the per-element declaration grammar — [`entity-status-display.md`](entity-status-display.md).

By component:

- Backend: [`StatusDisplayManager`](../../../src/hi/apps/monitor/status_display_manager.py), [`EntityStateDisplayData` / `EntityDisplayData`](../../../src/hi/apps/monitor/display_data.py), [`EntityStateStatusData`](../../../src/hi/apps/monitor/status_data.py).
- Frontend dispatcher: [`entity_state_status.js`](../../../src/hi/static/js/entity_state_status.js).
- Panel dispatcher: [`state_panel_dispatch.py`](../../../src/hi/apps/entity/state_panel_dispatch.py) + [`state_panel_tags.py`](../../../src/hi/apps/entity/templatetags/state_panel_tags.py).
- CSS palette and SVG status rules: [`main.css`](../../../src/hi/static/css/main.css) (search `:root` for variables, `g[status` and `.hi-status-display[status` for rules).
