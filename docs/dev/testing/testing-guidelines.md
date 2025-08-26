# Testing Guidelines

## Unit Tests

```bash
cd $PROJ_DIR/src
./manage.py test
```

## High-Value vs Low-Value Testing Criteria

### HIGH-VALUE Tests (Focus Here)
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

### LOW-VALUE Tests (Avoid These)
- Simple property getters/setters that just return field values
- Django ORM internals verification (Django already tests this)
- Trivial enum label checking without business logic
- Basic field access and obvious default values
- Simple string formatting without complex logic

## Critical Testing Anti-Patterns (Never Do These)

### NEVER Test Behavior Based on Log Messages

**Problem**: Log message assertions (`self.assertLogs()`, checking log output) are fragile and break easily when logging changes

**Issue**: Many existing tests deliberately disable logging for performance and clarity

**Solution**: Test actual behavior changes - state modifications, return values, method calls, side effects

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

### Additional Testing Anti-Patterns

#### Mock-Centric Testing Instead of Behavior Testing

**Problem**: Tests focus on verifying mock calls rather than testing actual behavior and return values.

```python
# BAD - Testing mock calls instead of behavior
@patch('module.external_service')
def test_process_data(self, mock_service):
    mock_service.return_value = {'status': 'success'}
    result = processor.process_data(input_data)
    mock_service.assert_called_once_with(expected_params)
    # Missing: What did process_data actually return?

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

#### Over-Mocking Internal Components

**Problem**: Mocking too many internal components breaks the integration between parts of the system.

```python
# BAD - Mocking both HTTP layer AND internal converter
@patch('module.http_client.get')
@patch('module.DataConverter.parse')
def test_fetch_and_parse(self, mock_parse, mock_get):
    mock_get.return_value = mock_response
    mock_parse.return_value = mock_parsed_data
    result = service.fetch_and_parse()
    # This tests nothing about actual data flow

# GOOD - Mock only at system boundaries
@patch('module.http_client.get')
def test_fetch_and_parse_integration(self, mock_get):
    mock_get.return_value = Mock(text='{"real": "json", "data": "here"}')
    result = service.fetch_and_parse()
    # Test that real data flows through real converter
    self.assertIsInstance(result, ExpectedDataType)
    self.assertEqual(result.parsed_field, "expected_value")
```

#### Testing Implementation Details Instead of Interface Contracts

**Problem**: Tests verify internal implementation details rather than public interface behavior.

```python
# BAD - Testing exact HTTP parameters instead of behavior
def test_api_call_constructs_correct_url(self):
    client.make_request('entity_123')
    expected_url = 'https://api.service.com/v1/entities/entity_123'
    expected_headers = {'Authorization': 'Bearer token', 'Content-Type': 'application/json'}
    mock_post.assert_called_once_with(expected_url, headers=expected_headers)

# GOOD - Testing the interface contract
def test_api_call_returns_entity_data(self):
    mock_response_data = {'id': 'entity_123', 'name': 'Test Entity'}
    mock_post.return_value = Mock(json=lambda: mock_response_data)
    result = client.make_request('entity_123')
    # Test the contract: what the method promises to return
    self.assertEqual(result['id'], 'entity_123')
    self.assertEqual(result['name'], 'Test Entity')
```

## Testing Best Practices Summary

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

### Database vs Mock Testing Strategy

**Prefer Real Database Operations:**
- Database state verification tests actual business logic and relationships
- Cascade deletion, constraints, and indexing are critical system behaviors
- TransactionTestCase provides proper isolation for database-dependent tests
- Real data flows through real code paths reveal integration issues

**When to Mock vs Real Database:**
- **Mock external APIs** (HTTP calls, third-party services)
- **Use real database** for business logic, relationships, and data transformations
- **Mock at system boundaries**, not internal ORM operations

## Django-Specific Testing Patterns

See [Testing Patterns](testing-patterns.md) for detailed Django testing patterns including:
- Abstract Model Testing
- Integration Key Pattern Testing
- Singleton Manager Testing
- Background Process and Threading Testing
- Manager Class Async/Sync Testing

## Development Data Injection

The development data injection system provides a runtime mechanism to modify application behavior without code changes or Django restarts. This is useful for testing scenarios that would otherwise require complex backend state setup.

**Example use case:** Injecting pre-formatted status responses for UI testing - you can override the `/api/status` endpoint to return specific transient view suggestions, allowing you to test auto-view switching behavior without manipulating the actual backend systems.

For complete usage details, see: `hi.testing.dev_injection.DevInjectionManager`

## Related Documentation
- Django-specific patterns: [Testing Patterns](testing-patterns.md)
- Test data management: [Test Data Management](test-data-management.md)
- Simulator testing: [Test Simulator](test-simulator.md)
- Coding standards: [Coding Standards](../shared/coding-standards.md)
- View testing: [Frontend Guidelines](../frontend/frontend-guidelines.md#view-testing)