# Entity State Panels

EntityStatePanels render the body of the entity status modal and of the per-entity cards inside collections. The framework dispatches per-`EntityType`, picking from one or more **panel declarations** that target that type. Each panel can present its entity in whatever form best fits — a flat state list, a graphical dial, a video frame, etc. — while the surrounding modal / card chrome stays uniform.

This document covers authoring a new panel.

**Related docs:**
- [`entity-display-overview.md`](entity-display-overview.md) — high-level architecture and how panels fit alongside the other display surfaces.
- [`entity-status-display.md`](entity-status-display.md) — the polling-update contract that panel templates and panel JS plug into.

## Concepts

A panel is a Python declaration plus a bundle of templates and static assets:

- The **declaration** (an `EntityStatePanel` instance constructed in `panel.py`) names the panel, the `EntityType` it claims, the `DisplayContext`s it handles, its priority, and the `EntityStateRole`s it requires and optionally uses.
- The **template** renders the panel body. Templates are context-agnostic: panels that need to look meaningfully different across display contexts should split into separate declarations, not branch inside a single template.
- The **static** assets — CSS and optional JS — handle visual styling and any custom polling-time behavior.

**EntityType is user-adjustable and is decoupled from an entity's actual `EntityStateRole` set.** A user can mark any entity as `THERMOSTAT` regardless of which states it happens to expose. The framework therefore selects panels by the intersection of `(EntityType, DisplayContext, EntityStateRoles present)` and provides framework-level behavior when no panel matches.

A single `EntityType` may have multiple panel declarations, distinguished by their required-role sets and their display contexts. This is the recommended way to express layout variants (single setpoint vs dual setpoint, modal-vs-grid divergence, etc.) — separate panels rather than conditional templates.

When no panel matches, the framework falls back to a flat state list. The fallback is itself a registered panel — see `state_panels/fallback/`.

## Anatomy

```
src/hi/apps/entity/state_panels/<name>/
    panel.py            # required: one or more EntityStatePanel instances at module scope

src/hi/apps/entity/templates/entity/state_panels/<name>/
    <author-chosen>.html  # the template(s) named by panel.py

src/hi/static/state_panels/<name>/
    <author-chosen>.css   # optional
    <author-chosen>.js    # optional, registers JS handlers
```

`<name>` is the panel's unique identifier and also the directory name. It is not tied to `EntityType.name` — multiple panels per type share the type but have distinct names (e.g. `thermostat_dual_setpoint`, `thermostat_single_setpoint`).

There is no enforced template filename. The declaration names the template explicitly; convention is to keep it under `entity/state_panels/<name>/`. Whether one panel uses one template across all its declared contexts, or different panels use different templates per context, is the author's call expressed through the declaration set.

## Panel declaration

Each panel is an [`EntityStatePanel`](../../../src/hi/apps/entity/state_panel_base.py) dataclass instance with the following fields:

| Field | Required | Meaning |
|---|---|---|
| `name` | yes | Unique identifier across all panels. By convention matches the directory name under `state_panels/`. |
| `display_contexts` | yes | Set of `DisplayContext` members this panel handles. No implicit inheritance: declaring `{DisplayContext.MODAL}` does not make the panel apply elsewhere. |
| `priority` | yes | Lower checked first; alphabetical `name` is a stable tiebreaker. |
| `template_name` | yes | Template path (e.g. `entity/state_panels/thermostat_single_setpoint/panel.html`). |
| `entity_type` | optional | The `EntityType` this panel claims. `None` (the default) marks a framework fallback panel: matched only after no type-specific panel matches. |
| `required_roles` | optional | Conjunctive. Panel is selected only when every role is present on the entity. Once selected, the template may assume every required role is in `state_status_data_by_role`. Defaults to empty. |
| `optional_roles` | optional | Roles the panel knows about and will display when present. Templates use `{% if %}` only for these. Defaults to empty. |

`required_roles` and `optional_roles` must be disjoint. Together they form the panel's **declared** role set; any `EntityStateRole` on the entity outside this set is an **extra** (see "Display contexts and extras" below).

Worked example:

```python
# src/hi/apps/entity/state_panels/thermostat_single_setpoint/panel.py
from hi.apps.entity.enums import DisplayContext, EntityStateRole, EntityType
from hi.apps.entity.state_panel_base import EntityStatePanel


panel = EntityStatePanel(
    name = 'thermostat_single_setpoint',
    entity_type = EntityType.THERMOSTAT,
    display_contexts = { DisplayContext.MODAL, DisplayContext.LIST, DisplayContext.GRID },
    priority = 20,
    required_roles = {
        EntityStateRole.THERMOSTAT_CURRENT_TEMPERATURE,
        EntityStateRole.THERMOSTAT_TARGET_TEMPERATURE,
        EntityStateRole.HVAC_ACTION,
    },
    optional_roles = {
        EntityStateRole.HVAC_MODE,
        EntityStateRole.FAN_MODE,
        EntityStateRole.PRESET_MODE,
        EntityStateRole.HUMIDITY,
    },
    template_name = 'entity/state_panels/thermostat_single_setpoint/panel.html',
)
```

