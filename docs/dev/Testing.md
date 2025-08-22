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
9. **Use real database operations over ORM mocking** when testing business logic
10. **Test database state changes** rather than mocking ORM calls to verify actual behavior

#### Database vs Mock Testing Strategy

**Prefer Real Database Operations:**
- Database state verification tests actual business logic and relationships
- Cascade deletion, constraints, and indexing are critical system behaviors
- TransactionTestCase provides proper isolation for database-dependent tests
- Real data flows through real code paths reveal integration issues

**When to Mock vs Real Database:**
- **Mock external APIs** (HTTP calls, third-party services)
- **Use real database** for business logic, relationships, and data transformations
- **Mock at system boundaries**, not internal ORM operations

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

### Manager Class Async/Sync Testing

Many manager classes in this codebase follow a dual sync/async pattern to support both traditional Django views and async integration services. These require special testing infrastructure.

#### Manager Pattern Characteristics
- Singleton pattern with `__init_singleton__()` 
- Both sync `ensure_initialized()` and async initialization methods
- Mix of sync methods for Django ORM access and async methods for integration services
- Thread safety considerations and shared state management

#### Async Testing Infrastructure
Use this pattern for testing manager classes with async methods:

```python
class AsyncManagerTestCase(TransactionTestCase):
    """Base class for async manager tests with proper infrastructure."""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Create a single shared event loop for all tests in this class
        cls._test_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(cls._test_loop)
    
    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, '_test_loop'):
            cls._test_loop.close()
        super().tearDownClass()
    
    def run_async(self, coro):
        """Helper method to run async coroutines using the shared event loop."""
        return self._test_loop.run_until_complete(coro)
    
    def setUp(self):
        super().setUp()
        # Reset singleton state for each test
        ManagerClass._instances = {}
        self.manager = ManagerClass()
        # Clear any cached state
        if hasattr(self.manager, '_recent_transitions'):
            self.manager._recent_transitions.clear()

    def test_async_method(self):
        """Example async test using wrapper pattern."""
        async def async_test_logic():
            # Use sync_to_async for database operations
            entity = await sync_to_async(Entity.objects.create)(name='Test Entity')
            result = await self.manager.async_method(entity)
            self.assertIsNotNone(result)
        
        self.run_async(async_test_logic())
```

**Key Requirements:**
- **Use `TransactionTestCase`** instead of `BaseTestCase` to avoid database locking
- **Shared event loop** prevents SQLite concurrency issues with multiple async tests
- **Reset singleton state** between tests to ensure isolation
- **Wrap sync database operations** with `sync_to_async()` in async test code
- **Use `select_related()`** in manager code to prevent lazy loading in async contexts

**Critical ORM Access Pattern:**
```python
# In manager async methods - avoid lazy loading issues
event_clauses = await sync_to_async(list)(
    event_definition.event_clauses.select_related('entity_state').all()
)

# In tests - wrap database operations
entity = await sync_to_async(Entity.objects.create)(name='Test')
```

## Django View Testing

Django views in this application come in five distinct patterns that require different testing approaches:

1. **Synchronous HTML Views** - Traditional Django page views returning HTML responses
2. **Synchronous JSON Views** - API endpoints returning JSON responses 
3. **Asynchronous HTML Views** - AJAX views returning HTML snippets for DOM insertion
4. **Asynchronous JSON Views** - AJAX views returning JSON data for JavaScript processing
5. **Dual-Mode Views** - Views (HiModalView/HiGridView) that handle both sync and async requests

### View Testing Base Classes

The framework uses a mixin-based architecture to provide clean separation of concerns:

- `ViewTestBase` - Common utilities and core assertions
- `SyncTestMixin` - Synchronous testing capabilities (regular `client.get()`, `client.post()`)  
- `AsyncTestMixin` - Asynchronous testing capabilities (`async_get()`, `async_post()` with AJAX headers)

These are composed into test case classes:

Use these base classes from `hi.tests.view_test_base` for consistent view testing:

