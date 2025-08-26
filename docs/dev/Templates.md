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

### When to Use Icons

**Use icons for:**
- Navigation actions (arrows, expand/collapse)
- Common operations (add, edit, delete, save)
- Media controls (play, video, camera)
- Status indicators

**Avoid icons for:**
- Complex or abstract concepts
- Text that is already descriptive
- Application-specific terminology

### Requirements

- Always include `{% load icons %}` at top of templates
- Icons must supplement text, not replace it
- Use semantic size and color parameters when available
- Include appropriate ARIA labels for accessibility

### Example

```django
{% load icons %}

<button class="btn btn-primary">
  {% icon "plus" size="sm" css_class="hi-icon-left" %}
  Add Item
</button>
```

See existing templates for more examples.
