# Icon System

## Icon System Overview

Use the standardized `{% icon %}` template tag. See `hi/apps/common/templatetags/icons.py` for implementation details and parameters.

## UX Principles for Icon Usage

### Primary Value
Icons provide faster recognition, universal language, space efficiency, and visual hierarchy.

### ALWAYS Add Icons When

- **Universal Actions**: Add (+), Delete (trash), Edit (pencil), Save (checkmark), Cancel (×)
- **Navigation**: Back/Forward arrows, Up/Down, Expand/Collapse
- **Media Controls**: Play, Pause, Video, Camera
- **Status/Feedback**: Success, Warning, Error, Info

### Key Principle
Focus on **ACTION TYPE** (add, delete, edit), not object specificity. "Add Item" and "Add Rule" both get the same + icon because they're both "add" actions.

## Implementation Requirements

- Always include `{% load icons %}` at top of templates
- Icons should supplement text, not replace it for important actions
- Use semantic size and color parameters when available
- Include appropriate ARIA labels for accessibility
- Maintain consistency: same action = same icon across the application

## Template Usage Examples

### Basic Icon Usage

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
```

### Icon-Only Actions

Use for space-constrained areas with proper accessibility:

```django
<!-- Delete action - icon-only for space constraints -->
<button class="btn btn-danger btn-sm" aria-label="Delete item">
  {% icon "delete" size="sm" %}
</button>

<!-- Modal close - icon-only (universal convention) -->
<button type="button" class="close" data-dismiss="modal" aria-label="Close">
  {% icon "close" size="sm" %}
</button>

<!-- Toolbar actions -->
<div class="btn-group" role="group">
  <button type="button" class="btn btn-outline-secondary" aria-label="Bold">
    {% icon "bold" size="sm" %}
  </button>
  <button type="button" class="btn btn-outline-secondary" aria-label="Italic">
    {% icon "italic" size="sm" %}
  </button>
  <button type="button" class="btn btn-outline-secondary" aria-label="Underline">
    {% icon "underline" size="sm" %}
  </button>
</div>
```

### Status and Feedback Icons

```django
<!-- Success message -->
<div class="alert alert-success">
  {% icon "check-circle" size="sm" css_class="hi-icon-left" %}
  Operation completed successfully!
</div>

<!-- Warning message -->
<div class="alert alert-warning">
  {% icon "exclamation-triangle" size="sm" css_class="hi-icon-left" %}
  Please review your settings before continuing.
</div>

<!-- Error message -->
<div class="alert alert-danger">
  {% icon "times-circle" size="sm" css_class="hi-icon-left" %}
  An error occurred while processing your request.
</div>

<!-- Info message -->
<div class="alert alert-info">
  {% icon "info-circle" size="sm" css_class="hi-icon-left" %}
  This feature is currently in beta.
</div>
```

### Navigation Icons

```django
<!-- Breadcrumb navigation -->
<nav aria-label="breadcrumb">
  <ol class="breadcrumb">
    <li class="breadcrumb-item">
      <a href="{% url 'home' %}">
        {% icon "home" size="sm" css_class="hi-icon-left" %}
        Home
      </a>
    </li>
    <li class="breadcrumb-item">
      <a href="{% url 'entities' %}">Entities</a>
    </li>
    <li class="breadcrumb-item active">Edit Entity</li>
  </ol>
</nav>

<!-- Back button -->
<a href="{{ back_url }}" class="btn btn-secondary">
  {% icon "arrow-left" size="sm" css_class="hi-icon-left" %}
  Back
</a>

<!-- Pagination -->
<nav>
  <ul class="pagination">
    <li class="page-item">
      <a class="page-link" href="?page={{ page.previous_page_number }}">
        {% icon "chevron-left" size="sm" %}
        Previous
      </a>
    </li>
    <li class="page-item active">
      <span class="page-link">{{ page.number }}</span>
    </li>
    <li class="page-item">
      <a class="page-link" href="?page={{ page.next_page_number }}">
        Next
        {% icon "chevron-right" size="sm" %}
      </a>
    </li>
  </ul>
</nav>
```

## Icon Parameters

All icon CSS rules are defined in `src/hi/static/css/icons.css`.

### Size Options
- `xs` - Extra small (12px)
- `sm` - Small (16px) - **Most common**
- `md` - Medium (20px) - Default
- `lg` - Large (24px)
- `xl` - Extra large (32px)

### CSS Classes
- `hi-icon-left` - Icon positioned to the left of text
- `hi-icon-right` - Icon positioned to the right of text
- `hi-icon-only` - Icon without accompanying text
- `hi-icon-spin` - Spinning animation for loading states

### Color Options
When available through the icon system:
- `text-primary` - Primary theme color
- `text-success` - Success/positive actions
- `text-warning` - Warning/caution
- `text-danger` - Danger/destructive actions
- `text-muted` - Subtle/disabled state

## Accessibility Considerations

### ARIA Labels

Always provide ARIA labels for icon-only buttons:

```django
<button class="btn btn-primary" aria-label="Edit entity settings">
  {% icon "edit" size="sm" %}
</button>
```

### Screen Reader Support

For decorative icons, use `aria-hidden="true"`:

```django
<h2>
  {% icon "user" size="sm" aria_hidden="true" %}
  User Profile
</h2>
```

### Focus Indicators

Ensure icon buttons have visible focus indicators:

```css
.btn:focus {
  outline: 2px solid var(--primary);
  outline-offset: 2px;
}
```

## Available Icons

Common icons available in the system (see `hi/apps/common/templatetags/icons.py` for complete list):

### Actions
- `plus` - Add/Create
- `edit` / `pencil` - Edit/Modify
- `delete` / `trash` - Delete/Remove
- `save` / `check` - Save/Confirm
- `cancel` / `times` - Cancel/Close
- `copy` - Duplicate
- `download` - Export/Download
- `upload` - Import/Upload

### Navigation
- `home` - Home page
- `arrow-left` / `arrow-right` - Back/Forward
- `chevron-left` / `chevron-right` - Previous/Next
- `arrow-up` / `arrow-down` - Up/Down
- `external-link` - External links

### Status/Feedback
- `check-circle` - Success
- `exclamation-triangle` - Warning
- `times-circle` - Error
- `info-circle` - Information
- `question-circle` - Help

### Media
- `play` - Play action
- `pause` - Pause action
- `video` - Video content
- `camera` - Camera/Photo

### UI Elements
- `search` - Search functionality
- `filter` - Filter/Sort
- `settings` / `cog` - Configuration
- `user` - User/Profile
- `list` - List view
- `grid` - Grid view

## Related Documentation
- Frontend guidelines: [Frontend Guidelines](frontend-guidelines.md)
- Style guidelines: [Style Guidelines](style-guidelines.md)
- Template conventions: [Template Conventions](template-conventions.md)