```python
from django.urls import reverse
from hi.tests.view_test_base import SyncViewTestCase, AsyncViewTestCase, DualModeViewTestCase

class TestMySyncViews(SyncViewTestCase):
    def test_synchronous_html_view(self):
        url = reverse('my_view_name')
        response = self.client.get(url)  # Regular Django test client
        self.assertSuccessResponse(response)
        self.assertHtmlResponse(response)
        self.assertTemplateRendered(response, 'my_app/template.html')
        
class TestMyAsyncViews(AsyncViewTestCase):
    def test_asynchronous_html_view(self):
        url = reverse('my_async_view_name')
        response = self.async_get(url)  # Automatically includes AJAX headers
        self.assertSuccessResponse(response)
        self.assertJsonResponse(response)

class TestMyDualModeViews(DualModeViewTestCase):
    def test_view_synchronous_mode(self):
        url = reverse('my_dual_view_name')
        response = self.client.get(url)  # Regular request
        self.assertSuccessResponse(response)
        self.assertHtmlResponse(response)
        
    def test_view_asynchronous_mode(self):
        url = reverse('my_dual_view_name') 
        response = self.async_get(url)  # AJAX request
        self.assertSuccessResponse(response)
        self.assertJsonResponse(response)
```

### Helper Methods

The base test classes provide these assertion and utility methods:

**Status Code Assertions:**
- `assertResponseStatusCode(response, expected_code)` - Verifies specific status code
- `assertSuccessResponse(response)` - Verifies 2xx status code
- `assertErrorResponse(response)` - Verifies 4xx status code
- `assertServerErrorResponse(response)` - Verifies 5xx status code

**Response Type Assertions:**
- `assertHtmlResponse(response)` - Verifies HTML content type (status code independent)
- `assertJsonResponse(response)` - Verifies JSON content type (status code independent)

**Template Assertions:**
- `assertTemplateRendered(response, template_name)` - Verifies specific template was used

**Session Assertions:**
- `assertSessionValue(response, key, expected_value)` - Verifies session contains specific key-value pair
- `assertSessionContains(response, key)` - Verifies session contains specific key

**Session Management:**
- `setSessionViewType(view_type)` - Set ViewType in session for subsequent requests
- `setSessionViewMode(view_mode)` - Set ViewMode in session for subsequent requests  
- `setSessionLocationView(location_view)` - Set location_view_id in session for subsequent requests
- `setSessionCollection(collection)` - Set collection_id in session for subsequent requests
- `setSessionViewParameters(view_type=None, view_mode=None, location_view=None, collection=None)` - Set multiple view parameters at once

**Redirect Testing:**
- `assertRedirectsToTemplates(initial_url, expected_templates)` - Follow redirects and verify final templates rendered

**AJAX Request Methods:**
- `async_get(url, data=None)` - GET request with AJAX headers
- `async_post(url, data=None)` - POST request with AJAX headers  
- `async_put(url, data=None)` - PUT request with AJAX headers
- `async_delete(url, data=None)` - DELETE request with AJAX headers

### Testing Patterns by View Type

#### Synchronous HTML Views
- Test status code, response type, and template rendering separately
- Verify error handling and edge cases
- Validate form processing and context data

```python
def test_location_view_renders_correctly(self):
    location = Location.objects.create(name='Test Location')
    url = reverse('location_detail', kwargs={'location_id': location.id})
    response = self.client.get(url)
    
    self.assertSuccessResponse(response)
    self.assertHtmlResponse(response)
    self.assertTemplateRendered(response, 'location/detail.html')
    self.assertEqual(response.context['location'], location)

def test_location_view_not_found(self):
    url = reverse('location_detail', kwargs={'location_id': 999})
    response = self.client.get(url)
    
    self.assertResponseStatusCode(response, 404)
    self.assertHtmlResponse(response)
```

#### Synchronous JSON Views
- Test status codes and JSON response structure separately
- Verify API endpoint error responses

```python
def test_api_status_returns_json(self):
    url = reverse('api_status')
    response = self.client.get(url)
    
    self.assertSuccessResponse(response)
    self.assertJsonResponse(response)
    data = response.json()
    self.assertIn('timestamp', data)
    self.assertIn('alertData', data)

def test_api_invalid_request(self):
    url = reverse('api_update')
    response = self.client.post(url, {'invalid': 'data'})
    
    self.assertErrorResponse(response)
    self.assertJsonResponse(response)
```

#### Asynchronous HTML Views
- Test AJAX request detection and proper status codes
- Verify HTML snippet responses for DOM insertion
- Test response when called incorrectly (sync instead of async)

