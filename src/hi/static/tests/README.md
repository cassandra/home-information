# JavaScript Unit Tests

This directory contains unit tests for JavaScript modules in the Home Information application.

> **See [JavaScript Testing Documentation](../../../docs/dev/frontend/javascript-testing.md)** for testing philosophy, approach, and best practices.

## Running Tests

### All Tests (Recommended)

1. **Open the master test runner in your browser:**
   ```bash
   # From project root
   open src/hi/static/tests/test-all.html
   
   # Or navigate to the file in your browser:
   # file:///path/to/project/src/hi/static/tests/test-all.html
   ```

2. **Via Django development server:**
   ```bash
   # Start the Django development server
   src/manage.py runserver
   
   # Then navigate to:
   # http://127.0.0.1:8411/static/tests/test-all.html
   ```

### Individual Module Tests

For debugging or focused testing, you can also run individual test files:
- `test-auto-view.html` - Tests for auto-view.js only

### Test Results

The QUnit test runner will display:
- Total number of tests
- Passed/failed counts
- Detailed results for each test
- Execution time

Green bars indicate passing tests, red bars indicate failures.

## Test Structure

```
/src/hi/static/tests/
├── README.md              # This file
├── test-all.html          # Master test runner (runs all tests)
├── test-auto-view.html    # Individual test runner for auto-view.js
├── test-auto-view.js      # Test cases for auto-view.js
├── run-tests-node.js      # Node.js command-line test runner
└── qunit/                 # QUnit framework files (vendored)
    ├── qunit-2.20.0.js
    └── qunit-2.20.0.css
```

## Writing New Tests

To add tests for a new JavaScript module:

1. **Create the test JavaScript file:**
   ```javascript
   // test-module-name.js
   QUnit.module('ModuleName.functionName', function(hooks) {
       QUnit.test('description of test', function(assert) {
           // Arrange
           const input = 'test';
           
           // Act
           const result = ModuleName.functionName(input);
           
           // Assert
           assert.equal(result, 'expected', 'Function returns expected value');
       });
   });
   ```

2. **Add to the master test runner:**
   Edit `test-all.html` and add:
   ```html
   <!-- In the source modules section -->
   <script src="../js/module-name.js"></script>
   
   <!-- In the test modules section -->
   <script src="test-module-name.js"></script>
   ```

3. **Optional: Create individual test runner:**
   For focused debugging, create `test-module-name.html` following the pattern of `test-auto-view.html`

This approach means you only need to visit one URL (`test-all.html`) to run all JavaScript tests.

## Test Coverage

### auto-view.js
- Throttle function timing behavior and edge cases
- Idle timeout decision logic (shouldAutoSwitch)
- Passive event detection and caching
- State management (interaction recording, timer management)
- Integration tests for initialization

## Debugging Tests

- **Browser Developer Console**: Check for JavaScript errors
- **QUnit UI**: Click on failed tests for detailed error messages  
- **Individual runners**: Use `test-{module}.html` for focused debugging
- **Async testing**: Use `assert.async()` for timing-dependent tests

## Notes

- All dependencies vendored locally (no internet required)
- Tests run in real browser environment 
- See `auto-view.js` implementation as reference example