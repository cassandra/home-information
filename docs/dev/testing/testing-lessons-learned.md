# Django Testing Anti-Patterns and Lessons Learned

## Overview

This document captures critical discoveries and learnings from a comprehensive effort to fix over-mocking issues in Django tests across the HI application. The work involved systematically converting heavily mocked tests to use real objects, revealing numerous anti-patterns and best practices.

## Core Anti-Patterns Identified

### 1. Over-Mocking Database Operations

**Problem**: Tests were mocking fundamental Django operations like model creation, relationships, and queries instead of using real database objects in test transactions.

**Examples Found**:
```python
# Anti-pattern: Mocking basic model operations
@patch.object(CollectionManager, 'toggle_entity_in_collection')
@patch.object(CollectionManager, 'get_collection_data')
def test_post_toggle_entity_add(self, mock_toggle, mock_get_data):
    mock_toggle.return_value = True
```

**Solution**:
```python
# Better: Test real database relationships
def test_post_toggle_entity_add(self):
    # Verify entity is not in collection initially
    self.assertFalse(CollectionEntity.objects.filter(collection=self.collection, entity=self.entity).exists())
    
    response = self.client.post(url)
    
    # Verify entity was added to collection
    self.assertTrue(CollectionEntity.objects.filter(collection=self.collection, entity=self.entity).exists())
```

**Lesson**: Django's test framework provides isolated database transactions. Use real objects instead of mocking database operations.

### 2. Mocking View Delegation Instead of Testing Integration

**Problem**: Tests mocked entire view classes when testing view delegation, missing integration issues and actual functionality.

**Example**:
```python
# Anti-pattern: Mocking the delegated view
@patch('hi.apps.edit.views.CollectionReorderEntitiesView')
def test_reorder_entities_in_collection(self, mock_view_class):
    mock_view = mock_view_class.return_value
    mock_view.post.return_value = JsonResponse({'status': 'ok'})
```

**Solution**:
```python
# Better: Test the full integration
def test_reorder_entities_in_collection(self):
    # Create real entities and add to collection
    CollectionEntity.objects.create(collection=self.collection, entity=entity1, order_id=0)
    
    # Test actual reordering
    response = self.client.post(url, post_data)
    
    # Verify database changes
    reordered_entities = list(CollectionEntity.objects.filter(collection=self.collection).order_by('order_id'))
    self.assertEqual(reordered_entities[0].entity, entity3)  # Verify new order
```

**Lesson**: Test the full integration path rather than just delegation mechanics.

### 3. Incorrect Response Type Expectations

**Problem**: Tests expected traditional HTTP redirects (302) when views actually returned JSON responses (200) via antinode.js integration.

**Example**:
```python
# Anti-pattern: Wrong response expectation
def test_post_delete_with_confirmation(self):
    response = self.client.post(url, {'action': 'confirm'})
    self.assertEqual(response.status_code, 302)  # Wrong!
```

**Solution**:
```python
# Better: Expect JSON responses from antinode views
def test_post_delete_with_confirmation(self):
    response = self.client.post(url, {'action': 'confirm'})
    
    self.assertSuccessResponse(response)
    self.assertJsonResponse(response)
    
    data = response.json()
    self.assertEqual(data['location'], expected_url)
```

**Lesson**: Understand your application's AJAX/async response patterns. Modern web apps often return JSON instead of traditional redirects.

## Model Relationship Discoveries

### Many-to-Many Through Models

**Discovery**: Collections and entities have a many-to-many relationship through `CollectionEntity`, not a direct relationship.

**Wrong Assumption**:
```python
# This doesn't work - no direct relationship
self.collection.entities.add(self.entity)
```

**Correct Approach**:
```python
# Use the through model
from hi.apps.collection.models import CollectionEntity
CollectionEntity.objects.create(collection=self.collection, entity=self.entity)
```

**Lesson**: Always verify model relationships in Django admin or model definitions before writing tests.

### Entity Pairing System

**Discovery**: Entity pairings work through `EntityStateDelegation` objects, not direct relationships.

**Implementation**:
```python
from hi.apps.entity.models import EntityStateDelegation
for entity_state in self.entity.states.all():
    EntityStateDelegation.objects.create(
        entity_state=entity_state,
        delegate_entity=self.paired_entity
    )
```

**Lesson**: Complex business logic often involves intermediate models that aren't immediately obvious.

## Form Validation Requirements

### Missing Required Fields

**Discovery**: `LocationItemPositionForm` requires all position fields (`svg_x`, `svg_y`, `svg_scale`, `svg_rotate`), not just coordinates.

**Problem**:
```python
# Incomplete form data
response = self.client.post(url, {
    'svg_x': '60.0',
    'svg_y': '70.0'  # Missing svg_scale and svg_rotate
})
# Position wasn't updated in database
```

