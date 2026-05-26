# Entity Visual Configuration

Configuring the visual representation of an `EntityType` on the LocationView map: SVG icon assets, area-based path assets, and the `StatusStyle` that drives their per-status appearance.

**Related docs:**
- [`entity-display-overview.md`](entity-display-overview.md) — high-level architecture and how LocationView visuals fit alongside the other display surfaces.
- [`entity-status-display.md`](entity-status-display.md) — the polling-update contract. Map icons and paths automatically receive live updates via this contract; the rendering templates ([`svg_icon_item.html`](../../../src/hi/apps/location/templates/location/panes/svg_icon_item.html) and [`svg_path_item_{open,closed}.html`](../../../src/hi/apps/location/templates/location/panes/)) emit the necessary `data-state-id` and declaration attributes for you.

## Overview

The LocationView map represents each positioned entity in one of two ways:

- **Icon**: an SVG `<g>` group containing the type's drawing commands, positioned, scaled, and rotated per the entity's `EntityPosition`. Used for point-like entities (sensors, switches, cameras).
- **Path**: an SVG `<path>` element drawn from the entity's `EntityPath` data. Used for area-like entities (rooms, zones, boundaries).

Choice is driven by `EntityType` registration — each type belongs to either the icon registry or one of the path registries. The framework hands the chosen template a populated `SvgIconItem` or `SvgPathItem` and renders it inside the LocationView SVG; live status updates flow through the polling dispatcher automatically.

### Key configuration files

- **Icons**: SVG drawing fragments at `src/hi/apps/entity/templates/entity/svg/type.{TYPE}.svg`
- **Registration and styling**: [`src/hi/hi_styles.py`](../../../src/hi/hi_styles.py) — `EntityStyle.EntityTypesWithIcons`, `EntityStyle.EntityTypeClosedPaths`, `EntityStyle.EntityTypeOpenPaths`, `EntityStyle.PathEntityTypeToSvgStatusStyle`, and the `StatusStyle` palette.
- **Rendering templates** (do not modify per-type — they read from `SvgIconItem` / `SvgPathItem`): [`svg_icon_item.html`](../../../src/hi/apps/location/templates/location/panes/svg_icon_item.html), [`svg_path_item_open.html`](../../../src/hi/apps/location/templates/location/panes/svg_path_item_open.html), [`svg_path_item_closed.html`](../../../src/hi/apps/location/templates/location/panes/svg_path_item_closed.html).
- **Factory**: [`svg_item_factory.py`](../../../src/hi/apps/location/svg_item_factory.py) — assembles `SvgIconItem` / `SvgPathItem` instances from entities, positions, and `StatusStyle`.

## Adding visual support for a new `EntityType`

### 1. Choose icon or path

- **Icon**: point-like entities — sensors, switches, cameras, displays.
- **Path**: area-like entities — rooms, zones, boundary lines.

### 2a. Icon-based configuration

**Create the SVG drawing fragment** at `src/hi/apps/entity/templates/entity/svg/type.<type_name>.svg` (where `<type_name>` is `EntityType.name.lower()`). Requirements:

- **No `<svg>` or `<g>` wrapper** — the LocationView's `svg_icon_item.html` template provides the wrapping `<g>` along with positioning transforms and the polling-update data attributes. The fragment should contain only drawing commands.
- **Clickable background**: include a transparent rectangle covering the entire viewbox so the whole icon area receives pointer events:
  ```svg
  <rect class="hi-entity-bg" x="0" y="0" width="64" height="64" fill="none"/>
  ```
- **Default viewbox is `0 0 64 64`.** Register a custom viewbox in `EntityStyle.EntityTypeToIconViewbox` if the design needs different proportions.

**Register the type** in `EntityStyle.EntityTypesWithIcons` (a set of `EntityType` values).

The icon receives its visual styling from CSS rules keyed on `g[status="..."]` and from the bucketed `status_value` produced per-state-type by [`EntityStateDisplayData._get_svg_status_style`](../../../src/hi/apps/monitor/display_data.py). For why icons use CSS-driven (not attribute-driven) styling, see [`entity-status-display.md`](entity-status-display.md#icon-vs-path-update-shape).

### 2b. Path-based configuration

**Pick the registry** — closed (filled) or open (line) paths:
- Closed: `EntityStyle.EntityTypeClosedPaths`
- Open: `EntityStyle.EntityTypeOpenPaths`

**Bind a `StatusStyle`** for the entity type in `EntityStyle.PathEntityTypeToSvgStatusStyle`. The `StatusStyle` instance defines stroke color, stroke width, fill color, fill opacity, dasharray — all attributes the polling dispatcher will push onto the path element on each refresh.

For the existing palette of `StatusStyle` instances and the status-value vocabulary they emit (`active`, `idle`, `recent`, `past`, `smoke_detected`, etc.), see [`StatusStyle` in `hi_styles.py`](../../../src/hi/hi_styles.py) and the status-vocabulary discussion in [`entity-status-display.md`](entity-status-display.md#status-value-vocabulary).

**Optional**: customize default path sizing in `EntityStyle.EntityTypePathInitialRadius` if your area type wants a non-default initial radius when first created.

### 3. Assign the type to an `EntityGroupType` bucket

Every new `EntityType` must be added to exactly one `EntityGroupType.entity_type_set` in [`src/hi/apps/entity/enums.py`](../../../src/hi/apps/entity/enums.py). The buckets organize the entity-editing and collection-editing UI group lists and serve as the default grouping dimension on the integration placement modal — a type with no explicit assignment silently falls into `GENERAL`. Pick the most natural domain bucket (`AUTOMATION`, `SECURITY`, `APPLIANCES`, etc.); reserve `GENERAL` for types that genuinely don't fit a domain.

## Visual asset guidelines

### SVG icon design

- Design to a 64×64 viewbox unless registering a custom one.
- Use `currentColor` for primary elements that should inherit state color through CSS.
- Use fixed colors sparingly for distinctive details.
- Maintain visibility at small scales (icons render down to ~16px in dense map views).
- Follow the visual language of existing icons (similar stroke weights, fill patterns, metaphors).

### Path styling

- Provide meaningful defaults for the idle state.
- Use color temperature progression (warm = active, cool = idle).
- Consider opacity for layered visual effects (overlapping coverage zones).

## Testing

1. Create an instance of the new entity type via the admin or simulator.
2. Position it on a location.
3. Trigger state changes via the integration or simulator.
4. Open the LocationView and verify:
   - Icon renders at the expected position, scale, and rotation.
   - Status changes update the visual (color tint, drop-shadow glow, etc.) within one polling cycle.
   - Click target covers the whole icon (the `hi-entity-bg` rectangle).
5. Open a collection containing the entity and verify the cards render reasonably; for entity types with custom panel needs see [`entity-state-panels.md`](entity-state-panels.md).

## Simulator integration (optional)

If the new entity type should be exercisable from the simulator, add it to `SimEntityType` in `hi.simulator.enums` and provide the matching simulator-side rendering and state machinery.

## Related documentation

- [Architecture overview](entity-display-overview.md)
- [Polling-update contract](entity-status-display.md)
- [Panel authoring](entity-state-panels.md)
- [Icon system](icon-system.md)
- [Style guidelines](style-guidelines.md)
