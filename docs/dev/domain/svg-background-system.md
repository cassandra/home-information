# SVG Background System

## Overview

Each Location in Home Information has a background SVG image that provides the visual context for the spatial layout. The background SVG is rendered behind entity icons and paths. Users can customize their background using the built-in SVG editor, by selecting from predefined templates, or by uploading their own SVG files.

## Architecture

### Storage

- **MEDIA_ROOT**: Background SVGs are stored as fragment files (inner content without the `<svg>` wrapper). The Location model's `svg_fragment_filename` field points to this file.
- **Templates**: Predefined backgrounds are Django templates at `src/hi/apps/profiles/templates/profiles/svg/backgrounds/`. These are full SVG files (with `<svg>` wrapper and viewBox) that get rendered, stripped, and written to MEDIA_ROOT.
- **Editor palette**: The shared palette definitions live at `src/hi/apps/location/templates/location/edit/svg/svg_edit_palette.svg`. This is injected into the editor's DOM at runtime by the editor canvas template (`src/hi/apps/location/templates/location/edit/panes/location_svg_edit_canvas.html`), not stored in the SVG files themselves.

### SVG Processing Pipeline

All SVG content (uploaded, template-rendered, or editor-saved) goes through `hi.apps.common.svg_utils.process_svg_content()` which validates structure, extracts the viewBox, strips the outer `<svg>` element, cleans XML namespaces, scans for dangerous elements, and generates a unique timestamped filename for MEDIA_ROOT.

### Rendering

The background SVG fragment is rendered via the `{% include_media_template %}` custom template tag (`hi.apps.common.templatetags.common_tags`), which reads from MEDIA_ROOT and renders as a Django template within the Location view's `<svg>` element.

## Editor-Compatible SVG Structure

The canonical reference for the editor-compatible SVG structure is the editor canvas template at `src/hi/apps/location/templates/location/edit/panes/location_svg_edit_canvas.html`. This template shows how the SVG is assembled: fill pattern `<defs>`, the palette `<defs>` (injected here as a sibling, not stored in the SVG files), and the background content loaded from MEDIA_ROOT.

### Element Types

Background elements use three editing modes, specified by the `data-bg-edit-type` attribute:

- **Closed paths** (`closed`): Polygonal areas (`M...L...Z`). Edited by manipulating vertices.
- **Open paths** (`open`): Line segments (`M...L`). Visual thickness from CSS `stroke-width`. Include a duplicate `<path class="hi-bg-hit-area">` for click targeting.
- **Icons** (`icon`): Predefined shapes positioned via SVG `transform`. Include a `<rect class="hi-bg-hit-area">` for click targeting.

### Layer Ordering

Elements are ordered back-to-front in the SVG DOM, with layer numbers controlling insertion order. The layer definitions and their enforcement are in the JS palette drop handler in `src/hi/static/js/location-svg-edit.js` (see the `insertAtLayer` function). The correct ordering matters for visual rendering — ground elements must be behind walls, which must be behind doors, etc.

## Palette System

The palette defines the set of element types available in the background editor. Each palette item is a `<g>` element inside a `<defs>` block containing the canonical shape and metadata attributes.

**Palette definition file**: `src/hi/apps/location/templates/location/edit/svg/svg_edit_palette.svg`

The palette is injected into the editor's SVG DOM at runtime. It is NOT stored in MEDIA_ROOT SVG files.

### How to Add a New Palette Item

1. **Add the `<defs>` entry** in `svg_edit_palette.svg`:
   ```xml
   <g id="hi-my-new-type" data-bg-edit-type="closed" data-bg-label="My Type"
      data-bg-category="features" data-bg-layer="6">
     <path class="my-new-type" d="M 0,0 L 80,0 L 80,40 L 0,40 Z" />
   </g>
   ```
   - `id`: Must be `hi-{type-name}`. The `hi-` prefix is stripped to derive `data-bg-type` for placed elements.
   - `data-bg-edit-type`: `icon`, `open`, or `closed`
   - `data-bg-label`: Display name shown in the palette UI
   - `data-bg-category`: `structural`, `features`, or `exterior` (determines palette grouping)
   - `data-bg-layer`: Rendering layer number (see Layer Ordering above)
   - Inner `<path>`: Default geometry with the CSS class for styling

