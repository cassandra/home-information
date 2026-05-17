# Entity Status Display — Polling-Update Contract

Reference for the polling-update contract that connects backend state to live DOM. Covers the server payload shape, the per-element declaration grammar, the status-value vocabulary, the color palette, and the icon-vs-path asymmetry.

If you're new to entity display, start with [`entity-display-overview.md`](entity-display-overview.md). For consuming the contract from authoring contexts, see [`entity-status-panels.md`](entity-status-panels.md) (panel authoring) and [`entity-visual-configuration.md`](entity-visual-configuration.md) (SVG asset authoring).

## The flow in one paragraph

On every `/api/status` poll, [`StatusDisplayManager`](../../../src/hi/apps/monitor/status_display_manager.py) builds an `entityStateStatusMap` keyed by `EntityState.id` (as a string). The JS dispatcher in [`entity_state_status.js`](../../../src/hi/static/js/entity_state_status.js) walks every DOM element carrying `data-state-id="<id>"`, looks up the row for that state, and writes whatever subset the element opted into via declaration attributes. No descendant traversal, no class-as-join — each element opts in directly.

The set of state ids in the map can grow or shrink between polls (e.g., an entity gains or loses an `EntityState`). Elements whose id is missing from the current map are left untouched on this tick; ids that newly appear are picked up on the next tick by any element that opts in. Custom `registerUpdate` handlers should follow the same shape — look up by id, no-op when the entry is absent.

## Server payload shape

Per-state row, built by [`EntityStateDisplayData.to_polling_update_dict`](../../../src/hi/apps/monitor/display_data.py):

```python
"42": {                                # key: str(entity_state.id)
    "status":    "active",             # singular status value (for [data-status])
    "controller": { "value": "on" },   # controller widget value (for [data-controller-value])
    "display": {
        "magnitude": 72.0,             # numeric magnitude (for [data-display-magnitude])
        "unit":      "°F",             # unit symbol (for [data-display-unit])
        "text":      "72.0°F",         # combined human-readable label (for [data-display-text])
    },
    "svg_style": {                     # full SVG attribute bundle (for [data-svg-style])
        "status":           "active",
        "stroke":           "red",
        "stroke-width":     4.0,
        "fill":             "red",
        "fill-opacity":     0.5,
        "stroke-dasharray": "2,4",     # optional
    },
}
```

Fields are present only when meaningful — sensor-only states omit `controller`; unit-less states omit `display.magnitude` / `display.unit`; states with no SVG styling omit `svg_style`. `entry.status` and `entry.svg_style.status` carry the same value when both are present; consumers pick the bundle that matches their opt-in.

## The DOM contract

Every element that wants polling updates carries one **anchor** attribute and one or more **declaration** attributes:

```html
<element data-state-id="<entity_state.id>"
         data-status                    ← presence-only opt-in
         data-display-text              ← presence-only opt-in
         ...>
```

The anchor identifies which state this element listens to. Each declaration is presence-only — the attribute being present opts the element in; the dispatcher provides the value from the matching row. Server-rendered initial values stay where they are; the dispatcher just keeps them current.

### Declaration grammar

| Declaration | What the dispatcher writes | Source field |
|---|---|---|
| `data-status` | Sets the `status` HTML attribute to the **status value** | `entry.status` |
| `data-controller-value` | Sets form `value` / `checked` / `selected` (per element type) | `entry.controller.value` |
| `data-display-magnitude` | Replaces text content with the **magnitude** | `entry.display.magnitude` |
| `data-display-unit` | Replaces text content with the **unit symbol** | `entry.display.unit` |
| `data-display-text` | Replaces text content with the combined **user-facing string** | `entry.display.text` |
| `data-svg-style` | Sets *all* keys in `entry.svg_style` as element attributes | `entry.svg_style` |

Sliders are special-cased: the dispatcher skips a `<input type="range">` that the user is actively dragging so a polling refresh doesn't yank the thumb out from under them.

### Status value vocabulary

The `status` value is a bucketed, CSS-friendly token derived from raw sensor data by per-state-type logic in [`EntityStateDisplayData._get_svg_status_style`](../../../src/hi/apps/monitor/display_data.py). CSS rules key on `[status="..."]` to apply visual styling. Common tokens used across multiple state types (so the same CSS rules cover several domains):

