# JavaScript Testing

This document describes the approach for testing JavaScript modules in the Home Information application.

## Overview

JavaScript testing uses QUnit framework with a local-first approach that requires no build tools or external dependencies. Tests focus on business logic functions rather than DOM manipulation or framework internals.

## Philosophy

- **Local-first**: All dependencies vendored locally, no CDN requirements
- **Lightweight**: QUnit framework only, no complex build pipeline
- **Manual execution**: Tests run in browser via simple HTML files
- **Business logic focus**: Test core functions, algorithms, and state management
- **Real browser testing**: Actual browser environment catches issues that mocks miss

## Framework Choice: QUnit

Selected for:
- Minimal setup (just HTML + script tags)
- No build tools required
- Django-compatible static file serving
- Comprehensive async testing support
- Small footprint (~25KB minified)

## Test Structure

```
/src/hi/static/tests/
├── test-all.html          # Master test runner (recommended)
├── test-{module}.html     # Individual module runners
├── test-{module}.js       # Test cases for each module
└── qunit/                 # QUnit framework (vendored)
```

## Running Tests

**Primary workflow:**
```bash
open src/hi/static/tests/test-all.html
```

**Via Django server:**
```bash
src/manage.py runserver
# Navigate to: http://127.0.0.1:8411/static/tests/test-all.html
```

## Example Implementation

The `auto-view.js` module demonstrates the complete testing approach:

- **Source**: `/src/hi/static/js/auto-view.js` 
- **Tests**: `/src/hi/static/tests/test-auto-view.js`
- **Individual runner**: `/src/hi/static/tests/test-auto-view.html`

Key test patterns demonstrated:
- Time-dependent logic testing with `Date.now()` mocking
- Throttling behavior with async timing tests
- Feature detection and caching verification
- State management transitions
- Context preservation in callbacks

## Testing Best Practices

### Focus Areas (High Value)
- Complex algorithms and timing logic
- State management and transitions
- Feature detection and caching
- Integration between module functions
- Edge cases and boundary conditions

### Avoid Testing (Low Value)
- jQuery DOM manipulation internals
- Browser event system mechanics
- Simple property getters/setters
- Framework-provided functionality

### Mocking Strategy
- **Mock system boundaries**: `Date.now()`, `window` properties, external APIs
- **Use real objects**: Prefer actual module instances over mocks
- **Minimal mocking**: Only mock what's necessary for isolation

## Adding New Module Tests

1. **Create test file**: `test-{module}.js` following QUnit patterns:
   ```javascript
   QUnit.module('ModuleName.functionName', function(hooks) {
       QUnit.test('description of test', function(assert) {
           // Arrange, Act, Assert
           const result = ModuleName.functionName(input);
           assert.equal(result, expected, 'Function returns expected value');
       });
   });
   ```

2. **Update master runner**: Add to `test-all.html`:
   ```html
   <!-- In source modules section -->
   <script src="../js/module-name.js"></script>
   
   <!-- In test modules section -->  
   <script src="test-{module}.js"></script>
   ```

3. **Optional**: Create individual runner `test-{module}.html` for focused debugging

## Integration with Development Workflow

- **Manual execution**: Part of JavaScript development process
- **PR checklist**: Include "JavaScript tests passing" verification
- **No CI automation**: Lightweight approach prioritizes simplicity
- **Browser compatibility**: Test in target browsers (Firefox, Chrome)

## Future Considerations

- Additional modules can reuse the established pattern
- Test coverage expansion as JavaScript complexity grows  
- Potential automation if testing frequency increases significantly
- Maintain local-first philosophy for any framework additions

This approach balances comprehensive testing coverage with development simplicity, providing confidence in JavaScript functionality without complex tooling overhead.
