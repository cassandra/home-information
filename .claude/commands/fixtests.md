---
allowed-tools: Bash, Read, TodoWrite, Grep, Glob, Task
description: Systematic test failure analysis and remediation
model: claude-3-5-sonnet-20241022
argument-hint:
---

Systematic test failure analysis and remediation:

## Test Remediation Process

Focus on fixing failing tests to achieve full test suite success:

1. **Use TodoWrite to plan test remediation workflow** - Track systematic test fixing

2. **Review project documentation** - Understand standards and guidelines:
   - Read `docs/CLAUDE.md` for AI escalation patterns and quality standards
   - Read `docs/dev/shared/coding-standards.md` for coding standards
   - Read `docs/dev/testing/testing-guidelines.md` for testing best practices
   - Reference `docs/dev/testing/testing-lessons-learned.md` for complex cases

3. **Run full test suite** - Identify all current failures:
   ```bash
   make test
   ```
   Capture complete output to understand scope and nature of failures

4. **Categorize test failures** - Organize by type and complexity:
   - **Syntax/Import errors** - Basic code issues preventing test execution
   - **Logic failures** - Tests failing due to incorrect assertions or logic
   - **Configuration issues** - Environment, settings, or dependency problems
   - **Integration failures** - Database, external service, or component integration issues
   - **Flaky tests** - Intermittent failures due to timing or state issues
   - **Outdated tests** - Tests that no longer match current implementation

5. **Assess test value** - Evaluate each failing test:
   - **High value** - Critical functionality, good coverage, well-written
   - **Medium value** - Useful but could be improved
   - **Low value** - Poor quality, redundant, or testing implementation details
   - **Questionable value** - May be candidates for removal or rewriting

6. **Create prioritized remediation plan** - Strategic fixing order:
   - **Priority 1** - Syntax/import errors (blocking other tests)
   - **Priority 2** - High-value logic and integration failures
   - **Priority 3** - Medium-value test failures
   - **Priority 4** - Configuration and environment issues
   - **Priority 5** - Flaky test stabilization
   - **Priority 6** - Low-value test assessment (fix, rewrite, or discuss removal)

7. **Use specialized test analysis** - Get expert assistance:
   - **Use Task tool with test-engineer agent** - Expert test analysis and fixing strategies
   - **Use Task tool with backend-dev agent** - Django test patterns and database issues
   - **Use Task tool with domain-expert agent** - Business logic test validation

8. **Execute systematic test fixing** - Follow prioritized plan:
   - Work through each priority level systematically
   - Fix tests according to testing guidelines and standards
   - **Apply 3-attempt rule** - If struggling with any test after 3 attempts, pause and escalate
   - Run tests frequently to verify fixes don't break other tests
   - Document complex fixes and reasoning

9. **Reference additional resources when needed** - For difficult cases:
   - Search `docs/dev/testing/testing-lessons-learned.md` for related guidance
   - Look for patterns and solutions to similar test issues
   - Apply lessons learned from previous test remediation efforts

10. **Validate test quality** - Ensure fixes maintain standards:
    - No compromising test coverage or quality
    - Follow testing best practices from guidelines
    - Ensure tests are maintainable and valuable
    - Verify fixed tests provide meaningful assertions

11. **Handle low-value test decisions** - Discuss removal candidates:
    - **Before removing any test** - Present case for removal with rationale
    - Consider rewriting instead of removal if test covers important functionality
    - Ensure removal doesn't create coverage gaps
    - Document decisions and reasoning

12. **Final validation** - Confirm complete success:
    ```bash
    make test
    ```
    Verify all tests pass with no failures or errors

**Test Remediation Standards:**
- Maintain or improve test coverage
- Follow testing guidelines and best practices
- No compromising test quality to make tests pass
- Systematic approach with clear prioritization
- Escalate after 3 attempts on any single test

**Escalation Pattern:**
- If struggling with any test after 3 attempts, pause and report
- Request human assistance for complex or unclear test failures
- Don't spend excessive time on single test without guidance

**Key Principles:**
- Quality over speed - proper fixes that maintain test value
- Systematic approach - work through priorities methodically
- Standards compliance - follow established testing guidelines
- No coverage compromise - removing tests must be explicitly discussed

Begin systematic test failure analysis and remediation now.