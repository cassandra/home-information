# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Workflow for GitHub Issues

When working on GitHub issues, follow this development workflow:

1. **Read the GitHub issue and all its comments** - Understand the requirements, context, and any discussion

2. **Ensure you're on the latest staging branch** - MANDATORY step before any work:
   - If coming from a merged PR, run Post-PR Cleanup first (see step 10)
   - Switch to staging branch: `git checkout staging`
   - Pull latest changes: `git pull origin staging`
   - Verify you're on the correct branch: `git status`

3. **Investigate and plan the implementation** - MANDATORY step for all issues:
   - Assign the issue to yourself: `gh issue edit <issue-number> --add-assignee @me`
   - Research the codebase to understand current implementation  
   - Identify files, functions, and components that need changes
   - Consider edge cases, dependencies, and potential impacts
   - Plan the implementation approach and sequence of changes
   - **Post a comment on the GitHub issue** documenting:
     - Summary of investigation findings
     - Proposed implementation approach
     - Key files/components that will be modified
     - Any questions or concerns identified
   - **Wait for confirmation only if**:
     - You have critical questions that could affect the implementation
     - Important information is missing or unclear from the issue
     - Multiple solution approaches exist with no clear best choice
     - The proposed changes have significant architectural implications
   - Otherwise, proceed directly to implementation

