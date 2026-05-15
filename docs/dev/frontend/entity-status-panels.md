# Entity Status Panels

EntityStatusPanels render the body of the entity status modal and of the per-entity cards inside collections. The framework dispatches per-`EntityType`, so each panel can present its entity in whatever form best fits — a flat state list, a graphical dial, a video frame, etc. — while the surrounding modal / card chrome stays uniform.

This document covers authoring a new panel.

**Related docs:**
- [`entity-display-overview.md`](entity-display-overview.md) — high-level architecture and how panels fit alongside the other display surfaces.
- [`entity-status-display.md`](entity-status-display.md) — the polling-update contract that panel templates and panel JS plug into.

## Overview

A panel is a self-contained bundle of templates, CSS, and JavaScript scoped to one `EntityType` and rendered in one of three **display contexts**:

| Context | Where it renders | Wrapper template |
|---|---|---|
| `modal` | The entity status modal body | `entity/templates/entity/modals/entity_status.html` |
| `list`  | A collection's list-card layout | `collection/templates/collection/panes/entity_card_list.html` |
| `grid`  | A collection's grid-card layout | `collection/templates/collection/panes/entity_card_grid.html` |

The wrapper renders its own identifying chrome (entity name, integration logo, type label). The panel body fills the area below and must not duplicate that chrome.

When an entity type has no panel of its own, the framework falls back to a flat state list. The fallback is itself a registered panel — see `entity/state_panels/fallback/`.

## Anatomy

```
src/hi/apps/entity/templates/entity/state_panels/<type>/
    modal.html          # required
    list.html           # optional, falls back per context chain
    grid.html           # optional, falls back per context chain

src/hi/static/state_panels/<type>/
    <type>.css          # optional
    <type>.js           # optional, registers JS handlers
```

`<type>` is the `EntityType.name.lower()` value (e.g. `thermostat`, `smoke_detector`).

**Template resolution chain** (see [`state_panel_dispatch.py`](../../../src/hi/apps/entity/state_panel_dispatch.py)):

1. `state_panels/<type>/<context>.html` — context-specific.
2. `state_panels/<type>/modal.html` — panel default, used for any unprovided context.
3. `state_panels/fallback/<context>.html` — framework fallback.

So `modal.html` is the only required file per panel: a panel that wants to render the same body in all three contexts just provides that one template.

## Template authoring

The dispatch template tag `{% render_entity_status_panel %}` is invoked by the wrapper. By the time a panel template runs, the parent context plus the entity's display projection are flattened together, so the following names are top-level:

| Name | What it is |
|---|---|
| `entity` | The `Entity` model instance. |
| `entity_status_data` | The `EntityDisplayData` wrapper. |
| `state_status_data_list` | Ordered list of `EntityStateDisplayData` for the entity's states (sorted per `ENTITY_STATUS_VIEW_ORDERING`). |
| `state_status_data_by_role` | Dict keyed by lowercase `EntityStateRole.name`. Use this to pull a specific state by role. |
| `entity_for_video` | The `Entity` whose video stream this panel should embed, or `None`. |
| `display_only_svg_icon_item` | The framework `SvgIconItem` for the entity's type icon, or `None`. |
| `display_category` | `EntityDisplayCategory` enum value for layout hints (`HAS_VIDEO` / `HAS_STATE` / `PLAIN`). |

Source of truth: `EntityDisplayData.to_template_context()` in [`display_data.py`](../../../src/hi/apps/monitor/display_data.py).

### Live updates via the polling contract

Elements inside a panel get live updates by carrying `data-state-id="<entity_state.id>"` plus one or more declaration attributes. Example: a span whose text mirrors the current temperature:

```html
<span data-state-id="{{ state_status_data_by_role.thermostat_current_temperature.entity_state.id }}"
      data-display-text>72.0°F</span>
```

