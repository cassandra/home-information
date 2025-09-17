# Testing Patterns

## View Testing Architecture

### View Types & Test Classes
Five distinct view patterns requiring different testing approaches:
1. **Synchronous HTML Views** - Traditional Django page views
2. **Synchronous JSON Views** - API endpoints
3. **Asynchronous HTML Views** - AJAX views returning HTML snippets
4. **Asynchronous JSON Views** - AJAX views returning JSON
5. **Dual-Mode Views** - HiModalView/HiGridView handling both sync and async

### Base Test Classes
From `hi.tests.view_test_base`:
- `SyncViewTestCase` - Regular `client.get()`, `client.post()`
- `AsyncViewTestCase` - AJAX requests with `async_get()`, `async_post()`
- `DualModeViewTestCase` - Tests both sync and async modes

### Key Assertion Methods
**Status**: `assertSuccessResponse()`, `assertErrorResponse()`, `assertServerErrorResponse()`
**Response Type**: `assertHtmlResponse()`, `assertJsonResponse()`
**Templates**: `assertTemplateRendered(response, template_name)`
**Session**: `assertSessionValue()`, `assertSessionContains()`
**AJAX Methods**: `async_get()`, `async_post()`, `async_put()`, `async_delete()`

### Session Management Helpers
- `setSessionViewType()`, `setSessionViewMode()`
- `setSessionLocationView()`, `setSessionCollection()`
- `setSessionViewParameters()` - Set multiple session values

## Manager Async/Sync Testing

### Manager Pattern Characteristics
- Singleton pattern with `__init_singleton__()`
- Dual sync/async methods for Django views and integration services
- Thread safety and shared state management

### Async Testing Requirements
**Use `AsyncManagerTestCase(TransactionTestCase)`** for async manager tests:
- Shared event loop prevents SQLite concurrency issues
- Reset singleton state between tests: `ManagerClass._instances = {}`
- Use `run_async(coroutine)` helper method
- Wrap database operations with `sync_to_async()`

### Critical ORM Pattern
```python
# In manager async methods - prevent lazy loading
entities = await sync_to_async(list)(
    Entity.objects.select_related('location').all()
)

# In tests - wrap database operations
entity = await sync_to_async(Entity.objects.create)(name='Test')
```

## Django-Specific Patterns

### Abstract Model Testing
Create concrete test classes for abstract models, mock Django operations for database-less testing.

### Integration Key Pattern
Test `IntegrationKeyMixin` inheritance with `integration_id` and `integration_name` fields.

### Singleton Manager Testing
Verify singleton behavior: `self.assertIs(manager1, manager2)`

### Authentication Testing
- Test protected views require authentication (redirect to login)
- Use `self.client.force_login(user)` for authenticated tests

### Form Validation Testing
- Success: Check redirects and database changes
- Errors: Form errors return 200 status, verify `assertFormError()`

## File Upload Testing

### Media Root Isolation
**Individual Tests**: Use `self.isolated_media_root()` context manager
**Test Classes**: Override `MEDIA_ROOT` in setUp/tearDown with temporary directory

## Key Test Base Classes

### View Testing
- `hi.tests.view_test_base.SyncViewTestCase`
- `hi.tests.view_test_base.AsyncViewTestCase`
- `hi.tests.view_test_base.DualModeViewTestCase`

### Manager Testing
- `hi.tests.view_test_base.AsyncManagerTestCase` (extends TransactionTestCase)
- Custom event loop management for async tests

### Utilities
- `hi.tests.view_test_base.ViewTestBase` - Common utilities and assertions
- Session management helpers
- File operation helpers with media root isolation

## Related Documentation
- [Testing Guidelines](testing-guidelines.md)
- [UI Testing](../frontend/ui-testing.md)
- [Backend Guidelines](../backend/backend-guidelines.md)