```python
def test_async_html_view_with_ajax_header(self):
    url = reverse('console_sensor_view', kwargs={'sensor_id': 1})
    response = self.async_get(url)  # Includes HTTP_X_REQUESTED_WITH header
    
    self.assertSuccessResponse(response)
    self.assertJsonResponse(response)
    # Test that async view returns content for DOM insertion
    data = response.json()
    self.assertIn('insert_map', data)
    
def test_async_view_called_synchronously_redirects(self):
    url = reverse('console_sensor_view', kwargs={'sensor_id': 1})
    response = self.client.get(url)  # Regular GET without AJAX headers
    
    expected_redirect = reverse('console_home')
    self.assertRedirects(response, expected_redirect)

def test_async_view_error_handling(self):
    url = reverse('console_sensor_view', kwargs={'sensor_id': 999})
    response = self.async_get(url)
    
    self.assertErrorResponse(response)
    self.assertJsonResponse(response)  # Error responses may be JSON
```

#### Asynchronous JSON Views
- Test AJAX JSON responses with correct status codes
- Verify JavaScript-consumable data formats
- Test error handling in async context

```python
def test_async_json_view_returns_update_data(self):
    url = reverse('api_update')
    response = self.async_post(url, {'entity_id': 1})  # Includes AJAX headers
    
    self.assertSuccessResponse(response)
    self.assertJsonResponse(response)
    data = response.json()
    self.assertIn('timestamp', data)
    self.assertIn('alertData', data)

def test_async_json_view_validation_error(self):
    url = reverse('api_update')
    response = self.async_post(url, {})  # Missing required data
    
    self.assertErrorResponse(response)
    self.assertJsonResponse(response)
```

#### Dual-Mode Views (HiModalView/HiGridView)
- Test both synchronous and asynchronous call patterns
- Verify correct response type based on request context
- Test modal rendering vs. full page rendering

```python
def test_modal_view_sync_request(self):
    url = reverse('weather_current_conditions_details')
    response = self.client.get(url)  # Regular request without AJAX headers
    
    self.assertSuccessResponse(response)
    self.assertHtmlResponse(response)
    # Should render both the base page and the modal template
    self.assertTemplateRendered(response, 'pages/main_default.html')
    self.assertTemplateRendered(response, 'weather/modals/conditions_details.html')

def test_modal_view_async_request(self):
    url = reverse('weather_current_conditions_details')
    response = self.async_get(url)  # Request with AJAX headers
    
    self.assertSuccessResponse(response)
    self.assertJsonResponse(response)
    self.assertTemplateRendered(response, 'weather/modals/conditions_details.html')
    # Verify modal response structure for AJAX
    data = response.json()
    self.assertIn('modal', data)
```

### View Testing Guidelines

**DO:**
- Use `reverse()` with URL names instead of hardcoded URL strings
- Use `async_get()`, `async_post()` etc. for AJAX requests to ensure proper headers
- Test status codes, response types, and template rendering as separate concerns
- Use `assertTemplateRendered()` to verify template usage independently
- Use real database operations and test data setup
- Test actual request/response flows through real code paths
- Mock only at system boundaries (HTTP calls, external services)
- Test conditional logic that affects response content or status codes
- Test error handling and edge cases with appropriate status code assertions
- Verify context data correctness
- **Test each view's specific decisions, not downstream redirect effects** (use `fetch_redirect_response=False` for immediate redirects)

**DON'T:**
- Use hardcoded URL strings - always use `reverse()` with URL names
- Use regular `client.get()` for AJAX requests - use `async_get()` helper methods
- Mix status code, response type, and template assertions in single method calls
- Test template content text that may change - use template name verification instead
- Use magic strings instead of defined enums/constants (e.g., `'EDIT'` vs `ViewMode.EDIT`)
- Mock internal Django components or ORM operations
- Test implementation details instead of interface contracts
- Create tests that depend on log message assertions
- Over-mock internal application components

### Database Setup for View Tests

View tests should create real test data to verify complete request/response flows:

```python
def setUp(self):
    super().setUp()
    self.location = Location.objects.create(name='Test Location')
    self.entity = Entity.objects.create(
        integration_id='test.entity',
        integration_name='test_integration',
        location=self.location
    )

def test_location_view_with_entities(self):
    url = reverse('location_detail', kwargs={'location_id': self.location.id})
    response = self.client.get(url)
    
    self.assertSuccessResponse(response)
    self.assertHtmlResponse(response)
    self.assertTemplateRendered(response, 'location/detail.html')
    self.assertEqual(response.context['location'], self.location)
    # Test that entity is in context or response data
    self.assertIn(self.entity, response.context['entities'])
```

