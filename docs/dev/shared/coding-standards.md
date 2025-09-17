# Coding Standards

## Code Conventions Checklist

Use these checklists when writing code and when reviewing code.

The answers to all of the questions in this checklist should be "no".
- [ ] Is the code using hard-coded "magic" strings?
- [ ] Are any comments stating the obvious given the naming and typing?
- [ ] Do any method return position-dependent tuples?
- [ ] Are there any hard-coded "magic" numbers?
- [ ] Are the compound/complex conditional statements without using explicit parentheses?
- [ ] Are double quoted strings used where single quotes could be used?
- [ ] Does any method definition with more than two arguments appear on one line?
- [ ] Are there any .flake8 linting violations?
- [ ] Do multi-line definitions omit the last commas when it can be provided?
- [ ] Are there any urls using a string path instead of a Django url name?
- [ ] Do templates have in-line Javascript
- [ ] Do templates have in-line CSS

The answers to all of the questions in this checklist should be "yes".
- [ ] Are all module imports at the top?
- [ ] All all methods using types for their parameters and return values?
- [ ] Are all function calls using named parameters?
- [ ] Are the spaces surrounding the equals ("=") sign when pasing parameters to methods?
- [ ] Does the file end with a newline?
- [ ] Do all multi-line method signatures have all their types and default values aligned?
- [ ] Do dataclass definitions have all their types and default values aligned?
- [ ] Do enum definitions have all their types and default values aligned?
- [ ] Are the spaces between logical groupings of imports (system/pip, django, project, local)?
- [ ] Do url paths follow our standard ordering convention?
- [ ] Do url names follow our standard naming convention?
- [ ] Do view names match url names?
- [ ] Do template names match view names?
- [ ] Do views raise exceptions for common error conditions? (Letting middleware handle it.)
- [ ] Are new enums subclassing LabeledEnum?
- [ ] Are boolean assignments to conditional clauses wrapped in `bool()`?
- [ ] Do all loops end with a `continue` or a `return`?
- [ ] Do all methods  end with a `return` or a `raise`?

## Code Conventions Details

### No "magic" strings

We do not use "magic" or hard-coded strings when needing multiple references. Any string that need to be used in two or more places is a risk of them being mismatched. This includes, but is not limited to:

- All references to urls *must* use the Django url name and reverse() to construct.
- Use enum values or constants/class variables to act as coordination point and provide some amount of compiler help in identifying mismatches. Most needed strings will already have a LabeledEnum type defined, but we should add new ones as needed. See "Enums" in [Back End Guidelines](../backend/backend-guidelines.md).
- All DOM ids and class strings that are shared between client and server must adhere to our `DIVID` pattern. See "Client-Server Namespace Sharing" in [Front End Guidelines](../frontend/frontend-guidelines.md).

### Type Hints

- We add type hints to dataclass fields, method parameters and method return values.
- We do not add type hints to locally declared method variables.
- Some allowed, but not required exceptions:
  - The `request` parameter when appearing in a Django view class.
  - Single parameter methods where the method name or parameter name makes its type unambiguous.

### Method Parameter Formatting

For readability, besides adding type hints to method parameters, we adhere to the following formatting conventions:
- For methods with a single parameter, or parameters of native types, they can appear in one line with the method name.
- If more than one parameter and app-defined types, then use a multiple line declaration.
- For methods with three or more parameters, we use one line per parameter and align the type names.

**Good Examples**

```
    def set_entity( self, entity_id : int ) -> EntityPath:

    def set_entity_order( self, entity_id : int, rank : int ) -> EntityPath:

    def set_entity_path( self,
                         entity_id     : int,
                         location      : Location,
                         svg_path_str  : str        ) -> EntityPath:
```

**Bad Examples**

```
    def set_entity_type( self, entity_id : int, entity_type : EntityType ) -> EntityPath:

    def set_entity_path( self,
                         entity_id : int,
                         location : Location,
                         svg_path_str: str ) -> EntityPath:

    def set_entity_path( self, entity_id : int,
                         location : Location, svg_path_str: str ) -> EntityPath:
```

### Explicit Booleans

We prefer to wrap all expression that evaluate to a boolean in `bool()` to make it explicit what type we are expecting:

**Good**
```
   my_variable = bool( len(my_list) > 4 )
```

**Bad***
```
   my_variable = len(my_list) == 4 
```

### Complex Boolean Expressions

- For boolean clauses and conditionals where there are multiple clauses, we prefer to explicitly enclose each clause with parentheses in order to make the intention clear.
- We do not rely on the user having a deep understanding of the compiler's ordeer of precedence.
- We use one line per clause unless the combined clauses are very short and obvious.
- Single boolean typed variables or methods that return a boolean do not need paretheses.

**Good**
```
    if is_editing and location_view:
        pass
                
    if (( hass_state.domain == HassApi.SWITCH_DOMAIN )
          and ( HassApi.LIGHT_DOMAIN in prefixes_seen )):
        pass
                
    if ( HassApi.BINARY_SENSOR_DOMAIN in domain_set
         and device_class_set.intersection( HassApi.OPEN_CLOSE_DEVICE_CLASS_SET )):
        pass

   
```

**Bad***
```
    if hass_state.domain == HassApi.SWITCH_DOMAIN and HassApi.LIGHT_DOMAIN == 'foo':
        pass
```

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

## Commenting Guidelines

