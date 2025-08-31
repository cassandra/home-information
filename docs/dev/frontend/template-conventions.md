# Template Conventions

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

### Block Structure

Common blocks to override:

```django
{% block head_title %}Page Title{% endblock %}
{% block extra_css %}
  <!-- Page-specific CSS -->
{% endblock %}
{% block content %}
  <!-- Main content area -->
{% endblock %}
{% block extra_js %}
  <!-- Page-specific JavaScript -->
{% endblock %}
```

## Template Context Patterns

### Standard Context Variables

Views should provide consistent context variables:

```python
context = {
    # Entity-related
    'entity': entity_instance,
    'entities': entity_queryset,
    'entity_position': position_instance,
    
    # Location-related
    'location': location_instance,
    'location_view': location_view_instance,
    
    # View state
    'view_mode': ViewMode.NORMAL,  # Use enums, not strings
    'view_type': ViewType.SECURITY,
    'is_edit_mode': False,
    
    # Pre-computed flags
    'has_sensors': bool(entity.sensors.exists()),
    'can_edit': request.user.has_perm('entity.change_entity'),
}
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

### Custom Template Tags

Create reusable template tags for complex display logic:

```python
# In templatetags/entity_tags.py
@register.inclusion_tag('entity/tags/status_badge.html')
def entity_status_badge(entity):
    return {
        'entity': entity,
        'status_class': entity.get_status_css_class(),
        'status_label': entity.get_status_display(),
    }
```

Usage:
```django
{% load entity_tags %}
{% entity_status_badge entity %}
```

## Form Templates

### Form Rendering Pattern

Use consistent form rendering:

```django
<form method="post" action="{% url 'entity_update' entity.id %}">
  {% csrf_token %}
  
  {% if form.non_field_errors %}
    <div class="alert alert-danger">
      {{ form.non_field_errors }}
    </div>
  {% endif %}
  
  {% for field in form %}
    <div class="form-group">
      {{ field.label_tag }}
      {{ field }}
      {% if field.help_text %}
        <small class="form-text text-muted">{{ field.help_text }}</small>
      {% endif %}
      {% if field.errors %}
        <div class="invalid-feedback d-block">
          {{ field.errors }}
        </div>
      {% endif %}
    </div>
  {% endfor %}
  
  <button type="submit" class="btn btn-primary">
    {% icon "save" size="sm" css_class="hi-icon-left" %}
    Save Changes
  </button>
</form>
```

## AJAX Template Patterns

### Returning HTML Fragments

For AJAX requests returning HTML:

```django
<!-- panes/entity_row.html -->
<tr class="entity-row" data-entity-id="{{ entity.id }}">
  <td>{{ entity.name }}</td>
  <td>{{ entity.location.name }}</td>
  <td>{% entity_status_badge entity %}</td>
</tr>
```

### JSON Response Structure

For AJAX views returning JSON with HTML:

```python
# In view
html = render_to_string('entity/panes/entity_row.html', {'entity': entity})
return JsonResponse({
    'status': 'success',
    'html': html,
    'entity_id': entity.id,
    'insert_method': 'append',
    'target_selector': '#entity-table tbody',
})
```

## Modal Templates

### Modal Structure

Standard modal template structure:

```django
<!-- modals/entity_edit.html -->
<div class="modal fade" id="entityEditModal" tabindex="-1" role="dialog">
  <div class="modal-dialog modal-lg" role="document">
    <div class="modal-content">
      <div class="modal-header">
        <h5 class="modal-title">Edit Entity</h5>
        <button type="button" class="close" data-dismiss="modal" aria-label="Close">
          {% icon "close" size="sm" %}
        </button>
      </div>
      <div class="modal-body">
        <!-- Modal content -->
      </div>
      <div class="modal-footer">
        <button type="button" class="btn btn-secondary" data-dismiss="modal">
          {% icon "cancel" size="sm" css_class="hi-icon-left" %}
          Cancel
        </button>
        <button type="submit" class="btn btn-primary">
          {% icon "save" size="sm" css_class="hi-icon-left" %}
          Save Changes
        </button>
      </div>
    </div>
  </div>
</div>
```

## Template Performance

### Efficient Queries

Use `select_related` and `prefetch_related` in views:

```python
# In view - prevent N+1 queries
entities = Entity.objects.select_related(
    'location', 
    'entity_type'
).prefetch_related(
    'sensors',
    'controllers'
)
```

### Template Fragment Caching

Cache expensive template fragments:

```django
{% load cache %}
{% cache 300 entity_detail entity.id entity.updated_at %}
  <!-- Expensive template rendering -->
  {% include "entity/panes/sensor_list.html" %}
{% endcache %}
```

## Debugging Templates

### Debug Toolbar

Use Django Debug Toolbar to identify template issues:
- Template rendering time
- Number of SQL queries
- Context variables

### Template Debug Mode

In development, use template debug mode:

```django
{% if debug %}
  <div class="debug-info">
    <pre>{{ entity|pprint }}</pre>
  </div>
{% endif %}
```

## Related Documentation
- Frontend guidelines: [Frontend Guidelines](frontend-guidelines.md)
- Icon system: [Icon System](icon-system.md)
- Style guidelines: [Style Guidelines](style-guidelines.md)
- Testing: [UI Testing](ui-testing.md)