At app-ready time, [`state_panel_registry.py`](../../../src/hi/apps/entity/state_panel_registry.py) imports each `state_panels/<name>/panel.py` and registers every `EntityStatePanel` instance at module scope. A module may declare one panel (typical) or multiple (siblings sharing CSS/JS or a templates directory).

For the resolution algorithm the framework uses to choose among matching declarations, read [`state_panel_dispatch.py`](../../../src/hi/apps/entity/state_panel_dispatch.py) directly.

## Display contract

Every `EntityStateRole` declared in `required_roles` or `optional_roles` is the panel's promise to the user: the panel must display the state (or its control) for any declared role that is present. If the panel does not show a role, it must not be in the declaration. Required-role guarantees let the template skip the `{% if %}` guard; optional-role presence is checked with `{% if %}`.

Extras — roles on the entity outside the panel's declared set — are framework-owned. The panel template does not see them.

## Display contexts and extras

| `DisplayContext` | Extras behavior |
|---|---|
| `MODAL` | Framework auto-appends an expandable **"Other states"** section below the panel chrome whenever extras exist. Renders each extra row using the existing fallback `state_row.html`. |
| `LIST`  | Framework ignores extras silently. |
| `GRID`  | Framework ignores extras silently. |

This produces a framework-level invariant for the modal context: **every `EntityState` on an entity is reachable in the modal view, always.** Either the active panel handles it (declared role) or the framework surfaces it (extra). Authors cannot opt out — the contract belongs to the user.

Grid and list are compact-by-intent; extras are intentionally invisible there to keep card layouts tight. Users who want to see every state open the modal.

## Template authoring

Panel templates render inside the wrapper's chrome. They must not duplicate the entity name, integration logo, or type label that the wrapper already supplies.

When a panel template runs, the parent context plus the entity's display projection are flattened together, so the following names are top-level:

| Name | What it is |
|---|---|
| `entity` | The `Entity` model instance. |
| `entity_status_data` | The `EntityDisplayData` wrapper. |
| `state_status_data_list` | Ordered list of `EntityStateDisplayData` for the entity's states (sorted per `ENTITY_STATUS_VIEW_ORDERING`). |
| `state_status_data_by_role` | Dict keyed by lowercase `EntityStateRole.name`. **Every required role is guaranteed present in this dict** for the selected panel. |
| `entity_for_video` | The `Entity` whose video stream this panel should embed, or `None`. |
| `display_only_svg_icon_item` | The framework `SvgIconItem` for the entity's type icon, or `None`. |
| `display_category` | `EntityDisplayCategory` enum value for layout hints (`HAS_VIDEO` / `HAS_STATE` / `PLAIN`). |

Source of truth: `EntityDisplayData.to_template_context()` in [`display_data.py`](../../../src/hi/apps/monitor/display_data.py).

Required-role access reads cleanly without `{% if %}`:

```django
{% with current_data=state_status_data_by_role.thermostat_current_temperature %}
  <span data-state-id="{{ current_data.entity_state.id }}"
        data-display-text>{{ current_data.display.text }}</span>
{% endwith %}
```

Optional-role access guards with `{% if %}`:

```django
{% with fan_data=state_status_data_by_role.fan_mode %}
  {% if fan_data %}
    <!-- render fan controls -->
  {% endif %}
{% endwith %}
```

For the live-update declaration grammar, server payload shape, and the icon-vs-path asymmetry, see [`entity-status-display.md`](entity-status-display.md). Authoring a panel template is mostly a matter of (1) pulling the right state via `state_status_data_by_role` or `state_status_data_list`, and (2) tagging the elements that should refresh.

## JS extensions

Most panels need no JavaScript — declarative HTML attributes and CSS rules carry all the live-update work. When more is needed (e.g., re-positioning an SVG marker from a numeric magnitude), register a handler with `Hi.statePanels`:

- **`Hi.statePanels.registerUpdate(handler)`** — fires after each polling apply pass, receiving the full status map keyed by state id. Use this for refresh-time work the declarative contract can't express.
- **`Hi.statePanels.registerInit(handler)`** — fires on initial page load *and* after every async content insertion (entity status modal opens, collection refreshes). Use this to position elements from server-rendered data. Handlers must be idempotent — they re-scan the document on each call.

