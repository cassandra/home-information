---
allowed-tools: Bash, Read, Edit, Write, TodoWrite, Grep, Glob, Task
description: Implement a GitHub issue that has been picked up, stopping at PR-ready state
model: claude-sonnet-4-20250514
argument-hint: [issue-number]
---

Implement GitHub issue #$1 following our development standards from `docs/dev/workflow/workflow-guidelines.md`:

## Implementation Process for #$1

Execute focused implementation workflow for issue that has already been picked up:

1. **Use TodoWrite to plan implementation steps** - Track the complete implementation workflow
   - Read `docs/CLAUDE.md` for development philosophy and quality standards
   - Focus on well-factored solutions following existing patterns

2. **Validate prerequisites** - Ensure issue is ready for implementation:
   ```bash
   # Verify we're on the correct feature branch (not staging/master)
   git branch --show-current
   # Should show: feature/$1-* or bugfix/$1-* etc.

   # Verify clean working directory
   git status
   # Should show: "nothing to commit, working tree clean"

   # Verify branch is up to date with remote
   git pull
   ```
   **CRITICAL**: STOP if not on feature branch or if working directory is not clean

3. **Read issue context** - Understand requirements completely:
   ```bash
   # Read the full issue including all comments
   gh issue view $1
   ```
   - Understand the problem statement and acceptance criteria
   - Review any discussion or clarifications in comments
   - Identify any specific implementation guidance provided

4. **Domain analysis and implementation strategy** - Determine implementation approach:

   **Read `.claude/agents/general-purpose.md` and apply its investigation approach to:**
   - **Identify domains involved**: Backend, Frontend, Integration, Domain Logic, etc.
   - **Assess scope and complexity**: Single domain vs. cross-cutting concerns
   - **Plan specialist engagement**: Clear domain boundaries vs. ambiguous work

   **Implementation approach decision**:
   - **FOR CLEAR DOMAIN WORK**: Use Task tool with appropriate specialist agent:
     - `backend-dev`: Django models, views, managers, database changes
     - `frontend-dev`: Templates, JavaScript, CSS, UI components
     - `integration-dev`: External APIs, data sync, third-party integrations
     - `domain-expert`: Business logic, entity relationships, domain rules

   - **FOR AMBIGUOUS/MIXED WORK**: Implement directly following general-purpose principles:
     - Apply cross-domain search and discovery patterns from general-purpose agent
     - Use broad codebase exploration techniques
     - Follow existing patterns and conventions discovered through investigation
     - Cast wide net first, then narrow focus based on findings

5. **Implementation phase** - Execute the planned approach:
   - **If using specialist agents**: Provide clear context and focus areas to the specialist
   - **If implementing directly**: Follow general-purpose investigation patterns and cross-domain awareness
   - **Always**: Follow existing code patterns and conventions
   - **Always**: Implement solution incrementally with frequent validation
   - **Always**: Add appropriate tests if required

6. **Mandatory code review phase** - Ensure quality and compliance:

   **Always use Task tool with these agents for code review**:
   - **code-quality agent**: Review architecture, patterns, maintainability, coding standards
   - **test-engineer agent**: Review test coverage, testing patterns, quality assurance

   **Conditionally use based on implementation scope**:
   - **backend-dev agent**: If Django models, views, or backend logic was modified
   - **frontend-dev agent**: If templates, JavaScript, CSS, or UI components were modified
   - **integration-dev agent**: If external APIs or integration services were modified
   - **domain-expert agent**: If business logic or domain rules were implemented

   **Review criteria**: All review agents must approve before proceeding to push

7. **Quality assurance** - Ensure PR-ready code quality:
   ```bash
   # Run full test suite (must pass)
   make test

   # Run code quality checks (must pass with no output)
   make lint
   ```
   **CRITICAL**: Fix any test failures or linting issues before proceeding

8. **Final validation** - Verify implementation completeness:
   - Review changes against issue requirements
   - Ensure all acceptance criteria are met
   - Verify no unrelated changes were introduced
   - Confirm solution follows project patterns
   - Verify all code review feedback has been addressed

9. **Push implementation** - Make code available for review:
   ```bash
   # Add all relevant changes
   git add .

   # Create descriptive commit message following our standards
   git commit -m "[Concise description of what was implemented]"

   # Push to remote feature branch
   git push origin
   ```

10. **Final status report** - Provide implementation summary:
    - Summarize what was implemented and approach taken
    - Note any key files or components modified
    - Highlight important implementation decisions
    - Report which agents were used and their feedback
    - Confirm all tests pass and code is PR-ready
    - **Instruct user to run `/pr` command to create pull request**

**Critical requirements:**
- Follow exact standards from `docs/dev/workflow/workflow-guidelines.md`
- Apply general-purpose agent investigation principles for domain analysis
- Use adaptive approach: specialist agents for clear domains, direct implementation for ambiguous work
- MANDATORY code review with code-quality and test-engineer agents
- MUST pass all tests, linting, and code review before completion
- NO PR creation - stop at PR-ready state
- Provide clear handoff to `/pr` command

**Prerequisites:**
- Issue #$1 must have been picked up with `/pickup` command
- Feature branch must already exist and be checked out
- Investigation and planning should already be complete

**Issue to implement:** #$1

**IMPORTANT**: This command stops before PR creation. After completion, user should review the implementation and run `/pr "Title"` to create the pull request.

Begin implementation process now.