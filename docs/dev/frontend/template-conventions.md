# Template Conventions

## Checklist

- [ ] Template names referenced in views closely match the view names that use them.
- [ ] No templates have in-line Javascript.
- [ ] No templates have in-line CSS.
- [ ] Templates appear in a subdirectory matching their purpose: modals, panes, pages.
- [ ] Template tags `load` statments near the top of the file.

## The "Hi Grid" Template Structure

### Important DIVIDs for Main Page Layout

We gathered strings that need to be shared between client and server in `src/hi/constants.py:DIVID`. The important ones that define the top-level page layout of `src/hi/templates/pages/hi_grid.html` are:

- `#hi-main-content` - Main display area, excluding header buttons, footer buttons and side panel
- `#hi-side-content` - Side panel content area
- `#hi-top-buttons` - Top button toolbar area
- `#hi-bottom-buttons` - Bottom button toolbar area
- `#hi-config-integration-tab` - Integrations use this for configuration-related views

## Template Directory Structure

### App Module Templates
Each Django app follows this template organization:

```
hi/apps/${APPNAME}/templates/${APPNAME}/
├── pages/          # Full HTML pages
├── modals/         # Modal dialogs
├── panes/          # Page fragments
├── email/          # Email templates
├── svg/            # SVG files
├── testing/        # Test templates
│   └── ui/        # Visual testing templates
└── edit/           # Edit mode templates
    ├── pages/
    ├── modals/
    └── panes/
```

## Template Inheritance

### Base Templates

All pages should extend from appropriate base templates:

```django
<!-- For main application pages -->
{% extends "pages/base.html" %}

<!-- For modal dialogs -->
{% extends "modals/base_modal.html" %}

<!-- For configuration pages -->
{% extends "config/pages/config_base.html" %}
```

### Avoiding Template Logic

**Bad - Logic in template:**
```django
{% if entity.sensors.count > 0 and entity.is_active and not entity.deleted %}
  {% for sensor in entity.sensors.all %}
    {% if sensor.last_reading and sensor.last_reading.timestamp|timesince < "1 hour" %}
      <!-- Display sensor -->
    {% endif %}
  {% endfor %}
{% endif %}
```

**Good - Logic in view:**
```python
# In view
context = {
    'active_sensors': entity.get_recent_active_sensors(),
    'has_active_sensors': bool(active_sensors),
}
```

```django
<!-- In template -->
{% if has_active_sensors %}
  {% for sensor in active_sensors %}
    <!-- Display sensor -->
  {% endfor %}
{% endif %}
```

## Template Tags and Filters

### Loading Template Tags

Always load required template tags at the top:

```django
{% load static %}
{% load icons %}
{% load custom_filters %}
```

## Modal Templates

Extend one of the standard modal templates: `src/hi/templates/modals`.

## Related Documentation
- Frontend guidelines: [Frontend Guidelines](frontend-guidelines.md)
- Icon system: [Icon System](icon-system.md)
- Style guidelines: [Style Guidelines](style-guidelines.md)
- Testing: [UI Testing](ui-testing.md)