API source: [`entity_state_status.js`](../../../src/hi/static/js/entity_state_status.js).

### Keeping render-time and update-time in sync

Templates render initial values into HTML — often as `data-*` attributes on the same elements that opt into the polling contract. The polling-update apply pass then refreshes those values on each tick. When a panel does *further* derivation from those values — for example, computing an SVG marker angle from a numeric magnitude carried in `data-temp-value` — that derivation must run in both places: once via `registerInit` against the server-rendered initial value, and again via `registerUpdate` for every subsequent tick. Both hooks should call the same routine so the initial frame and every later frame stay consistent.

This is why derivations live in JS, not in a parallel Python helper: a Python implementation would only run at render time, leaving update-time to do the same math separately and drift.

## Debug

Append `?debug_panel=1` to any view that renders an entity status panel to see the dispatch trace inline (and in the DEBUG log).

## Walkthrough: adding a panel

1. Pick a `<name>` unique across all panels (typically `<entity_type>_<variant>` if variants are anticipated, or just `<entity_type>` for a single panel).
2. Create `src/hi/apps/entity/state_panels/<name>/panel.py` that constructs an `EntityStatePanel` at module scope. Set `display_contexts`, `priority`, `required_roles`, `optional_roles`, `template_name`, and `entity_type` (omit `entity_type` only if the panel is a framework fallback).
3. Create the template at the path named by `template_name`.
4. Fetch required-role states via `state_status_data_by_role.<role_name>` (lowercase `EntityStateRole.name`) — no `{% if %}` needed. Guard optional-role access with `{% if %}`.
5. Tag refreshable elements per the polling-update contract (see [`entity-status-display.md`](entity-status-display.md)).
6. Drop panel-private CSS and JS in `src/hi/static/state_panels/<name>/` if needed.
7. Register any panel JS handlers via `Hi.statePanels.registerInit` / `registerUpdate`.
8. Verify in the simulator: open the entity status modal, change values on the simulator side, watch the panel refresh; open a collection containing the entity and check the list and grid contexts. If the panel doesn't render where expected, hit the URL with `?debug_panel=1` and check the resolution trace.

## Exemplars

Read the existing panels when starting a new one — copy from the closest match.

- **[`fallback/`](../../../src/hi/apps/entity/templates/entity/state_panels/fallback/)** — universal flat state list. Authors needing the standard rendering can include `fallback/state_list.html` directly.
- **[`smoke_detector/`](../../../src/hi/apps/entity/templates/entity/state_panels/smoke_detector/)** — CSS-only panel. Status-attribute-driven variants switch icon and label visibility without any JS.
- **[`thermostat_*`](../../../src/hi/apps/entity/templates/entity/state_panels/)** — multi-declaration thermostat family. Role-keyed state lookups, custom CSS, init + update JS hooks for an SVG dial.
- **[`camera/`](../../../src/hi/apps/entity/templates/entity/state_panels/camera/)** — embeds the live view alongside camera controls.

## Pitfalls

- **`data-svg-style` is for single-element styling.** Don't put it on a multi-element SVG `<g>` icon — children inherit the pushed `fill`/`stroke` attributes and lose their differentiated styling. Use `data-status` and CSS branching instead. See [`entity-status-display.md`](entity-status-display.md#icon-vs-path-update-shape) for the full rationale.
- **Init handlers must be idempotent.** `registerInit` fires on both initial DOM-ready and every async content insertion. Handlers re-scan the document each time; applying state to already-initialized elements must be safe.
- **Don't duplicate chrome.** The modal wrapper supplies the type icon, entity name, integration logo, and type label in its subheader. The collection-card wrappers supply the entity-name title and (when applicable) the video stream. Panel bodies render below this chrome and should not repeat any of it.
- **Don't render extras inside the panel.** The modal context auto-appends an "Other states" section for any role outside the panel's declared set. Panels that try to render unknown states inside their own chrome will duplicate them.
- **Declare what you display, display what you declare.** If a role appears in `required_roles` or `optional_roles`, the template must render it (subject to `{% if %}` for optionals). If a role is rendered but not declared, the framework will still treat it as an "extra" and may surface it twice in modal.
- **Don't branch a template by `DisplayContext`.** If the panel needs context-specific layout, split into separate declarations with their own templates rather than `{% if context == ... %}` inside one file.
- **Shared partials live where they were first authored.** The flat state list and per-state row templates live under `state_panels/fallback/` (where they were born). Other panels that want the same list reference them from that path; there's no separate "shared" namespace.
