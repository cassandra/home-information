<img src="../../src/hi/static/img/hi-logo-w-tagline-197x96.png" alt="Home Information Logo" width="128">

# Testing

## Unit Tests

``` shell
./manage.py test
```

## Testing Guidelines and Best Practices

### High-Value vs Low-Value Testing Criteria

**HIGH-VALUE Tests (Focus Here)**
- **Database constraints and cascade deletion behavior** - Critical for data integrity
- **Complex business logic and algorithms** - Custom calculations, aggregation, processing
- **Singleton pattern behavior** - Manager classes, initialization, thread safety
- **Enum property conversions with custom logic** - from_name_safe(), business rules
- **File handling and storage operations** - Upload, deletion, cleanup, error handling
- **Integration key parsing and external system interfaces** - API boundaries
- **Complex calculations** - Geometric (SVG positioning), ordering, aggregation logic
- **Caching and performance optimizations** - TTL caches, database indexing
- **Auto-discovery and Django startup integration** - Module loading, initialization sequences
- **Thread safety and concurrent operations** - Locks, shared state, race conditions
- **Background process coordination** - Async/sync dual access, event loop management

**LOW-VALUE Tests (Avoid These)**
- Simple property getters/setters that just return field values
- Django ORM internals verification (Django already tests this)
- Trivial enum label checking without business logic
- Basic field access and obvious default values
- Simple string formatting without complex logic

### Critical Testing Anti-Patterns (Never Do These)

**NEVER Test Behavior Based on Log Messages**
- **Problem**: Log message assertions (`self.assertLogs()`, checking log output) are fragile and break easily when logging changes
- **Issue**: Many existing tests deliberately disable logging for performance and clarity
- **Solution**: Test actual behavior changes - state modifications, return values, method calls, side effects
- **Example**: Instead of `assertLogs('module', level='WARNING')`, verify the actual error handling behavior occurred

```python
# BAD - Testing based on log messages
with self.assertLogs('weather.manager', level='WARNING') as log_context:
    manager.process_data(invalid_data)
    self.assertTrue(any("Error processing" in msg for msg in log_context.output))

# GOOD - Testing actual behavior
mock_fallback = Mock()
with patch.object(manager, 'fallback_handler', mock_fallback):
    result = manager.process_data(invalid_data)
    mock_fallback.assert_called_once()
    self.assertIsNone(result)  # Verify expected failure behavior
```

### Django-Specific Testing Patterns

```python
# Abstract Model Testing - Create concrete test class
class ConcreteTestModel(AbstractModel):
    def required_abstract_method(self):
        return "test_implementation"

# Mock Django operations for database-less testing
with patch('django.db.models.Model.save') as mock_save:
    instance.save()
    mock_save.assert_called_once()

# Integration Key Pattern Testing
def test_integration_key_inheritance(self):
    model = TestModel.objects.create(
        integration_id='test_id',
        integration_name='test_integration'
    )
    self.assertEqual(model.integration_id, 'test_id')

# Singleton Manager Testing
def test_manager_singleton_behavior(self):
    manager1 = ManagerClass()
    manager2 = ManagerClass()
    self.assertIs(manager1, manager2)

# Background Process and Threading Testing
async def test_async_manager_method(self):
    with patch('asyncio.run') as mock_run:
        result = await manager.async_method()
        mock_run.assert_called()

def test_manager_thread_safety(self):
    results = []
    def worker():
        results.append(manager.thread_safe_operation())
    
    threads = [threading.Thread(target=worker) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
```

## Integration Tests

_TBD_

## Visual Testing Page

Visit: [http://127.0.0.1:8411/tests/ui](http://127.0.0.1:8411/tests/ui).

These tests/ui views are only available in the development environment when `DEBUG=True`. (They are conditionally loaded in the root `urls.py`.)

### Adding to the Visual Testing Page

The `hi.tests.ui` module uses auto-discovery by looking in the app directories.

In the app directory you want to have a visual testing page:

``` shell
mkdir -p tests/ui
touch tests.__init__.py
touch tests/ui.__init__.py
```

Then:
- Create `tests/ui/views.py`
- Create `tests/ui/urls.py` (This gets auto-discovered. Esnure some default home page rule.)

The templates for these tests, by convention, would be put in the app templates directory as `templates/${APPNAME}/tests/ui`. At a minimum, you will probably want a home page `templates/${APPNAME}/tests/ui/home.html` like this:

``` html
{% extends "pages/base.html" %}
{% block head_title %}HI: PAGE TITLE{% endblock %}

{% block content %}
<div class="container-fluid m-4">

  <h2 class="text-info">SOME TESTS</h2>

  <!-- Put links to views here -->

</div>
{% endblock %}
```

And in `tests/ui/views.py`:

``` python
class Test${APPNAMNE}HomeView( View ):

    def get(self, request, *args, **kwargs):
        context = {
        }
        return render(request, "${APPNAME}/tests/ui/home.html", context )
```

And in `tests/ui/urls.py`:

``` python
from django.urls import re_path

from . import views


urlpatterns = [

    re_path( r'^$',
             views.TestUi${APPNAME}HomeView.as_view(), 
             name='${APPNAME}_tests_ui'),
]
```

### Email Testing

There are some helper base classes to test viewing email formatting and sending emails.
``` shell
hi.tests.ui.email_test_views.py
```
This requires the email templates follow the naming patterns expected in view classes.