- We avoid over-commenting and let the code variable/method naming be clear on the intent.
- We believe in the philosophy: "Before add a comment, ask yourself how the code can be changed to make this comment unnecessary."
- Do not add comments that are not timeless and refer to work in progress or future work. i.e., it must make sense for future readers of the code.
- Comments should explain the **why** not the **what**. Good comments document:
  - Non-obvious design decisions
  - Complex business logic
  - External API/library quirks and workarounds
  - Time-based complexities
  - Bug fixes that prevent regression
- Avoid comments that:
  - State what the code obviously does
  - Contain development artifacts or work-stream context
  - Leave commented-out code (creates confusion)
  - Explain what better naming could clarify
- When in doubt, ask: "Can I change the code to make this comment unnecessary?"
  
### Special Cases

#### TRACE Pattern (Accepted)
- `TRACE = False # for debugging` is an accepted pattern
- Addresses Python logging limitation (lacks TRACE level below DEBUG)
- Used for very frequent or large-volume debug output
- Keep the comment to explain purpose for those unfamiliar with the pattern

### GOOD Comments - What TO Include

1. **Design rationale that is non-obvious**
   - Example: `# Single source of truth for position vs path classification`
   - Explains architectural decisions

2. **Complex domain logic explanations**
   - Example: Multi-line explanation of entity delegation concept
   - Business rules that aren't obvious from code structure

3. **Summarize complex or non-standard coding approaches**
   - When using unusual patterns or workarounds
   - Algorithm explanations that aren't obvious

4. **Design decision rationale**
   - Example: "The general types could be used for these, since all are just name-value pairs. However, by being more specific, we can provide more specific visual and processing"
   - Explains why one approach was chosen over alternatives

5. **Mathematical/geometric calculations**
   - Example: `'80.0,40.0', # top-left (100-20, 50-10)`
   - Coordinate calculations that are difficult to verify mentally
   - Especially valuable in test cases for validation

6. **Cross-file coordination notes**
   - Example: `# Match SvgItemFactory.NEW_PATH_RADIUS_PERCENT`
   - Important synchronization between related constants/values in different files

7. **Complex domain abstractions**
   - Example: Multi-line explanation of LocationItem interface concept
   - Abstract concepts that need implementation guidance

8. **Multi-step process/algorithm documentation**
   - Example: `alert_manager.py:40-56` - Breaks down the three distinct checks and explains why HTML is always returned
   - Complex workflows that need step-by-step explanation of the "why"

9. **External API/library limitations and workarounds**
   - Example: `wmo_units.py:838-841` - Documents Pint library limitations requiring unit mappings
   - Example: `zoneminder/monitors.py:81-87` - pyzm timezone parsing quirks
   - Critical for understanding why non-obvious code patterns exist
   - Brief expressions of frustration (e.g., "ugh") acceptable when documenting known pain points

10. **External service configuration rationale**
   - Example: `usno.py:59-62` - Documents API priority, rate limits, polling intervals
   - Explains constraints and decisions for external integrations

11. **Future extension points**
   - Example: `daily_weather_tracker.py:96-100` - "Future: Add other weather field tracking here"
   - Marks logical insertion points for anticipated features
   - Should be brief hints, not commented-out code blocks

12. **Temporal/timing complexity in APIs**
   - Example: `zoneminder/monitors.py:99-110` - Events as intervals vs points, open/closed handling
   - Example: `zoneminder/monitors.py:166-171` - Why polling time cannot advance
   - Critical for understanding time-based edge cases in external systems

13. **Bug fix documentation**
   - Example: `zoneminder/monitors.py:132-133` - "This fixes the core bug where..."
   - Documents what was broken and why the current approach fixes it
   - Helps prevent regression

### BAD Comments - What NOT To Include

1. **Avoid commenting obvious variable purposes**
   - Bad: `# Store original entity_type_str to detect changes`
   - The variable name should make this clear

2. **Remove work-stream artifacts**
   - Bad: Comments explaining why tests were removed or referencing specific issues
   - Comments should be timeless, not tied to particular development contexts

3. **Redundant descriptions of clear code**
   - Bad: `# Track EntityType change and response needed after transaction`
   - When variable names already convey this information

4. **Cryptic references**
   - Bad: `# Recreate to preserve "max" to show new form`
   - If unclear, either explain properly or remove

5. **Development phase/work-stream artifacts**
   - Bad: Comments explaining "Phase 3/Phase 4" development contexts
   - Bad: Explanations of why code was removed or changed
   - These belong in commit messages or PR descriptions, not in main branch code

6. **TODO comments (high bar to justify)**
   - Generally avoid TODOs in main branch
   - If important enough for TODO, create an issue and prioritize it
   - Only acceptable when there's a compelling reason not to address immediately
   - Must be specific and actionable, not vague intentions

7. **Commented-out code**
   - Bad: Dead code that's been disabled or replaced
   - Bad: Example implementations as large code blocks
   - Bad: Logic that looks like it might need uncommenting (e.g., `zoneminder/integration.py:65-66`)
   - If needed for future reference, create an issue instead
   - Exception: Very brief one-line hints at extension points (see "Future extension points" in good comments)
   - Commented code creates confusion about whether it should be active

### Consider Alternatives

1. **Method names over behavioral comments**
   - Instead of commenting behavior, consider renaming methods to be self-documenting
   - Example: Comment about "always attempt regardless of mode/view" might be better as a more descriptive method name


## Related Documentation
- Testing standards: [Testing Guidelines](../testing/testing-guidelines.md)
- Backend patterns: [Backend Guidelines](../backend/backend-guidelines.md)
- Frontend standards: [Frontend Guidelines](../frontend/frontend-guidelines.md)
- Workflow and commits: [Workflow Guidelines](../workflow/workflow-guidelines.md)



