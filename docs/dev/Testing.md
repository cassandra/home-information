<img src="../../src/hi/static/img/hi-logo-w-tagline-197x96.png" alt="Home Information Logo" width="128">

# Testing

## Unit Tests

``` shell
cd $PROJ_DIR/src
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

### Additional Testing Anti-Patterns (Avoid These)

**Mock-Centric Testing Instead of Behavior Testing**

**Problem**: Tests focus on verifying mock calls rather than testing actual behavior and return values.

**Bad Example**:
```python
# BAD - Testing mock calls instead of behavior
@patch('module.external_service')
def test_process_data(self, mock_service):
    mock_service.return_value = {'status': 'success'}
    
    result = processor.process_data(input_data)
    
    # Only testing that the mock was called correctly
    mock_service.assert_called_once_with(expected_params)
    # Missing: What did process_data actually return?
```

**Good Example**:
```python
# GOOD - Testing actual behavior and return values
@patch('module.external_service')
def test_process_data_returns_transformed_result(self, mock_service):
    mock_service.return_value = {'status': 'success', 'data': 'raw_value'}
    
    result = processor.process_data(input_data)
    
    # Test the actual behavior and return value
    self.assertEqual(result['transformed_data'], 'processed_raw_value')
    self.assertEqual(result['status'], 'completed')
    self.assertIn('timestamp', result)
```

**Over-Mocking Internal Components**

**Problem**: Mocking too many internal components breaks the integration between parts of the system.

**Bad Example**:
```python
# BAD - Mocking both HTTP layer AND internal converter
@patch('module.http_client.get')
@patch('module.DataConverter.parse')
def test_fetch_and_parse(self, mock_parse, mock_get):
    mock_get.return_value = mock_response
    mock_parse.return_value = mock_parsed_data
    
    result = service.fetch_and_parse()
    # This tests nothing about actual data flow
```

**Good Example**:
```python
# GOOD - Mock only at system boundaries
@patch('module.http_client.get')
def test_fetch_and_parse_integration(self, mock_get):
    mock_get.return_value = Mock(text='{"real": "json", "data": "here"}')
    
    result = service.fetch_and_parse()
    
    # Test that real data flows through real converter
    self.assertIsInstance(result, ExpectedDataType)
    self.assertEqual(result.parsed_field, "expected_value")
```

**Testing Implementation Details Instead of Interface Contracts**

**Problem**: Tests verify internal implementation details rather than public interface behavior.

**Bad Example**:
```python
# BAD - Testing exact HTTP parameters instead of behavior
def test_api_call_constructs_correct_url(self):
    client.make_request('entity_123')
    
    expected_url = 'https://api.service.com/v1/entities/entity_123'
    expected_headers = {'Authorization': 'Bearer token', 'Content-Type': 'application/json'}
    mock_post.assert_called_once_with(expected_url, headers=expected_headers)
    # Missing: What happens with the response?
```

**Good Example**:
```python
# GOOD - Testing the interface contract
def test_api_call_returns_entity_data(self):
    mock_response_data = {'id': 'entity_123', 'name': 'Test Entity'}
    mock_post.return_value = Mock(json=lambda: mock_response_data)
    
    result = client.make_request('entity_123')
    
    # Test the contract: what the method promises to return
    self.assertEqual(result['id'], 'entity_123')
    self.assertEqual(result['name'], 'Test Entity')
```

**Superficial Edge Case Testing**

**Problem**: Creating edge case tests that don't test meaningful business logic scenarios.

**Bad Example**:
```python
# BAD - Testing trivial edge cases without business impact
def test_handles_various_url_formats(self):
    test_cases = [
        ('http://localhost', 'http://localhost'),
        ('http://localhost/', 'http://localhost'),
        ('https://example.com/', 'https://example.com')
    ]
    for input_url, expected in test_cases:
        client = ApiClient(input_url)
        self.assertEqual(client.base_url, expected)
```

**Good Example**:
```python
# GOOD - Testing edge cases that affect actual functionality
def test_url_normalization_prevents_api_call_failures(self):
    client_with_slash = ApiClient('https://api.example.com/')
    client_without_slash = ApiClient('https://api.example.com')
    
    # Test that both work correctly for actual API calls
    with patch('requests.get') as mock_get:
        mock_get.return_value = Mock(json=lambda: {'data': 'test'})
        
        result1 = client_with_slash.fetch_data()
        result2 = client_without_slash.fetch_data()
        
        # Both should work and return same data
        self.assertEqual(result1, result2)
        # Verify no double slashes in URL
        for call in mock_get.call_args_list:
            url = call[0][0]
            self.assertNotIn('//api', url)
```

**Complex Multi-Purpose Tests**

**Problem**: Single tests that verify too many different behaviors, making failures hard to diagnose.

**Bad Example**:
```python
# BAD - Testing multiple services and scenarios in one test
def test_service_various_operations(self):
    test_cases = [
        ('light', 'turn_on', 'light.bedroom'),
        ('switch', 'turn_off', 'switch.outlet'),
        ('climate', 'set_temperature', 'climate.thermostat'),
        ('media_player', 'play_media', 'media_player.living_room'),
    ]
    for domain, service, entity in test_cases:
        with self.subTest(domain=domain):
            result = client.call_service(domain, service, entity)
            # Generic assertions that don't test domain-specific logic
            self.assertIsNotNone(result)
```

**Good Example**:
```python
# GOOD - Focused tests for specific behaviors
def test_light_service_calls_return_response_objects(self):
    mock_response = Mock(status_code=200, json=lambda: {'context': 'light_context'})
    
    result = client.call_service('light', 'turn_on', 'light.bedroom')
    
    self.assertEqual(result.status_code, 200)
    self.assertIn('context', result.json())

def test_climate_service_handles_temperature_data(self):
    service_data = {'temperature': 72, 'hvac_mode': 'heat'}
    
    result = client.call_service('climate', 'set_temperature', 'climate.thermostat', service_data)
    
    # Test climate-specific behavior
    call_data = mock_post.call_args[1]['json']
    self.assertEqual(call_data['temperature'], 72)
    self.assertEqual(call_data['hvac_mode'], 'heat')
```

**Inadequate Error Context Testing**

**Problem**: Testing that errors occur without verifying error messages provide useful debugging information.

**Bad Example**:
```python
# BAD - Only testing that an error occurs
def test_invalid_entity_raises_error(self):
    with self.assertRaises(ValueError):
        client.set_state('invalid.entity', 'on')
```

**Good Example**:
```python
# GOOD - Testing error context and messages
def test_invalid_entity_provides_descriptive_error(self):
    mock_response = Mock(status_code=404, text='Entity invalid.entity not found')
    
    with self.assertRaises(ValueError) as context:
        client.set_state('invalid.entity', 'on')
    
    error_message = str(context.exception)
    self.assertIn('invalid.entity', error_message)
    self.assertIn('404', error_message)
    self.assertIn('not found', error_message)
    # Verify error provides actionable information
```

### Testing Best Practices Summary

1. **Mock at system boundaries only** (HTTP calls, database, external services)
2. **Test return values and state changes**, not mock call parameters
3. **Use real data through real code paths** when possible
4. **Test error messages provide useful context** for debugging
5. **Focus on interface contracts**, not implementation details
6. **Create focused tests** that test one behavior well
7. **Test meaningful edge cases** that affect business logic
8. **Verify data transformations** work correctly end-to-end

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

