# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Workflow for GitHub Issues

When working on GitHub issues, follow this development workflow:

1. **Read the GitHub issue and all its comments** - Understand the requirements, context, and any discussion
2. **Ensure staging branch is in sync with GitHub** - Make sure you have the latest changes
3. **Create a dev branch off the staging branch** - Follow naming conventions from `docs/dev/Workflow.md`
4. **Do development changes** - Commit to git at logical checkpoints during development
5. **After first commit, push the branch to GitHub** - Use the same branch name as the local one
6. **Once issue is complete and all changes pushed** - Create a pull request using the template
7. **Before creating the pull request** - Ensure all unit tests pass and flake8 linting with .flake8-ci config is clean

### Pull Request Requirements

Before any pull request can be merged, the following requirements must be met:

1. **Unit Tests**: All unit tests must pass (`./manage.py test`)
2. **Code Quality**: flake8 linting with `.flake8-ci` configuration must pass with no violations
3. **GitHub CI**: GitHub Actions will automatically verify these requirements and will block PR merging if they fail

These requirements are enforced by GitHub branch protection rules and cannot be bypassed.

For detailed branching conventions and additional workflow information, see `docs/dev/Workflow.md`.

### Work Documentation for Non-Trivial Issues

When working on complex issues that involve significant planning or multi-step implementation:

1. **Capture Work Progress**: Document completed work, current status, and remaining tasks
2. **Document Planning**: Record architectural decisions, implementation approaches, and design rationale
3. **Maintain Context**: Keep notes that allow resuming work efficiently if interrupted
4. **Reference in Issues**: Update the GitHub issue with progress summaries and decision points

This documentation helps maintain continuity across work sessions and provides valuable context for code reviews and future maintenance.

## Environment-Specific Configuration

### Git Remote Configuration
- The remote repository name is `github` (not `origin`)
- Use `git push github` or `git push -u github branch-name` for pushing branches

### Development Commands Quick Reference
For detailed setup and daily commands, see [Development Setup](dev/Setup.md).

```bash
# Daily development setup
. ./init-env-dev.sh

# Common commands
cd src && ./manage.py test
cd src && flake8 --config=.flake8-ci src/
./manage.py runserver  # http://127.0.0.1:8411
```

## Project Documentation References

For comprehensive project information, see:

- **Architecture**: [dev/Architecture.md](dev/Architecture.md) - System design, patterns, and component overview
- **Development Guidelines**: [dev/Guidelines.md](dev/Guidelines.md) - Coding standards, style guide, and conventions
- **Testing**: [dev/Testing.md](dev/Testing.md) - Testing patterns, best practices, and anti-patterns
- **Setup**: [dev/Setup.md](dev/Setup.md) - Environment setup and daily development commands
- **Workflow**: [dev/Workflow.md](dev/Workflow.md) - Branching, commits, and pull request process

## Generated Code Standards (Claude-Specific)

All generated code must comply with the `.flake8-ci` configuration rules. Common issues to avoid:

1. **Final Newlines**: All files must end with a single newline character
2. **Unused Imports**: Remove all unused import statements
3. **Unused Variables**: Remove or prefix unused variables with underscore (`_variable`)
4. **Line Continuation**: Proper indentation for multi-line statements following PEP 8
5. **Line Length**: Respect maximum line length limits defined in `.flake8-ci`

Before submitting code, always run: `cd src && flake8 --config=.flake8-ci src/` to verify compliance.

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