2. **Add CSS styling** in `src/hi/static/css/svg-location-color.css`:
   ```css
   svg.hi-location-view-svg path.my-new-type {
       fill: #color;
       stroke: black;
       stroke-width: 1;
   }
   ```
   This styling applies both in the editor and in the normal Location view.

3. **Add palette swatch CSS** in `src/hi/static/css/location-svg-edit.css` (in the "Palette Swatch Fills" section):
   ```css
   .hi-palette-swatch path.my-new-type { fill: #color; stroke: black; stroke-width: 1; }
   ```
   Swatches use flat colors since fill patterns from the main SVG are not available in the separate palette mini-SVGs.

4. **For open-path types** (like walls): Hit areas are handled by the shared `.hi-bg-hit-area` CSS rules already in `svg-location-color.css`. No additional CSS needed.

5. **For new icon types**: The `<defs>` entry defines the canonical shape. When dragged from the palette, the JS creates an inline copy with a `transform` attribute and a `<rect class="hi-bg-hit-area">` for click targeting.

## Background Templates

### What is a Background Template

A background template is a Django template file (`.svg` extension) containing a complete SVG document. Templates are rendered via `render_to_string()`, processed through `process_svg_content()`, and the resulting fragment is written to MEDIA_ROOT.

**Template directory**: `src/hi/apps/profiles/templates/profiles/svg/backgrounds/`

Templates placed in this directory automatically appear in the "Choose a Template" modal. The display name is derived from the filename (hyphens to spaces, version suffix stripped, title-cased) or from the `data-hi-name` attribute on the outer `<g>` element.

### How to Add a New Template

1. **Create the SVG using the editor**: Use the background editor to build the floor plan.
2. **Export it**: Click the EXPORT button in the editor footer to download the SVG file.
3. **Copy to the templates directory**: Place the downloaded file in the backgrounds template directory listed above.
4. **Name it**: Use lowercase with hyphens and a numeric version suffix: `my-layout-0.svg`
5. **Verify the `data-hi-name`**: Check that the outer `<g>` has `data-hi-name="My Layout"`. The EXPORT includes this if the SVG was editor-compatible. Add it manually if needed.

### Template Format

A minimal template:
```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 2000 2000">
<g data-hi-editor="1" data-hi-name="My Template">
  <!-- Placed elements here, ordered by layer -->
</g>
</svg>
```

Templates can use Django template tags (e.g., `{% include %}`) but currently none do — the palette defs are injected separately by the editor canvas template.

## Key Files

| File | Purpose |
|------|---------|
| `src/hi/apps/common/svg_utils.py` | SVG processing pipeline (`process_svg_content`) |
| `src/hi/apps/common/svg_forms.py` | Form-based SVG handling for user uploads |
| `src/hi/apps/location/location_manager.py` | SVG file management, draft system, template rendering |
| `src/hi/apps/location/templates/location/edit/svg/svg_edit_palette.svg` | Palette definitions |
| `src/hi/apps/location/templates/location/edit/panes/location_svg_edit_canvas.html` | Editor canvas rendering |
| `src/hi/apps/profiles/templates/profiles/svg/backgrounds/` | Background SVG templates |
| `src/hi/static/css/svg-location-color.css` | SVG element styling (shared between editor and normal views) |
| `src/hi/static/css/location-svg-edit.css` | Editor-specific styling (palette swatches, layout) |
| `src/hi/static/js/location-svg-edit.js` | Editor initialization, palette building, draft save, drag-and-drop |
| `src/hi/static/js/svg-icon-core.js` | Icon editing core (drag, scale, rotate, mirror) |
| `src/hi/static/js/svg-path-core.js` | Path editing core (proxy points, vertex manipulation) |
| `src/hi/static/js/svg-pan-zoom-core.js` | Pan/zoom core (viewBox manipulation) |
| `src/hi/static/js/svg-bg-event-listeners.js` | Event dispatcher for editor context |
