# Code Commenting Guidelines

## Core Philosophy

We generally want to avoid over-commenting and let the code variable/method naming be clear on the intent. We believe in the philosophy: **"Before adding a comment, ask yourself how the code can be changed to make the comment unnecessary."**

## Guidelines

### ✅ GOOD Comments - What TO Include

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

### ❌ BAD Comments - What NOT To Include

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

### 🤔 Consider Alternatives

1. **Method names over behavioral comments**
   - Instead of commenting behavior, consider renaming methods to be self-documenting
   - Example: Comment about "always attempt regardless of mode/view" might be better as a more descriptive method name

## Examples from Entity Module Review

### Keep These Comments:
- `entity/enums.py:104` - "Single source of truth for position vs path classification"
- `entity/entity_pairing_manager.py:20-23` - Multi-line explanation of delegation concept  
- `entity/enums.py:160-163` - Explains why specific types exist vs general types
- `location/models.py:224-226` - LocationItem interface concept
- `alert/alert_manager.py:40-56` - Multi-step process breakdown
- `alert/alarm.py:25-27` - Data structure behavior explanation
- `weather/monitors.py:47-50` - Rate-limiting protection rationale
- `weather/wmo_units.py:838-841` - Pint library limitation workarounds
- `weather/aggregated_weather_data.py:26-32` - Comprehensive class documentation
- `zoneminder/monitors.py:99-110` - Complex temporal logic explanation
- `zoneminder/monitors.py:166-171` - Critical edge case reasoning
- `zm_manager.py:22` - External library frustration ("ugh") with context

### Remove/Improve These:
- `entity/views.py:37` - "Store original entity_type_str to detect changes"
- `entity/views.py:48` - "Track EntityType change and response needed after transaction"
- `entity/tests/test_views.py:66-72` - Long explanations of why tests were removed
- `location/edit/views.py:171` - "Recreate to preserve 'max' to show new form" - Cryptic reference
- `location/location_manager.py:169` - "Only collect position OR path based on EntityType, not both" - States obvious
- `alert/alert_queue.py:62` - "Use queue_insertion_datetime instead of start_datetime" - States what code does
- Test files with "Phase 3/Phase 4" development context comments
- `weather/daily_weather_tracker.py:39,42,45` - Simple labels that state the obvious
- `zoneminder/integration.py:65-66` - Commented-out logic that creates confusion

### Borderline (Keep for now):
- `entity/views.py:87` - "Always attempt advanced transition handling regardless of mode/view" - Conveys important business rule despite unclear phrasing
- Enum inline comments - Generally add semantic value about domain purpose

## Special Cases

### TRACE Pattern (Accepted)
- `TRACE = False # for debugging` is an accepted pattern
- Addresses Python logging limitation (lacks TRACE level below DEBUG)
- Used for very frequent or large-volume debug output
- Keep the comment to explain purpose for those unfamiliar with the pattern

## Summary

Comments should explain the **why** not the **what**. Good comments document:
- Non-obvious design decisions
- Complex business logic
- External API/library quirks and workarounds
- Time-based complexities
- Bug fixes that prevent regression

Avoid comments that:
- State what the code obviously does
- Contain development artifacts or work-stream context
- Leave commented-out code (creates confusion)
- Explain what better naming could clarify

When in doubt, ask: "Can I change the code to make this comment unnecessary?"