### Authentication and Permission Testing

For views requiring authentication:

```python
def test_protected_view_requires_authentication(self):
    url = reverse('protected_view')
    response = self.client.get(url)
    login_url = reverse('login')
    self.assertRedirects(response, f'{login_url}?next={url}')

def test_protected_view_with_authenticated_user(self):
    self.client.force_login(self.user)
    url = reverse('protected_view')
    response = self.client.get(url)
    
    self.assertSuccessResponse(response)
    self.assertHtmlResponse(response)
```

### Form Validation Testing

For views that process forms:

```python
def test_form_validation_success(self):
    form_data = {'name': 'Test Entity', 'location': self.location.id}
    url = reverse('entity_create')
    response = self.client.post(url, form_data)
    
    success_url = reverse('entity_list')
    self.assertRedirects(response, success_url)
    self.assertTrue(Entity.objects.filter(name='Test Entity').exists())

def test_form_validation_errors(self):
    form_data = {'name': ''}  # Missing required field
    url = reverse('entity_create')
    response = self.client.post(url, form_data)
    
    self.assertSuccessResponse(response)  # Form errors return 200, not 4xx
    self.assertHtmlResponse(response)
    self.assertTemplateRendered(response, 'entity/create.html')
    self.assertFormError(response, 'form', 'name', 'This field is required.')
```

## Integration Tests

_TBD_

## Development Data Injection

The development data injection system provides a runtime mechanism to modify application behavior without code changes or Django restarts. This is useful for testing scenarios that would otherwise require complex backend state setup.

**Example use case:** Injecting pre-formatted status responses for UI testing - you can override the `/api/status` endpoint to return specific transient view suggestions, allowing you to test auto-view switching behavior without manipulating the actual backend systems.

**General concept:** Any code location can become an injection point by adding a `DEBUG_FORCE_*` setting and a conditional check. The system supports both one-time and persistent overrides via management commands.

For complete usage details, implementation instructions, and extending to new injection points, see:
```
hi.testing.dev_injection.DevInjectionManager
```

## Visual Testing Page

Visit: [http://127.0.0.1:8411/testing/ui](http://127.0.0.1:8411/testing/ui).

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

The templates for these tests, by convention, would be put in the app templates directory as `templates/${APPNAME}/testing/ui`. At a minimum, you will probably want a home page `templates/${APPNAME}/testing/ui/home.html` like this:

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
        return render(request, "${APPNAME}/testing/ui/home.html", context )
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

### UI Testing Framework Guidelines

The visual testing framework at `/testing/ui` is designed for viewing UI styling and layout during development. These are **read-only** views that should never modify system state.

#### Critical UI Testing Principle: System State Isolation

**NEVER modify real system state in UI test views**:
- Do not add data to real managers (AlertManager, WeatherManager, etc.)
- Do not modify database records 
- Do not modify in-memory caches or singletons
- Do not persist test data that appears in production views

**Correct Approach - Render Templates Directly:**
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

**Incorrect Approach - Modifying System State:**
```python
# BAD - This modifies real AlertManager state
class TestUiAlertDetailsView(AlertDetailsView, AlertMixin):
    def get(self, request, *args, **kwargs):
        alert = self._create_synthetic_alert(alert_type)
        
        # WRONG - Adding to real system manager
        alert_manager = self.alert_manager()
        alert_manager._alert_queue._alert_list.append(alert)
        
        return super().get(request, *args, **kwargs)
```

#### UI Testing Architecture Patterns

**When to Inherit vs. Render Directly:**

1. **Render Templates Directly (Preferred):**
   - For testing UI styling and layout
   - When you need specific synthetic data scenarios
   - When testing requires system state isolation
   - Follows pattern used by weather, notify modules

2. **Inherit from Production Views (Avoid):**
   - Only when testing actual view logic, not just UI styling
   - Requires careful state management to avoid system pollution
   - Must ensure test data doesn't persist

**Code Duplication Prevention:**
- Move shared logic to domain object methods (e.g., `Alert.get_first_visual_content()`)
- Use centralized synthetic data classes
- Create utility functions for common data preparation patterns

### Email Testing

There are some helper base classes to test viewing email formatting and sending emails.
``` shell
hi.tests.ui.email_test_views.py
```
This requires the email templates follow the naming patterns expected in view classes.