- `active`, `idle` — base states for binary alarms (movement, smoke, moisture, CO, gas), open/close, and HVAC action.
- `recent`, `past` — decay buckets for sensors that visually "cool off" after activity (movement, open/close, smoke, etc.).
- `on`, `off`, `dim` — binary power / light states.
- `open`, `closed`, `partial` — open/close discrete states.
- `connected`, `disconnected` — connectivity state.
- `high`, `low` — discrete range state.
- `smoke_detected`, `smoke_clear`, `moisture_detected`, `moisture_clear`, `co_detected`, `co_clear`, `gas_detected`, `gas_clear` — alarm-specific values, kept distinct from generic `active`/`idle` where the surface needs domain-specific styling.

Adding a new state type that needs its own status token also requires adding matching CSS rules. The complete authoritative palette is in [`StatusStyle`](../../../src/hi/hi_styles.py) on the backend and the `g[status="..."]` / `.hi-status-display[status="..."]` rule blocks in [`main.css`](../../../src/hi/static/css/main.css) on the frontend.

## Color palette

CSS custom properties in [`main.css`](../../../src/hi/static/css/main.css)'s `:root`:

```css
--status-active-color   /* alarmed / detected — red */
--status-recent-color   /* recently alarmed — orange */
--status-past-color     /* past alarm decaying — yellow */
--status-ok-color       /* nominal / connected — green */
--status-bad-color      /* fault — dark red */
--status-idle-color     /* default / neutral — gray */
--status-on-color       /* powered on — yellow */
--status-off-color      /* powered off — gray */
```

Each has an `--on-status-*-color` companion for foreground text against the corresponding background.

The decay sequence used by recently-active sensors moves through `active → recent → past → idle` as time passes since the last activation; the thresholds live in [`EntityStateDisplayData`](../../../src/hi/apps/monitor/display_data.py) (`RECENT_*_THRESHOLD_SECS`, `PAST_*_THRESHOLD_SECS`).

## Icon vs path update shape

LocationView SVG icons and SVG paths react to status updates through different opt-ins, and the asymmetry is intentional.

- **Icons** (`<g>` elements) declare `data-status`. The polling dispatcher writes only the `status` attribute; CSS rules keyed on `g[status="..."]` (and nested selectors like `g[status="off"] path.hi-state-bg`) supply the visual styling.
- **Paths** (`<path>` elements) declare `data-svg-style`. The dispatcher writes the full bundle (`status`, `stroke`, `stroke-width`, `fill`, `fill-opacity`, `stroke-dasharray`) as inline SVG attributes; CSS only adds drop-shadow on top.

Icons can't safely receive the full bundle because they are multi-element. A typical icon `<g>` wraps several primitives — body, outline, background plate — each of which may want differentiated styling for a given status. If the dispatcher pushed `fill="red"` onto the parent `<g>`, SVG attribute inheritance would paint every child red, overriding child-specific CSS. Per-child selectors are the only mechanism that gives each child independent control, which is why icons confine themselves to pushing the `status` attribute and letting CSS branch from there.

Paths can use the full bundle because they are single-element — one `<path>` per region, no inheritance hazard — and their per-entity-type palette (movement vs smoke vs open/close, each with its own colors) is naturally expressed by Python's `StatusStyle` rather than as a Cartesian product of CSS rules. The attribute-driven path also leaves room for future continuous-value visuals (e.g., opacity proportional to a numeric magnitude) which closed-set CSS rules can't express.

When adding a new visual, copy from an existing icon or path of the same shape — the right opt-in comes along.

## Panel JS hooks

Surfaces that need per-tick behavior beyond what the declarative contract expresses (e.g., a thermostat dial whose SVG marker angles are computed from numeric magnitudes) register a handler:

- **`Hi.statePanels.registerUpdate(handler)`** — fires after each polling apply pass, receiving the full status map. For refresh-time work the declarative contract can't express.
- **`Hi.statePanels.registerInit(handler)`** — fires at jQuery ready and after every async content insertion (modal opens, fragment loads). For positioning elements from server-rendered initial data. Handlers must be idempotent — they re-scan the document on each call.

See [`entity_state_status.js`](../../../src/hi/static/js/entity_state_status.js) for the API and [`state_panels/thermostat/thermostat.js`](../../../src/hi/static/state_panels/thermostat/thermostat.js) for a canonical example using both hooks.

## Related documentation

- [Architecture overview](entity-display-overview.md)
- [Panel authoring](entity-status-panels.md)
- [SVG asset authoring](entity-visual-configuration.md)
- [Style guidelines](style-guidelines.md)
- [Template conventions](template-conventions.md)
