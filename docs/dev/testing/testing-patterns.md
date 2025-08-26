# Testing Patterns

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

Use these base classes from `hi.tests.view_test_base`:

```python
from django.urls import reverse
from hi.tests.view_test_base import SyncViewTestCase, AsyncViewTestCase, DualModeViewTestCase

class TestMySyncViews(SyncViewTestCase):
    def test_synchronous_html_view(self):
        url = reverse('my_view_name')
        response = self.client.get(url)
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
        response = self.client.get(url)
        self.assertSuccessResponse(response)
        self.assertHtmlResponse(response)
        
    def test_view_asynchronous_mode(self):
        url = reverse('my_dual_view_name')
        response = self.async_get(url)
        self.assertSuccessResponse(response)
        self.assertJsonResponse(response)
```

### Helper Methods

**Status Code Assertions:**
- `assertResponseStatusCode(response, expected_code)` - Verifies specific status code
- `assertSuccessResponse(response)` - Verifies 2xx status code
- `assertErrorResponse(response)` - Verifies 4xx status code
- `assertServerErrorResponse(response)` - Verifies 5xx status code

**Response Type Assertions:**
- `assertHtmlResponse(response)` - Verifies HTML content type
- `assertJsonResponse(response)` - Verifies JSON content type

**Template Assertions:**
- `assertTemplateRendered(response, template_name)` - Verifies specific template was used

**Session Assertions:**
- `assertSessionValue(response, key, expected_value)` - Verifies session contains specific key-value
- `assertSessionContains(response, key)` - Verifies session contains specific key

**Session Management:**
- `setSessionViewType(view_type)` - Set ViewType in session
- `setSessionViewMode(view_mode)` - Set ViewMode in session
- `setSessionLocationView(location_view)` - Set location_view_id in session
- `setSessionCollection(collection)` - Set collection_id in session
- `setSessionViewParameters(view_type=None, view_mode=None, location_view=None, collection=None)`

**Redirect Testing:**
- `assertRedirectsToTemplates(initial_url, expected_templates)` - Follow redirects and verify final templates

**AJAX Request Methods:**
- `async_get(url, data=None)` - GET request with AJAX headers
- `async_post(url, data=None)` - POST request with AJAX headers
- `async_put(url, data=None)` - PUT request with AJAX headers
- `async_delete(url, data=None)` - DELETE request with AJAX headers

## Manager Class Async/Sync Testing

Many manager classes in this codebase follow a dual sync/async pattern to support both traditional Django views and async integration services.

### Manager Pattern Characteristics
- Singleton pattern with `__init_singleton__()`
- Both sync `ensure_initialized()` and async initialization methods
- Mix of sync methods for Django ORM access and async methods for integration services
- Thread safety considerations and shared state management

### Async Testing Infrastructure

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

## Django-Specific Testing Patterns

### Abstract Model Testing
```python
# Create concrete test class for abstract models
class ConcreteTestModel(AbstractModel):
    def required_abstract_method(self):
        return "test_implementation"

# Mock Django operations for database-less testing
with patch('django.db.models.Model.save') as mock_save:
    instance.save()
    mock_save.assert_called_once()
```

### Integration Key Pattern Testing
```python
def test_integration_key_inheritance(self):
    model = TestModel.objects.create(
        integration_id='test_id',
        integration_name='test_integration'
    )
    self.assertEqual(model.integration_id, 'test_id')
```

### Singleton Manager Testing
```python
def test_manager_singleton_behavior(self):
    manager1 = ManagerClass()
    manager2 = ManagerClass()
    self.assertIs(manager1, manager2)
```

### Background Process and Threading Testing
```python
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

## Authentication and Permission Testing

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

## Form Validation Testing

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

## Database Setup for Tests

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
    self.assertIn(self.entity, response.context['entities'])
```

## Related Documentation
- Testing guidelines: [Testing Guidelines](testing-guidelines.md)
- UI testing: [UI Testing](../frontend/ui-testing.md)
- Backend testing: [Backend Guidelines](../backend/backend-guidelines.md#testing)