**Solution**:
```python
# Complete form data
response = self.client.post(url, {
    'svg_x': '60.0',
    'svg_y': '70.0',
    'svg_scale': '1.0',
    'svg_rotate': '0.0'
})
```

**Lesson**: Always check form field requirements. Use Django form validation errors to debug incomplete test data.

## Session and Middleware Requirements

### View Parameter Dependencies

**Discovery**: Many views depend on session state managed by custom middleware for location, collection, and view mode context.

**Common Setup Pattern**:
```python
def setUp(self):
    super().setUp()
    # Set edit mode (required by decorator)
    self.setSessionViewMode(ViewMode.EDIT)
    
    # Create location/location view for middleware
    location = Location.objects.create(...)
    location_view = LocationView.objects.create(location=location, ...)
    
    # Set collection context if needed
    self.setSessionCollection(self.collection)
```

**Lesson**: Understand your application's middleware dependencies. Views may require specific session state to function.

### Default Object Resolution

**Discovery**: Views often use "get_default" patterns that require objects with specific `order_id` values.

**Pattern**:
```python
# Ensure this is the default by setting order_id=0
self.collection.order_id = 0
self.collection.save()
```

**Lesson**: Many applications use ordering conventions for default object resolution.

## Test Infrastructure Patterns

### Synthetic Data Pattern

**Discovery**: The application uses a consistent synthetic data pattern across modules for test data creation.

**Structure**:
```python
# hi/apps/{module}/tests/synthetic_data.py
class {Module}SyntheticData:
    @staticmethod
    def create_test_{model}(**kwargs) -> {Model}:
        unique_id = str(uuid.uuid4())[:8]
        defaults = {
            'name': f'Test {Model} {unique_id}',
            # ... reasonable defaults
        }
        defaults.update(kwargs)
        return {Model}.objects.create(**defaults)
```

**Lesson**: Centralized test data creation prevents duplication and ensures consistency.

### Test Base Class Hierarchy

**Discovery**: The application uses specialized test base classes with different capabilities.

**Classes Found**:
- `SyncViewTestCase`: For traditional synchronous views
- `DualModeViewTestCase`: For views that work in both sync and async modes
- Custom assertion methods: `assertJsonResponse()`, `assertHtmlResponse()`, `assertSuccessResponse()`

**Lesson**: Leverage application-specific test utilities rather than recreating common patterns.

## Enum and String Conversion Patterns

### LabeledEnum Usage

**Discovery**: The application uses `LabeledEnum` types that require string conversion with `str()`.

**Pattern**:
```python
# Always use str() conversion for enum fields
entity = Entity.objects.create(
    entity_type_str=str(EntityType.LIGHT)  # Not just EntityType.LIGHT
)
```

**Lesson**: Understand your application's enum handling patterns.

### HTML ID Format Conventions

**Discovery**: The application uses specific HTML ID formats for different item types.

**Pattern**:
```python
# Use ItemType.parse_html_id() format: hi-{type}-{id}
'hi-entity-1'           # Entity with ID 1
'hi-collection-1'       # Collection with ID 1  
'hi-location_view-1'    # LocationView with ID 1 (note underscore)
```

**Lesson**: Web applications often have specific ID conventions for JavaScript integration.

## Error Handling and Exception Patterns

### Custom Exception Handling

**Discovery**: The application uses custom exceptions handled by middleware rather than Django's built-in HTTP exceptions.

**Pattern**:
```python
# Application uses custom MethodNotAllowedError
# Middleware converts to HttpResponseNotAllowed(405)
```

**Lesson**: Understand your application's exception handling architecture.

## Best Practices Derived

### 1. Test Real Behavior, Not Implementation Details

- Test database state changes, not method calls
- Test full request-response cycles, not just view delegation
- Verify business logic outcomes, not internal mechanics

### 2. Understand Your Application Architecture

- Know your middleware dependencies
- Understand session management patterns  
- Learn enum and string conversion requirements
- Study model relationship patterns

### 3. Use Application-Specific Test Utilities

- Leverage existing test base classes
- Use synthetic data generators
- Employ custom assertion methods
- Follow established test data patterns

### 4. Debug Systematically

- Read error messages carefully - they often reveal missing setup
- Check form validation requirements when database changes don't occur
- Verify response types match expectations (JSON vs HTML vs redirects)
- Use `print()` debugging in tests to understand data flow

### 5. Create Missing Test Infrastructure

- Build synthetic data generators following established patterns
- Create reusable test setup methods
- Document model relationship requirements
- Share learnings with the team

## Conclusion

The transition from over-mocked tests to real object testing revealed deep application architecture patterns and significantly improved test coverage quality. The key insight is that Django's test framework is designed to support real database operations in isolated transactions, making mocking of basic CRUD operations unnecessary and counterproductive.

These patterns and lessons should guide future test development to avoid the anti-patterns that led to fragile, hard-to-maintain tests that provided false confidence in system behavior.
