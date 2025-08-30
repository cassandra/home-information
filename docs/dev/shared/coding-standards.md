# Coding Standards

## Code Organization and Conventions

### Directory Structure

#### Top-level Directory
- `src`: application source code
- `deploy`: helper scripts and files for deploying and setting up the application
- `package`: extra items that need to be packaged up to support running the application in Docker
- `Makefile`: provides convenience wrappers around commands for building, packaging and running
- `docs`: all documentation suitable to be in markdown files

#### The `src` Directory
- `hi`: entry point urls/views and some app-wide helper classes
- `hi/templates`: For top-level views and app-wide common base templates
- `hi/apps/${APPNAME}`: For normal application modules
- `hi/integrations`: Code for dealing with integration not related to a specific integration
- `hi/services/${SERVICENAME}`: Code for a particular integration
- `hi/simulator`: The code for the separate simulator helper app
- `hi/settings`: Django settings, including runtime population from environment variables
- `hi/requirements`: Python package dependencies
- `custom`: Custom user model and other general customizations
- `bin`: Helper scripts needed with the code to run inside a Docker container

## Coding Style

### No "magic" strings

We do not use "magic" or hard-coded strings when needing multiple references. Any string that need to be used in two or more places is a risk of them being mismatched. This includes, but is not limited to:

- All references to urls *must* use the Django url name and reverse() to construct.
- Use enum values or constants/class variables to act as coordination point and provide some amount of compiler help in identifying mismatches. Most needed strings will already have a LabeledEnum type defined, but we should add new ones as needed. See "Enums" in [Back End Guidelines](../backend/backend-guidelines.md).
- All DOM ids and class strings that are shared between client and server must adhere to our `DIVID` pattern. See "Client-Server Namespace Sharing" in [Front End Guidelines](../frontend/frontend-guidelines.md).

### Type Hints

We add type hints to dataclass fields, method parameters and method return values.
We do not add type hints to locally declared method variables.


### Method parameter formatting

zzz

zzz wrapping bool()



### Flake8 Configurations

The project uses two different flake8 configurations:

#### Development Configuration (`.flake8`)
Our preferred style for daily development work, with specific whitespace deviations from PEP8 for enhanced readability:

```ini
[flake8]
max-line-length = 110
# Disabled for enhanced readability with spaces:
# E129, E201, E202, E203, E221, E231, E251, W293, W291, W391, W503
ignore = E129,D203,E201,E202,E203,E221,E231,E251,W293,W291,W391,W503
```

#### CI Configuration (`.flake8-ci`)
**Hard requirement** for pull request approval. GitHub Actions enforces these standards and blocks PR merging if violations exist.

**Before submitting any PR**, you must run: `flake8 --config=src/.flake8-ci src/` and ensure it passes with no violations.

### Generated Code Standards

### Linting

All generated code (including AI-generated code) must comply with `.flake8-ci` configuration:

1. **Final Newlines**: All files must end with a single newline character
2. **Unused Imports**: Remove all unused import statements
3. **Unused Variables**: Remove or prefix unused variables with underscore (`_variable`)
4. **Line Continuation**: Proper indentation for multi-line statements following PEP 8
5. **Line Length**: Respect maximum line length limits defined in `.flake8-ci`

### Control Flow Statements
- Always include explicit `continue` statements in loops
- Always include explicit `return` statements in functions
- This improves code readability and makes control flow intentions explicit

Example:
```python
def process_items(items):
    results = []
    for item in items:
        if not item.valid:
            continue  # Explicit continue for invalid items
        
        if item.needs_processing:
            result = process(item)
            results.append(result)
            continue  # Explicit continue after processing
        
        # Handle non-processing case
        results.append(item.default_value)
        continue  # Explicit continue at end of loop
    
    return results  # Explicit return at end of function
```

### Operator Spacing
- Use spaces around assignment operators and most other operators in expressions
- Examples: `x = y + z`, `result += value`, `if count == 0`
- Exception: Don't add spaces in function keyword arguments (`func(x=y)`) or type annotations

### Boolean Expressions
When assigning or returning boolean values, wrap expressions in `bool()` to make intent explicit:

```python
# Good - explicit boolean conversion
is_active = bool(user.last_login)
in_modal_context = bool(request.POST.get('context') == 'modal')

# Avoid - implicit boolean conversion
is_active = user.last_login
in_modal_context = request.POST.get('context') == 'modal'
```


## Related Documentation
- Testing standards: [Testing Guidelines](../testing/testing-guidelines.md)
- Backend patterns: [Backend Guidelines](../backend/backend-guidelines.md)
- Frontend standards: [Frontend Guidelines](../frontend/frontend-guidelines.md)
- Workflow and commits: [Workflow Guidelines](../workflow/workflow-guidelines.md)

### Commenting

- We avoid over-commenting and let the code variable/method naming be clear on the intent.
- We believe in the philosophy: "Before add a comment, ask yourself how the code can be changed to make this comment unnecessary."
- Do not add comments that are not timeless and refer to work in progress or future work. i.e., it must make sense for future readers of the code.
