# Coding Standards

## Code Conventions Checklist

Checklists for writing and reviewing code.

**General**:
- [ ] Code does not use hard-coded "magic" strings.
- [ ] Code does no use any hard-coded "magic" numbers.
- [ ] All comments add value and follow our commenting guidelines.
- [ ] No urls appear as hard-coded path and all use Django url names and `reverse()`.
- [ ] There no .flake8 linting violations.
- [ ] The file ends with a newline
- [ ] All new files follow the project structure's name and location conventions.
- [ ] There are no Emoji's in any code, templates or documentation.

**Imports**:
- [ ] All module imports are at the top of the file.
- [ ] Imports are grouped logically: system/pip, django, project, apps then module local.
- [ ] Imports have one line space between groups.
- [ ] Within a group, imports are sorted alphabetically
- [ ] No module relies on indirect (hidden) imports
- [ ] There are no unused imports

**Method Declarations**:
- [ ] All methods uses type hints for their parameters and return values.
- [ ] All method definition with more than two arguments use one line per argunment.
- [ ] All multi-line method signatures have all their types and default values aligned.
- [ ] No methods return position-dependent tuples.

**Class Declarations**:
- [ ] All dataclass definitions have all their types and default values aligned.
- [ ] All enum definitions have all their types and default values aligned.
- [ ] Are enums subclass LabeledEnum

**Method Calling**:
- [ ] All method calls use named parameters.
- [ ] All metghod calls with more than two argumants use one line per argument.
- [ ] All multi-line method calls use a comma after last item.
- [ ] Spaces surrounding all equals ("=") signs when passing parameters to methods.

**Expressions**:
- [ ] All boolean assignments to conditional clauses are wrapped in `bool()`.
- [ ] All loops end with an explicit  `continue` or a `return`.
- [ ] All methods end with an explicit `return` or a `raise`?
- [ ] All multi-line arrays, sets, dictionaries use a comma after last item.
- [ ] Compound/complex conditional statements use explicit delimiting parentheses.
- [ ] Single quote are used for all strings in Python code.
- [ ] All multi-line arrays, dictionaries and sets use a comma after last item.

**Views**:
- [ ] All url paths components follow our standard ordering conventions.
- [ ] All url Django names follow our standard naming conventions
- [ ] All view names match url names (except for casing and underlining).
- [ ] ALl views raise exceptions for common error conditions. (Let middleware handle it.)

**Templates**:
- [ ] Template names referenced in views closely match the view names that use them.
- [ ] No templates have in-line Javascript.
- [ ] No templates have in-line CSS.
- [ ] Templates appear in a subdirectory matching their purpose: modals, panes, pages.
- [ ] Template tags `load` statments near the top of the file.

**Comments**:
- [ ] No comments that state what is obvious from the naming and typing and context.
- [ ] No method docstrings that simply restate what the method name already says.
- [ ] No inline comments that describe what the code is doing (vs why).
- [ ] No comments that refer to the past, future or current work in progress.

## Code Conventions Details

### No "magic" strings

We do not use "magic" or hard-coded strings when needing multiple references. Any string that need to be used in two or more places is a risk of them being mismatched. This includes, but is not limited to:

All DOM ids and class strings that are shared between client and server must adhere to our `DIVID` pattern. See "Client-Server Namespace Sharing" in [Front End Guidelines](../frontend/frontend-guidelines.md).

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

**Good Examples**:

```
    def set_entity( self, entity_id : int ) -> EntityPath:

    def set_entity_order( self, entity_id : int, rank : int ) -> EntityPath:

    def set_entity_path( self,
                         entity_id     : int,
                         location      : Location,
                         svg_path_str  : str        ) -> EntityPath:
```

**Bad Examples**:

