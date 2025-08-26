# UI Testing

## Visual Testing Page

Visit: [http://127.0.0.1:8411/testing/ui](http://127.0.0.1:8411/testing/ui)

These test/ui views are only available in development when `DEBUG=True`. They are conditionally loaded in the root `urls.py`.

## UI Testing Framework Guidelines

The visual testing framework is designed for viewing UI styling and layout during development. These are **read-only** views that should never modify system state.

### Critical Principle: System State Isolation

**NEVER modify real system state in UI test views:**
- Do not add data to real managers (AlertManager, WeatherManager, etc.)
- Do not modify database records
- Do not modify in-memory caches or singletons
- Do not persist test data that appears in production views

### Correct Approach: Render Templates Directly

```python
class TestUiAlertDetailsView(View):
    def get(self, request, *args, **kwargs):
        # Create synthetic data
        alert = AlertSyntheticData.create_single_alarm_alert(
            alarm_level=AlarmLevel.WARNING,
            has_image=True
        )
        
        # Prepare context data using domain object methods
        visual_content = alert.get_first_visual_content()
        
        # Render template directly with synthetic data
        context = {
            'alert': alert,
            'alert_visual_content': visual_content,
        }
        return render(request, 'alert/modals/alert_details.html', context)
```

### Architecture Patterns

**Render Templates Directly (Preferred):**
- For testing UI styling and layout
- When you need specific synthetic data scenarios
- When testing requires system state isolation
- Follows pattern used by weather, notify modules

**Code Duplication Prevention:**
- Move shared logic to domain object methods (e.g., `Alert.get_first_visual_content()`)
- Use centralized synthetic data classes
- Create utility functions for common data preparation patterns

## Setting Up Visual Testing

### Auto-Discovery Structure

The `hi.tests.ui` module uses auto-discovery by looking in app directories.

In the app directory you want to have a visual testing page:

```bash
mkdir -p tests/ui
touch tests/__init__.py
touch tests/ui/__init__.py
```

### Required Files

Create these files:
- `tests/ui/views.py`
- `tests/ui/urls.py` (gets auto-discovered)

### Template Structure

Templates go in `templates/${APPNAME}/testing/ui/`. Create a home page:

```html
<!-- templates/${APPNAME}/testing/ui/home.html -->
{% extends "pages/base.html" %}
{% load icons %}

{% block head_title %}HI: {{ app_name|title }} UI Tests{% endblock %}

{% block content %}
<div class="container-fluid m-4">
  <h2 class="text-info">{{ app_name|title }} UI Tests</h2>
  
  <div class="row">
    <div class="col-md-6">
      <h3>Component Tests</h3>
      <ul class="list-group">
        <li class="list-group-item">
          <a href="{% url 'test_entity_card' %}">Entity Cards</a>
        </li>
        <li class="list-group-item">
          <a href="{% url 'test_status_badges' %}">Status Badges</a>
        </li>
      </ul>
    </div>
    
    <div class="col-md-6">
      <h3>Modal Tests</h3>
      <ul class="list-group">
        <li class="list-group-item">
          <a href="{% url 'test_edit_modal' %}" data-toggle="modal" data-target="#editModal">
            Edit Entity Modal
          </a>
        </li>
      </ul>
    </div>
  </div>
</div>
{% endblock %}
```

### View Implementation

```python
# tests/ui/views.py
from django.shortcuts import render
from django.views import View
from hi.apps.entity.models import Entity

class TestUiEntityHomeView(View):
    def get(self, request, *args, **kwargs):
        context = {
            'app_name': 'entity',
        }
        return render(request, 'entity/testing/ui/home.html', context)

class TestUiEntityCardView(View):
    def get(self, request, *args, **kwargs):
        # Create synthetic test data
        entities = [
            self.create_synthetic_entity('Living Room Light', 'active'),
            self.create_synthetic_entity('Kitchen Sensor', 'recent'),
            self.create_synthetic_entity('Garage Door', 'idle'),
            self.create_synthetic_entity('Weather Station', 'unknown'),
        ]
        
        context = {
            'entities': entities,
            'page_title': 'Entity Card Variations',
        }
        return render(request, 'entity/testing/ui/card_variations.html', context)
    
    def create_synthetic_entity(self, name, status):
        """Create synthetic entity for testing - does not save to database"""
        entity = Entity(
            name=name,
            integration_id=f'test.{name.lower().replace(" ", "_")}',
            integration_name='test_integration'
        )
        # Add synthetic status for display
        entity._test_status = status
        return entity
```

### URL Configuration

```python
# tests/ui/urls.py
from django.urls import re_path
from . import views

urlpatterns = [
    re_path(r'^$',
            views.TestUiEntityHomeView.as_view(),
            name='entity_tests_ui'),
    
    re_path(r'^cards/$',
            views.TestUiEntityCardView.as_view(),
            name='test_entity_cards'),
]
```

## Component Testing Patterns

### Testing Responsive Design

Create viewport testing utilities:

```html
<!-- Responsive testing template -->
<div class="responsive-test">
  <h3>Viewport Testing</h3>
  <div class="viewport-buttons">
    <button class="btn btn-sm btn-outline-secondary" data-viewport="320x568">iPhone SE</button>
    <button class="btn btn-sm btn-outline-secondary" data-viewport="768x1024">iPad</button>
    <button class="btn btn-sm btn-outline-secondary" data-viewport="1200x800">Desktop</button>
  </div>
  
  <div class="test-component">
    <!-- Component under test -->
    {% include "entity/panes/entity_card.html" %}
  </div>
</div>

<script>
document.querySelectorAll('[data-viewport]').forEach(button => {
    button.addEventListener('click', function() {
        const [width, height] = this.dataset.viewport.split('x');
        // Simulate viewport for testing
        document.querySelector('.test-component').style.maxWidth = width + 'px';
    });
});
</script>
```

### Testing State Variations

Create comprehensive state testing:

```python
class TestUiStatusStatesView(View):
    def get(self, request, *args, **kwargs):
        # Test all possible status states
        status_variations = [
            ('active', 'Red - Currently active'),
            ('recent', 'Orange - Recently active'),
            ('past', 'Yellow - Past activity'),
            ('idle', 'Green - Idle state'),
            ('unknown', 'Gray - Unknown/offline'),
        ]
        
        entities = []
        for status, description in status_variations:
            entity = self.create_entity_with_status(status)
            entity._description = description
            entities.append(entity)
        
        context = {
            'entities': entities,
            'page_title': 'Status State Variations',
        }
        return render(request, 'entity/testing/ui/status_states.html', context)
```

### Testing Icon Usage

```html
<!-- Icon testing template -->
<div class="icon-test-grid">
  <h3>Icon Usage Tests</h3>
  
  <div class="row">
    <div class="col-md-4">
      <h4>Actions</h4>
      <div class="btn-group-vertical w-100">
        <button class="btn btn-primary">
          {% icon "plus" size="sm" css_class="hi-icon-left" %}
          Add New
        </button>
        <button class="btn btn-secondary">
          {% icon "edit" size="sm" css_class="hi-icon-left" %}
          Edit
        </button>
        <button class="btn btn-danger">
          {% icon "delete" size="sm" css_class="hi-icon-left" %}
          Delete
        </button>
      </div>
    </div>
    
    <div class="col-md-4">
      <h4>Icon Sizes</h4>
      {% for size in "xs,sm,md,lg,xl"|split:"," %}
        <div class="mb-2">
          {% icon "home" size=size %} {{ size }} ({{ size }})
        </div>
      {% endfor %}
    </div>
    
    <div class="col-md-4">
      <h4>Status Icons</h4>
      <div class="alert alert-success">
        {% icon "check-circle" size="sm" css_class="hi-icon-left" %}
        Success message
      </div>
      <div class="alert alert-warning">
        {% icon "exclamation-triangle" size="sm" css_class="hi-icon-left" %}
        Warning message
      </div>
    </div>
  </div>
</div>
```

## Modal Testing

### Modal Component Testing

```python
class TestUiModalView(View):
    def get(self, request, *args, **kwargs):
        # Test modal with different content types
        modal_variations = [
            {
                'size': 'sm',
                'title': 'Small Modal',
                'content': 'Simple confirmation modal',
                'actions': ['Cancel', 'Confirm']
            },
            {
                'size': 'lg',
                'title': 'Large Modal',
                'content': 'Complex form modal with multiple fields',
                'actions': ['Cancel', 'Save', 'Save & Continue']
            }
        ]
        
        context = {
            'modal_variations': modal_variations,
        }
        return render(request, 'entity/testing/ui/modal_tests.html', context)
```

## Form Testing

### Form State Testing

```html
<!-- Form testing template -->
<div class="form-test-variations">
  <h3>Form State Testing</h3>
  
  <div class="row">
    <div class="col-md-6">
      <h4>Normal State</h4>
      <form>
        <div class="form-group">
          <label for="normal-input">Entity Name</label>
          <input type="text" class="form-control" id="normal-input" value="Living Room Light">
        </div>
        <button type="submit" class="btn btn-primary">Save</button>
      </form>
    </div>
    
    <div class="col-md-6">
      <h4>Error State</h4>
      <form>
        <div class="form-group">
          <label for="error-input">Entity Name</label>
          <input type="text" class="form-control is-invalid" id="error-input" value="">
          <div class="invalid-feedback">
            This field is required.
          </div>
        </div>
        <button type="submit" class="btn btn-primary">Save</button>
      </form>
    </div>
  </div>
</div>
```

## Email Template Testing

Use helper base classes for email testing:

```python
# From hi.tests.ui.email_test_views.py
class EmailTestView(View):
    def test_alert_notification_email(self):
        # Test email templates with synthetic data
        context = {
            'alert': self.create_synthetic_alert(),
            'user': self.create_synthetic_user(),
        }
        return self.render_email_template('alert/email/notification.html', context)
```

## Performance Testing

### Template Rendering Performance

```python
import time
from django.test.utils import override_settings

class TestUiPerformanceView(View):
    def get(self, request, *args, **kwargs):
        # Test template rendering with large datasets
        start_time = time.time()
        
        # Create large synthetic dataset
        entities = [self.create_synthetic_entity(f'Entity {i}') for i in range(100)]
        
        render_time = time.time() - start_time
        
        context = {
            'entities': entities,
            'render_time': render_time,
        }
        return render(request, 'entity/testing/ui/performance_test.html', context)
```

## Related Documentation
- Frontend guidelines: [Frontend Guidelines](frontend-guidelines.md)
- Template conventions: [Template Conventions](template-conventions.md)
- Testing patterns: [Testing Patterns](../testing/testing-patterns.md)
- Test data management: [Test Data Management](../testing/test-data-management.md)