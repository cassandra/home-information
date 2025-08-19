<img src="../../src/hi/static/img/hi-logo-w-tagline-197x96.png" alt="Home Information Logo" width="128">

# Development Guidelines

## Code Organization and Conventions

### Directories

#### Top-level Directory

- `src`: application source code (see below).
- `deploy`: helper scripts and files for deploying and setting up the application.
- `package`: extra items that need to be packaged up to support running the application in Docker.
- `Makefile`: provides convenience wrappers around command for building, packaging and running.
- `docs`: all documentation that suitable to be in markdown files.

#### The `src` Directory

- `hi`: entry point urls/views and some app-wide helper classes.
- `hi/templates`: For top-level views and app-wide common base templates.
- `hi/apps/${APPNAME}`: For normal application modules.
- `hi/apps/${APPNAME}/edit`: For normal application modules.
- `hi/apps/`: For normal application modules.
- `hi/integrations`: Code for dealing with integration not related to a specific integration.
- `hi/services/${SERVICENAME}`: Code for a particular integration. See the [Integrations Page](Integrations.md).
- `hi/simulator`: The code for the separate simulator helper app. See the [Simulator Page](Simulator.md).
- `hi/settings`: Django settings, including runtime population from environment variables.
- `hi/requirements`: Python package dependencies.
- `custom`: Custom user model and other general customizations.
- `bin`: Helper scripts needed with the code to run inside a Docker container.

### App Module Structure

- `enums.py`: For enums related to the module.
- `models.py`: For Django ORM models (by Django conventions).
- `transient_models.py`: For (small-ish) non-ORM models that are not persisted.
- `urls.py` - When module provides views.
- `views.py` - Main views for module.
- `views_mixin.py` - If there is common view functions needs.
- `forms.py` - If any Django forms are using in views.
- `${NAME}_manager.py` - If there is internal, persistent data the module provides, a singleton manager class is used.
- `settings.py`: If app wants to provide user-controllable settings.
- `monitors.py`: If app module needs a periodic background process.
- `templates/${APPNAME}`: The apps templates. Also see the [Templates Page](Templates.md).
- `apps.py`: Django-required module definition.
- `tests/test_${NAME}`: Unit tests for the module (by Django conventions).
- `admin.py`: For adding to Django admin console (by Django conventions).

If a module provides views or functionality that is only applicable to edit mode, then an `edit` subdirectory is used with the same structure, e.g., 

- `edit/urls.py` - URLs if module provides edit-only views.
- `edit/views.py` - Edit-only views for module.
- etc.

## Coding Style

### Flake8 Configurations

The project uses two different flake8 configurations for different purposes:

#### Development Configuration (`.flake8`)
Our preferred style for daily development work. The project tries to adhere to PEP8 but we strongly disagree with the broadly accepted coding guidelines around spaces. Spaces are great visual delimiters and greatly enhance readability. The whitespace deviations we make to PEP8 are shown in this Flake8 config file (`ignore`).

``` shell
[flake8]
max-line-length = 110

# Things I disable:
#
# E129 - visually indented line with same indent as next logical line
# D203 -
# E201 - whitespace after brackets
# E202 - whitespace before brackets
# E203 -
# E221 - multiple spaces before operator
# E231 - 
# E251 - unexpeced whitespace around keyword parameters
# W293 - blank line contains whitespace
# W291 - white space at end of line
# W391 - blank line at end of file
# W503 - line break before binary operator

ignore = E129,D203,E201,E202,E203,E221,E231,E251,W293,W291,W391,W503
```

#### CI Configuration (`.flake8-ci`)
**Hard requirement** for pull request approval. GitHub uses this configuration to enforce code quality standards and will block PR merging if linting fails.

**Before submitting any PR**, you must run: `flake8 --config=src/.flake8-ci src/` and ensure it passes with no violations.

### Generated Code Standards

All generated code (including AI-generated code) must comply with the `.flake8-ci` configuration rules. Common issues to avoid:

1. **Final Newlines**: All files must end with a single newline character
2. **Unused Imports**: Remove all unused import statements
3. **Unused Variables**: Remove or prefix unused variables with underscore (`_variable`)
4. **Line Continuation**: Proper indentation for multi-line statements following PEP 8
5. **Line Length**: Respect maximum line length limits defined in `.flake8-ci`

### Control Flow Statements
- Always include explicit `continue` statements in loops, even when not syntactically required
- Always include explicit `return` statements in functions, even when not syntactically required
- This improves code readability and makes control flow intentions explicit

### Operator Spacing
- Use spaces around assignment operators and most other operators in expressions
- Examples: `x = y + z`, `result += value`, `if count == 0`, `total -= amount`
- Exception: Don't add spaces in function keyword arguments (`func(x=y)`) or type annotations (`x: int = 5`)

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

def simple_function():
    print("Hello world")
    return  # Explicit return even for void functions
```

### General Guidelines
- Follow existing code patterns and conventions in the codebase
- Use descriptive variable and function names
- Maintain consistency with Django and Python best practices
- **Boolean expressions**: When assigning or returning boolean values, wrap expressions in `bool()` to make intent explicit and improve readability:
  ```python
  # Good - explicit boolean conversion
  is_active = bool(user.last_login)
  in_modal_context = bool(request.POST.get('context') == 'modal')
  
  # Avoid - implicit boolean conversion
  is_active = user.last_login
  in_modal_context = request.POST.get('context') == 'modal'
  ```

## Testing Conventions

See [Testing Guidelines](Testing.md) for comprehensive testing patterns, conventions, and best practices.

## Complex Issue Implementation Strategy

When tackling issues that involve multiple aspects, trade-offs, or significant complexity, use this proven multi-phase approach:

### Core Methodology

1. **Analyze and Break Down**: Identify distinct phases or approaches
   - Phase 1: Simple, reliable solution that fully addresses the core issue
   - Phase 2+: Advanced optimizations, UX improvements, or edge cases

2. **Implement Incrementally**: Complete phases sequentially
   - Complete Phase 1 first - ensure the bug/issue is FULLY RESOLVED
   - Commit and push Phase 1 (but do not create PR yet)
   - Validate approach before proceeding to optimizations
   - Wait for feedback before proceeding to Phase 2

3. **Communication and Review**: Natural checkpoints for feedback
   - Post investigation findings and phase breakdown to GitHub issue
   - After each phase, update issue with implementation details
   - Only create PR when all phases are complete or explicitly requested
   - Enable course correction if needed

4. **Benefits of This Approach**:
   - Allows for early validation of approach
   - Enables course correction if needed
   - Provides natural checkpoints for review
   - Ensures core functionality before optimizations
   - Independent value delivery per phase

### Key Principles

1. **Always solve the core issue first** - Phase 1 must fully resolve the bug
2. **Incremental value delivery** - Each phase should be independently valuable
3. **Natural stopping points** - Complete phases are good moments for review
4. **No PR until complete** - Unless explicitly asked, wait until all phases done

### Case Study: Issue #30 - EntityType Icon Updates

- **Phase 1**: Simple page refresh on EntityType change (reliable, addresses core issue)
- **Phase 2**: Smart transitions with database management (UX optimization)

This strategy proved highly effective by providing early validation of the approach, allowing for feedback before complex optimizations, ensuring the core bug was fixed before adding enhancements, and creating natural checkpoints for code review.

## Commit Messages

See [Workflow Guidelines](Workflow.md) for commit message standards and branching conventions.

## PR Descriptions

See [Workflow Guidelines](Workflow.md) for pull request templates and review process.

## Documentation

_TBD_
