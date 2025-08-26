<img src="../../src/hi/static/img/hi-logo-w-tagline-197x96.png" alt="Home Information Logo" width="128">

# Django Templates

## Template naming conventions

- `pages` - For full HTML pages
- `modals` - For HTML modals
- `panes` - For all other HTML page fragments
- `email` - For email templates
- `svg` - for SVG files.

For app modules that also define some separate "edit" views, they will be in the same structure, one level down in an `edit` subdirectory.

## The "Hi Grid" Template Structure

_TBD_

### Important DIV Ids

This are gathered in `src/hi/constants.py:DIV_IDS`:

- `#hi-main-content` - This is the main display area, excluding header buttons, footer buttons and the side panel.
- `#hi-side-content`
- `#hi-top-buttons`
- `#hi-button-bottons`
- `#hi-config-integration-tab` - Integrations use this for any configuration-related views.

## Icon Usage Guidelines

### Icon System

Use the standardized `{% icon %}` template tag. See `hi/apps/common/templatetags/icons.py` for implementation details and parameters.

### UX Principles for Icon Usage

**Primary Value**: Icons provide faster recognition, universal language, space efficiency, and visual hierarchy.

**ALWAYS Add Icons When:**
- **Universal Actions**: Add (+), Delete (trash), Edit (pencil), Save (checkmark), Cancel (×)
- **Navigation**: Back/Forward arrows, Up/Down, Expand/Collapse
- **Media Controls**: Play, Pause, Video, Camera
- **Status/Feedback**: Success, Warning, Error, Info

**Key Principle**: Focus on **ACTION TYPE** (add, delete, edit), not object specificity. "Add Item" and "Add Rule" both get the same + icon because they're both "add" actions.

### Implementation Requirements

- Always include `{% load icons %}` at top of templates
- Icons should supplement text, not replace it for important actions
- Use semantic size and color parameters when available
- Include appropriate ARIA labels for accessibility
- Maintain consistency: same action = same icon across the application

### Examples

```django
{% load icons %}

<!-- Primary action with icon -->
<button class="btn btn-primary">
  {% icon "plus" size="sm" css_class="hi-icon-left" %}
  Add New Rule
</button>

<!-- Edit action -->
<a class="btn btn-secondary" href="/edit/">
  {% icon "edit" size="sm" css_class="hi-icon-left" %}
  Edit
</a>

<!-- Save/Submit action -->
<button class="btn btn-success" type="submit">
  {% icon "save" size="sm" css_class="hi-icon-left" %}
  Save Changes
</button>

<!-- Cancel action -->
<a class="btn btn-tertiary" href="#" data-dismiss="modal">
  {% icon "cancel" size="sm" css_class="hi-icon-left" %}
  Cancel
</a>

<!-- Delete action - icon-only for space constraints -->
<button class="btn btn-danger" aria-label="Delete item">
  {% icon "delete" size="sm" %}
</button>

<!-- Modal close - icon-only (universal convention) -->
<button type="button" class="close" data-dismiss="modal" aria-label="Close">
  {% icon "close" size="sm" %}
</button>
```

**Available Icons**: See `hi/apps/common/templatetags/icons.py` for the complete list of available icons.

See existing templates for more examples.