For the full declaration grammar, server payload shape, and the icon-vs-path asymmetry, see [`entity-status-display.md`](entity-status-display.md). Authoring a panel template is mostly a matter of (1) pulling the right state via `state_status_data_by_role` or `state_status_data_list`, and (2) tagging the elements that should refresh.

## JS extensions

Most panels need no JavaScript — declarative HTML attributes and CSS rules carry all the live-update work. When more is needed (e.g., re-positioning an SVG marker from a numeric magnitude), register a handler with `Hi.statePanels`:

- **`Hi.statePanels.registerUpdate(handler)`** — fires after each polling apply pass, receiving the full status map keyed by state id. Use this for refresh-time work the declarative contract can't express.
- **`Hi.statePanels.registerInit(handler)`** — fires on initial page load *and* after every async content insertion (entity status modal opens, collection refreshes). Use this to position elements from server-rendered data. Handlers must be idempotent — they re-scan the document on each call.

API source: [`entity_state_status.js`](../../../src/hi/static/js/entity_state_status.js). Reference panel: [`state_panels/thermostat/thermostat.js`](../../../src/hi/static/state_panels/thermostat/thermostat.js) uses both hooks for its SVG dial.

## Walkthrough: adding a panel for a new `EntityType`

1. Create `src/hi/apps/entity/templates/entity/state_panels/<type>/modal.html`. Add `list.html` / `grid.html` only if those contexts need a different layout.
2. Fetch specific states by role with `state_status_data_by_role.<role_name>` (lowercase `EntityStateRole.name`), or iterate `state_status_data_list` for the ordered set. The `{% panel_state entity "role_name" %}` tag returns just the `EntityState` model if that's what you need.
3. Tag refreshable elements per the polling-update contract. Server-rendered initial values stay; the dispatcher rewrites them each tick.
4. Drop panel-private CSS and JS in `src/hi/static/state_panels/<type>/` if needed.
5. Register any panel JS handlers via `Hi.statePanels.registerInit` / `registerUpdate`.
6. Verify in the simulator: open the entity status modal, change values on the simulator side, watch the panel refresh; open a collection containing the entity and check the list and grid contexts.

## Exemplars

Read the existing panels when starting a new one — copy from the closest match.

- **[`fallback/`](../../../src/hi/apps/entity/templates/entity/state_panels/fallback/)** — universal flat state list. Authors needing the standard rendering can include `fallback/state_list.html` directly.
- **[`smoke_detector/`](../../../src/hi/apps/entity/templates/entity/state_panels/smoke_detector/)** — CSS-only panel. Status-attribute-driven variants switch icon and label visibility without any JS.
- **[`thermostat/`](../../../src/hi/apps/entity/templates/entity/state_panels/thermostat/)** — full kit. Role-keyed state lookups, custom CSS, init + update JS hooks for an SVG dial.
- **[`camera/`](../../../src/hi/apps/entity/templates/entity/state_panels/camera/)** — embeds the shared flat state list partial alongside a video stream, demonstrating panel composition with framework partials.

## Pitfalls

- **`data-svg-style` is for single-element styling.** Don't put it on a multi-element SVG `<g>` icon — children inherit the pushed `fill`/`stroke` attributes and lose their differentiated styling. Use `data-status` and CSS branching instead. See [`entity-status-display.md`](entity-status-display.md#icon-vs-path-update-shape) for the full rationale.
- **Init handlers must be idempotent.** `registerInit` fires on both initial DOM-ready and every async content insertion. Handlers re-scan the document each time; applying state to already-initialized elements must be safe.
- **Don't duplicate chrome.** The modal wrapper supplies the type icon, entity name, integration logo, and type label in its subheader. The collection-card wrappers supply the entity-name title and (when applicable) the video stream. Panel bodies render below this chrome and should not repeat any of it.
- **Shared partials live where they were first authored.** The flat state list and per-state row templates live under `state_panels/fallback/` (where they were born). Other panels that want the same list reference them from that path; there's no separate "shared" namespace.
