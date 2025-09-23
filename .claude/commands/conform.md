# /conform Command

Automated code quality conformance - reviews and fixes Python files to match project coding standards with test safety verification.

## Usage
```
/conform <target>
```

Where `<target>` can be:
- A Python filename (e.g., `history_table_manager.py`)
- A class name (e.g., `HistoryTableManager`)
- A relative path (e.g., `hi/apps/common/history_table_manager.py`)
- A module path (e.g., `hi.apps.common.history_table_manager`)

## Examples
```
/conform HistoryTableManager
/conform history_table_manager.py
/conform hi/apps/entity/managers.py
/conform hi.apps.entity.managers
```

## What It Does

This command automates the process of bringing Python code into conformance with project coding standards while ensuring test coverage and safety:

1. **Verifies test coverage** - Ensures tests exist or creates them
2. **Runs initial tests** - Establishes baseline that tests pass
3. **Applies automated fixes** - Corrects coding standard violations
4. **Validates changes** - Ensures tests still pass after modifications
5. **Runs final linting** - Confirms no new issues introduced

## Process Flow

### Phase 1: Test Verification
- Locate the target Python file
- Search for associated test file(s)
- If no tests exist:
  - Launch test-engineer agent to create comprehensive tests
  - Verify new tests pass
- If tests exist:
  - Run tests to ensure they pass before changes

### Phase 2: Analysis
- Launch code-quality agent for comprehensive review
- Identify all coding standard violations
- Categorize issues by severity and type
- Create fix plan

### Phase 3: Automated Fixes
- Apply fixes for clear violations:
  - Remove obvious comments and docstrings
  - Fix alignment in method parameters, dataclasses, enums
  - Add missing explicit control flow statements
  - Organize imports properly
  - Preserve deliberate style choices (e.g., spaces in parentheses)

### Phase 4: Validation
- Run tests again to ensure no functional changes
- Run `make lint` to verify no new issues
- Provide summary of changes made
- Flag any issues that require manual review

## Quality Gates

The command will STOP if:
- No test file exists AND test creation fails
- Initial tests fail (won't modify code with failing tests)
- Tests fail after modifications (will revert changes)
- Linting introduces new errors (will attempt to fix or revert)

## Sub-Agent Coordination

### Phase 1 Agent: test-engineer (if needed)
- **Role**: Create comprehensive test coverage
- **Input**: Target file and class/module structure
- **Output**: Test file with appropriate coverage
- **Validation**: Tests must pass before proceeding

### Phase 2 Agent: code-quality
- **Role**: Analyze file and identify all violations
- **Input**: Full file path and content
- **Output**: Detailed list of violations with line numbers

### Supporting Operations:
- **Bash tool**: Run tests and linting
- **MultiEdit tool**: Apply batched fixes efficiently
- **Read tool**: Verify changes

## Expected Output

```
Conforming history_table_manager.py to project standards...

Step 1: Verifying test coverage
✓ Found test file: tests/test_history_table_manager.py
✓ Running tests... All 15 tests pass

Step 2: Analyzing code quality
Found 12 violations:
- 5 alignment issues
- 4 obvious comments
- 2 missing explicit returns
- 1 import organization issue

Step 3: Applying automated fixes
✓ Fixed method parameter alignment (lines 81-86)
✓ Fixed dataclass alignment (lines 54-58)
✓ Fixed enum alignment (lines 39-50)
✓ Removed obvious docstrings (lines 37, 188-190, 194-196)
✓ Removed redundant comments (lines 56, 117, 132, 139, 152)
✓ Added explicit returns (lines 93, 186)
✓ Reorganized imports

Step 4: Validation
✓ Tests still pass (15/15)
✓ make lint: No violations

Successfully conformed history_table_manager.py to project standards.
12 issues fixed automatically, all tests still passing.
```

## Error Handling

- **No test file found**:
  - Automatically creates tests via test-engineer agent
  - If test creation fails, aborts the cleanup

- **Tests fail before changes**:
  - Aborts with message to fix tests first
  - Suggests using `/fixtests` command

- **Tests fail after changes**:
  - Automatically reverts all changes
  - Reports which changes caused test failures
  - Suggests manual review

- **Lint failures after fixes**:
  - Attempts secondary fixes
  - If still failing, reverts and reports

## Safety Features

1. **Test-First Approach**: Won't modify code without passing tests
2. **Incremental Changes**: Applies fixes in logical batches
3. **Automatic Rollback**: Reverts if tests fail after changes
4. **Change Validation**: Each change verified against tests
5. **Audit Trail**: Lists every change made with line numbers

## Important Notes

- **Preserves functionality** - Changes only syntax/style, never logic
- **Respects project preferences** - Maintains deliberate PEP8 deviations
- **Comments philosophy** - Removes only obviously redundant comments
- **Variable assignments** - Maintains named variables over inlining
- **Test coverage** - Ensures or creates tests before any modifications

## Limitations

- Works only with Python files in the project
- Cannot fix complex architectural issues
- Requires ability to run tests (proper environment setup)
- May not handle all edge cases in test discovery
- Does not modify third-party or system files

## Related Commands
- `/fixtests` - Fix failing tests before running conform
- `/review` - Code review without automatic fixes
- `/commit` - Commit changes after conformance
- `/test` - Run tests for a specific module
