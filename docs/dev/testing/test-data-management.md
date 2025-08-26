# Test Data Management

## Visual Testing Page

Visit: [http://127.0.0.1:8411/testing/ui](http://127.0.0.1:8411/testing/ui)

These tests/ui views are only available in the development environment when `DEBUG=True`. They are conditionally loaded in the root `urls.py`.

## UI Testing Framework

For comprehensive UI testing framework guidelines, visual testing setup, component testing patterns, and system state isolation principles, see [UI Testing](../frontend/ui-testing.md).

## Email Testing

There are helper base classes to test viewing email formatting and sending emails:
```
hi.tests.ui.email_test_views.py
```

This requires the email templates follow the naming patterns expected in view classes.

## Synthetic Data Classes

We have another pattern that we use for generating mock/synthetic data since the need for this comes up in testing scenarios too, so we like to create it once and reuse it rather than later deleting it when it is replaced.  The pattern is to put these methods like `_create_mock_sensor_history()` into a file in the tests directory and since this data is related to the sense module, it would be `src/hi/apps/sense/tests/synthetic_data.py`.  This supports our principle of not using mocked DB models.

Create centralized synthetic data generators for consistent test data:

```python
class EntitySyntheticData:
    @staticmethod
    def create_test_entity(location=None, **kwargs):
        defaults = {
            'name': 'Test Entity',
            'integration_id': 'test.entity',
            'integration_name': 'test_integration',
            'location': location or LocationSyntheticData.create_test_location()
        }
        defaults.update(kwargs)
        return Entity.objects.create(**defaults)
    
    @staticmethod
    def create_entity_with_state(state_type, state_value):
        entity = create_test_entity()
        # Create associated state and sensor
        return entity
```

## Development Data Injection

The development data injection system provides runtime mechanism to modify application behavior without code changes:

```python
# Example: Override /api/status endpoint for testing
from hi.testing.dev_injection import DevInjectionManager

manager = DevInjectionManager()
manager.set_injection('DEBUG_FORCE_STATUS_RESPONSE', {
    'transient_view': 'alert_active',
    'alert_count': 5
})
```

This allows testing specific scenarios without complex backend state setup.

## Test Data Cleanup

Always ensure proper cleanup in test tearDown:

```python
def tearDown(self):
    # Clear any singleton state
    if hasattr(ManagerClass, '_instances'):
        ManagerClass._instances = {}
    
    # Clear cached data
    cache.clear()
    
    # Call parent tearDown
    super().tearDown()
```

## Related Documentation
- Testing guidelines: [Testing Guidelines](testing-guidelines.md)
- Testing patterns: [Testing Patterns](testing-patterns.md)
- UI development: [Frontend Guidelines](../frontend/frontend-guidelines.md)
