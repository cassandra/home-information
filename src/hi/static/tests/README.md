# JavaScript Unit Tests

This directory contains unit tests for JavaScript modules in the Home Information application.

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

## Test Philosophy

Following the project's testing guidelines:

- **Focus on business logic**, not framework internals
- **Test actual behavior**, not implementation details
- **Mock only at system boundaries** (window, external APIs)
- **Avoid testing DOM manipulation** - jQuery handles this
- **Use real objects** when available, not mocks

## Test Coverage

Current test coverage includes:

### auto-view.js
- ✅ Throttle function timing behavior
- ✅ Idle timeout decision logic (shouldAutoSwitch)
- ✅ Passive event detection and caching
- ✅ State management (interaction recording, timer management)
- ✅ Integration tests for initialization

## Local-First Philosophy

All test dependencies are vendored locally to support offline development:
- QUnit framework files are stored in `/qunit/` directory
- No CDN dependencies required
- Tests can run completely offline

## Debugging Tests

1. **Browser Developer Console**: Check for JavaScript errors
2. **QUnit UI**: Click on failed tests for detailed error messages
3. **Add `console.log` statements**: Temporarily add logging in test code
4. **Use `assert.async()`**: For testing asynchronous behavior

## Future Improvements

- Add test coverage reporting
- Integrate with CI/CD pipeline
- Add visual regression tests for UI components
- Create test fixtures for complex data structures