3.5. **For Complex Issues - Apply Multi-Phase Strategy** (when applicable):
   - If issue involves multiple aspects, significant trade-offs, or substantial complexity, apply the multi-phase methodology from [Guidelines.md](dev/Guidelines.md#complex-issue-implementation-strategy)
   - Post phase breakdown to GitHub issue before starting implementation
   - Complete Phase 1 fully, commit and push (but don't create PR yet)
   - Update TodoWrite tool with phase completion status
   - Stop and report Phase 1 completion with summary
   - Wait for human feedback before proceeding to subsequent phases
   - Only create PR when all phases complete or explicitly requested

4. **Development environment check** - The virtual environment and necessary environment variables should be set before starting claude. If there is no virtual environment, this is an indication that the environment has not been properly set up. That means the unit test cannot run and code changes cannot be validated.  We shoudl stop the process and fix it.  There is no need to check ever time since this shoudl be rare, but if running tests is failing, that is a good thing to look for.

5. **Create a dev branch off the staging branch** - Use proper naming convention:
   - **Bug fixes**: `bugfix/##-description` (e.g., `bugfix/31-controller-modal-fix`)
   - **New features**: `feature/##-description` (e.g., `feature/45-weather-alerts`)
   - **Documentation**: `docs/##-description` (e.g., `docs/22-api-documentation`)
   - **Operations**: `ops/##-description` (e.g., `ops/18-docker-improvements`)
   - **Refactoring**: `refactor/##-description` (e.g., `refactor/33-cleanup-views`)
   - See `docs/dev/Workflow.md` for complete conventions including test-only and tweak branches
6. **Do development changes** - Commit to git at logical checkpoints during development
7. **After first commit, push the branch to GitHub** - Use the same branch name as the local one
8. **Once issue is complete and all changes pushed** - Create a pull request using the template
9. **Before creating the pull request** - Run full test validation (see Testing Workflow below)
10. **After pull request is merged** - Clean up and prepare for next work (see Post-PR Cleanup below)

### Testing Workflow (Required Before Pull Requests)

**MANDATORY**: Before creating any pull request, you must run and pass all of these checks:

**NOTE**: All commands run from PROJECT ROOT directory for consistency.

```bash
# 1. Run full unit test suite
src/manage.py test
# Must show: "OK" with all tests passing

# 2. Run code quality check (only if source code was modified)
flake8 --config=src/.flake8-ci src/hi/
# Must show: no output (clean)

# 3. Verify Django configuration
src/manage.py check
# Must show: "System check identified no issues"
```

**Important**: Do not create pull requests if any of these checks fail. Fix all issues first.

### Pull Request Requirements

Before any pull request can be merged, the following requirements must be met:

1. **Unit Tests**: All unit tests must pass (`src/manage.py test`)
2. **Code Quality**: flake8 linting with `.flake8-ci` configuration must pass with no violations (if source code modified) (`flake8 --config=src/.flake8-ci src/hi/`)
3. **Django Check**: Django system check must pass with no issues (`src/manage.py check`)
4. **GitHub CI**: GitHub Actions will automatically verify these requirements and will block PR merging if they fail

These requirements are enforced by GitHub branch protection rules and cannot be bypassed.

For detailed branching conventions and additional workflow information, see `docs/dev/Workflow.md`.

### Post-PR Cleanup (After Pull Request Merged)

**HUMAN INITIATED**: This workflow must be triggered manually when you confirm a PR has been merged. Never run without explicit confirmation that the PR is merged.

**MANDATORY Safety Checks** - Execute these verification steps before any cleanup actions:

```bash
# 1. Verify current branch is a feature branch (not staging/master)
git branch --show-current
# Must show a feature branch pattern like: bugfix/##-description, feature/##-description, etc.
# STOP if output shows: staging, master, main

# 2. Verify working directory is clean (no uncommitted changes)
git status
# Must show: "nothing to commit, working tree clean"
# STOP if there are uncommitted changes - commit or stash them first

# 3. Verify the PR is actually merged
gh pr view --json state,mergedAt
# Must show: "state": "MERGED" and "mergedAt": with a timestamp
# STOP if state is not "MERGED"
```

**Cleanup Actions** - Only proceed if all safety checks pass:

```bash
# 4. Switch to staging branch
git checkout staging

# 5. Sync with latest remote changes
git pull origin staging

# 6. Delete the merged feature branch (use branch name from step 1)
git branch -d <feature-branch-name>
# Example: git branch -d bugfix/31-controller-modal-fix

# 7. Verify clean final state
git status
# Should show: "On branch staging" and "nothing to commit, working tree clean"
```

**If any safety check fails:**
- **DO NOT proceed** with cleanup actions
- **Address the issue** (commit changes, wait for PR merge, etc.)
- **Re-run verification** before attempting cleanup

This process ensures you're ready for the next issue while preventing accidental data loss.

### Work Documentation for Non-Trivial Issues

When working on complex issues that involve significant planning or multi-step implementation:

1. **Capture Work Progress**: Document completed work, current status, and remaining tasks
2. **Document Planning**: Record architectural decisions, implementation approaches, and design rationale
3. **Maintain Context**: Keep notes that allow resuming work efficiently if interrupted
4. **Reference in Issues**: Update the GitHub issue with progress summaries and decision points

This documentation helps maintain continuity across work sessions and provides valuable context for code reviews and future maintenance.

## Environment-Specific Configuration

### Git Remote Configuration
- Use `git push origin` or `git push -u origin branch-name` for pushing branches

### Development Commands Quick Reference
For detailed setup and daily commands, see [Development Setup](dev/Setup.md).

```bash
# Common commands (all run from PROJECT ROOT)
src/manage.py test
flake8 --config=src/.flake8-ci src/hi/
src/manage.py runserver  # http://127.0.0.1:8411
```

## Project Documentation References

For comprehensive project information, see:

- **Architecture**: [dev/Architecture.md](dev/Architecture.md) - System design, patterns, and component overview
- **Development Guidelines**: [dev/Guidelines.md](dev/Guidelines.md) - Coding standards, style guide, and conventions
- **Testing**: [dev/Testing.md](dev/Testing.md) - Testing patterns, best practices, and anti-patterns
- **Setup**: [dev/Setup.md](dev/Setup.md) - Environment setup and daily development commands
- **Workflow**: [dev/Workflow.md](dev/Workflow.md) - Branching, commits, and pull request process

## Release Process (Claude-Specific)

When executing the release process documented in `docs/dev/ReleaseProcesses.md`, use these AI-specific commands and considerations:

### Release Execution Commands
```bash
# Pre-release verification (combine all checks)
git status && make check

# Version bump and commit
git add HI_VERSION && git commit -m "Bump version number to vX.X.X"
git push origin staging

# Merge to master
git checkout master && git pull origin master
git merge staging && git push origin master

# Create release (CLI method - preferred for automation)
gh release create vX.X.X --title "vX.X.X" --generate-notes --latest
```

### Release Process Considerations
- **Working Directory**: Always verify clean working directory before starting
- **Dependency Vulnerabilities**: GitHub may warn about dependencies during push - note but don't block release
- **Documentation Changes**: Commit any documentation updates to staging before switching branches
- **GitHub CLI**: Prefer `gh` command for release creation over manual UI steps

See `docs/dev/ReleaseProcesses.md` for the complete process documentation.

## Generated Code Standards (Claude-Specific)

All generated code must comply with the `.flake8-ci` configuration rules. Common issues to avoid:

1. **Final Newlines**: All files must end with a single newline character
2. **Unused Imports**: Remove all unused import statements
3. **Unused Variables**: Remove or prefix unused variables with underscore (`_variable`)
4. **Line Continuation**: Proper indentation for multi-line statements following PEP 8
5. **Line Length**: Respect maximum line length limits defined in `.flake8-ci`

Before submitting code, always run: `flake8 --config=src/.flake8-ci src/hi/` to verify compliance.

## Commit Message Guidelines (Claude-Specific)

- Use concise, descriptive commit messages without attribution text
- Focus on **what** was changed and **why**, not implementation details
- Keep messages professional and project-focused
- **Do NOT include** Claude Code attribution, co-author tags, or generated-by comments

**Good examples:**
```
Fix weather module unit test failures and improve WMO units handling
Add support for temperature offset unit arithmetic in Pint
Remove invalid AlertUrgency.PAST enum value for weather alerts
```

**Avoid:**
```
🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>
```