```
    def set_entity_type( self, entity_id : int, entity_type : EntityType ) -> EntityPath:

    def set_entity_path( self,
                         entity_id : int,
                         location : Location,
                         svg_path_str: str ) -> EntityPath:

    def set_entity_path( self, entity_id : int,
                         location : Location, svg_path_str: str ) -> EntityPath:
```

### Variable Assignment vs Inlining

We prefer explicit variable assignment over inlining function calls. This is not about minimizing lines of code - it's about readability and debuggability.

**Good** - Named intermediate values
```python
table_name = self.queryset.model._meta.db_table
logger.debug( f"Processing table: {table_name}" )

cutoff_date = datetimeproxy.now() - timedelta( days=30 )
old_records = queryset.filter( created__lt=cutoff_date )
```

**Bad** - Inlined function calls
```python
logger.debug( f"Processing table: {self.queryset.model._meta.db_table}" )

old_records = queryset.filter(
    created__lt=datetimeproxy.now() - timedelta( days=30 )
)
```

Benefits of variable assignment:
- Provides semantic naming that clarifies intent
- Easier to debug (can inspect intermediate values)
- Improves readability by breaking complex expressions
- Allows reuse without recalculation

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

**Good**:
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

**Bad**:
```
    if hass_state.domain == HassApi.SWITCH_DOMAIN and HassApi.LIGHT_DOMAIN == 'foo':
        pass
```

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

### Parentheses Spacing (Deliberate PEP8 Deviation)
- **We prefer spaces inside parentheses for enhanced readability**
- This is a deliberate deviation from PEP8 standards (E201, E202)
- Examples:
  - Good: `if ( condition ):`
  - Good: `my_function( param1, param2 )`
  - Good: `result = calculate( x + y )`
- This applies to all parentheses: function calls, conditionals, expressions
- Rationale: Extra spacing improves readability by visually separating content from delimiters

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

### Linting: Flake8 Configurations

The project uses two different flake8 configurations:
- Development Configuration (`src/.flake8`) : Our preferred style for daily development work, with specific whitespace deviations from PEP8 for enhanced readability:
  - **E201, E202**: We use spaces inside parentheses for better visual separation
  - **E221**: We align operators and values in multi-line declarations
  - **E251**: We use spaces around keyword parameters for consistency
  - **Note**: These are deliberate choices for improved code readability, not oversights
- CI Configuration (`src/.flake8-ci`): GitHub Actions enforces these standards and blocks PR merging if violations exist.

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

### Examples

#### GOOD Comments - What TO Include

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

#### BAD Comments - What NOT To Include

1. **Method docstrings that restate the obvious**
   - Bad: `"""Get the total number of records in the history table."""` for `_get_record_count()` in a HistoryTableManager class
   - Bad: `"""Delete records with the given IDs."""` for `_delete_records( ids )`
   - Bad: `"""Types of cleanup operation results."""` for an enum called CleanupResultType
   - The method/class name + parameters + return type already convey this information
   - Exception: Public API methods may need docstrings for documentation generation

2. **Avoid commenting obvious variable purposes**
   - Bad: `# Store original entity_type_str to detect changes`
   - Bad: `# Human-readable message for health status` when field is named `reason: str`
   - The variable name and type should make this clear

3. **Remove work-stream artifacts**
   - Bad: Comments explaining why tests were removed or referencing specific issues
   - Comments should be timeless, not tied to particular development contexts

4. **Redundant descriptions of clear code**
   - Bad: `# Track EntityType change and response needed after transaction`
   - Bad: `# Check if we're over the total record limit` before `if total_count <= self.max_records_limit:`
   - When variable names and conditionals already convey this information

5. **Cryptic references**
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

## Related Documentation
- Testing standards: [Testing Guidelines](../testing/testing-guidelines.md)
- Backend patterns: [Backend Guidelines](../backend/backend-guidelines.md)
- Frontend standards: [Frontend Guidelines](../frontend/frontend-guidelines.md)
- Workflow and commits: [Workflow Guidelines](../workflow/workflow-guidelines.md)



