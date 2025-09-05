# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Quick Reference - Common Process Checkpoints

**Before Starting Development:**
- [ ] On staging branch with latest changes (`git status`, `git pull origin staging`)
- [ ] Use TodoWrite tool to plan tasks (mandatory for complex work)
- [ ] Create properly named feature branch

**During All Code Changes:**
- [ ] **All new files MUST end with newline** (prevents W391 linting failures)
- [ ] **All imports MUST be at file top** (never inside functions/methods)
- [ ] **Use `/bin/rm` instead of `rm`** (avoid interactive prompts)

**Before Any Commit:**
- [ ] Use concise commit messages WITHOUT Claude attribution
- [ ] Examples: "Fix UI testing framework system state issue" ✅
- [ ] Avoid: "🤖 Generated with Claude Code" ❌

**Before Creating Pull Request:**
- [ ] `make test` (must show "OK")
- [ ] `make lint` (must show no output)
- [ ] Both MUST pass before PR creation
- [ ] **Use a /tmp file for PR body** (prevents quoting failures)
- [ ] Follow `.github/PULL_REQUEST_TEMPLATE.md` structure

**Before Creating Unit Tests:**
- [ ] Consult Testing guidelines and `docs/dev/testing/testing-guidelines.md`

**Process Verification Pattern:**
Before major actions, ask yourself:
1. "Did I use TodoWrite to plan this work?"
2. "Have I run all required tests?"
3. "Is my commit message following guidelines?"
4. "Am I on the correct branch with latest staging changes?"

## Task Management (TodoWrite Tool)

**MANDATORY for complex tasks**: Use TodoWrite tool extensively for:
- Planning multi-step implementations
- Breaking down complex issues into phases
- Tracking progress during development
- Including testing and validation steps in todos
- Ensuring no steps are forgotten

**Use immediately when starting work on:**
- GitHub issues with multiple requirements
- Refactoring tasks
- Any work involving multiple files or components

IMPORTANT: Always use the TodoWrite tool to plan and track tasks throughout the conversation.

## Sub-Agent Usage Patterns

Claude Code has access to specialized sub-agents with specific expertise areas defined in their YAML configurations. Use them proactively rather than as a fallback - they often provide more thorough, expert-level analysis than attempting work directly.

### Best Practices for Sub-Agent Usage

**Be Specific About Scope**: Instead of "help debug tests", use "debug why EntityForm validation is failing when entity_type_str='sensor' but passing for 'wall_switch'"

**Provide Context**: Give sub-agents the specific issue, relevant code snippets, and what you've already tried

**Request Actionable Output**: Ask for specific deliverables like "return the exact test code to add" or "provide the minimal fix for the payload detection logic"

**Chain Sub-Agents**: Use results from one sub-agent as input to another (e.g., investigation findings from general-purpose → specific implementation from domain expert)

### Example Usage

```
# Good: Specific scope and clear deliverable request
Task(subagent_type="test-engineer", 
     prompt="Debug why EntityEditView POST test fails with 500 error when submitting properties-only form. 
     Focus on form validation - I suspect EntityForm.is_valid() is failing but need to identify the specific field causing issues.
     Return the exact cause and minimal fix needed.")

# Less effective: Too broad and vague
Task(subagent_type="general-purpose", 
     prompt="Help with entity editing")
```

**Key Insight**: Sub-agents often provide more thorough, expert-level analysis than attempting the work directly. Use them proactively rather than as a fallback.

## Development Workflow for GitHub Issues

When working on GitHub issues, follow this development workflow:

1. **Read the GitHub issue and all its comments** - Understand the requirements, context, and any discussion

2. **Ensure you're on the latest staging branch** - MANDATORY step before any work:
   - If coming from a merged PR, run Post-PR Cleanup first (see step 11)
   - Switch to staging branch: `git checkout staging`
   - Pull latest changes: `git pull origin staging`
   - Verify you're on the correct branch: `git status`

3. **Create a feature branch immediately** - MANDATORY before any investigation or changes:
   - Use proper naming convention based on issue type:
     - **Bug fixes**: `bugfix/##-description` (e.g., `bugfix/31-controller-modal-fix`)
     - **New features**: `feature/##-description` (e.g., `feature/45-weather-alerts`)
     - **Documentation**: `docs/##-description` (e.g., `docs/22-api-documentation`)
     - **Operations**: `ops/##-description` (e.g., `ops/18-docker-improvements`)
     - **Refactoring**: `refactor/##-description` (e.g., `refactor/33-cleanup-views`)
   - **Why create immediately**: Investigation may involve temporary file changes, and it's safer to work on a branch
   - **If no changes needed**: Simply delete the unused branch with `git branch -d branch-name`
   - See `docs/dev/workflow/workflow-guidelines.md` for complete conventions including test-only and tweak branches

4. **Use TodoWrite tool to plan the work** - MANDATORY for complex tasks:
   - Break down the issue into specific, actionable tasks
   - Include investigation, implementation, testing, and validation steps
   - Mark tasks as in_progress/completed as you work

5. **Investigate and plan the implementation** - MANDATORY step for all issues:
   - Assign the issue to yourself: `gh issue edit <issue-number> --add-assignee @me`
   - Research the codebase to understand current implementation  
   - Identify files, functions, and components that need changes
   - Consider edge cases, dependencies, and potential impacts
   - **Check for design-heavy issues** - If issue involves both design/UX work AND implementation, consider splitting (see Design-Heavy Issue Detection below)
   - Plan the implementation approach and sequence of changes
   - **Post a comment on the GitHub issue** documenting:
     - Summary of investigation findings
     - Proposed implementation approach
     - Key files/components that will be modified
     - Any questions or concerns identified
     - Issue splitting recommendation if applicable
   - **Wait for confirmation only if**:
     - You have critical questions that could affect the implementation
     - Important information is missing or unclear from the issue
     - Multiple solution approaches exist with no clear best choice
     - The proposed changes have significant architectural implications
     - **You recommend splitting a design-heavy issue**
   - Otherwise, proceed directly to implementation

#### Design-Heavy Issue Detection and Splitting

During investigation, if an issue involves **both** design/UX work **and** implementation:

**Indicators of design-heavy issues:**
- Requests for "better styling", "improved layout", "enhanced UI"
- Mentions of wireframes, mockups, or visual design
- Ambiguous visual requirements needing clarification
- Multiple UI components or significant template changes
- User experience improvements without specific implementation details

**Recommended approach:**
1. **Suggest issue splitting** in your GitHub comment:
   ```
   Based on investigation, this issue involves both design and implementation work. 
   I recommend splitting this into:
   
   - Issue A: "[Original Title] - Design & Wireframes" 
     - Create wireframes/mockups
     - Define visual approach and information architecture
     - Get stakeholder approval on design direction
   
   - Issue B: "[Original Title] - Implementation"
     - Implement approved design
     - Code templates and styling
     - Add tests and validation
   
   This approach allows design iteration without blocking implementation and 
   enables focused review of each phase.
   ```

2. **Wait for confirmation** before proceeding (this falls under the "significant architectural implications" case)

3. **If splitting approved**: Complete design work in current issue, create implementation issue upon design approval

4. **If splitting declined**: Proceed but use multi-phase strategy with design as Phase 1

**Design Phase Deliverables:**
- Always include wireframes/mockups as GitHub issue comments with images
- Get explicit "approved for implementation" comment before coding begins
- Use GitHub issue linking (`Closes #123`) to maintain traceability between design and implementation issues

#### Design Work Documentation Workflow

When working on design-focused issues (UX improvements, UI redesigns, mockups, wireframes):

**Local Work Directory Structure:**
```bash
# All design work goes in data/design (git ignored)
data/design/issue-{number}/
├── mockup.html                    # Interactive HTML mockups
├── architecture.md                # Technical architecture docs  
├── interaction-patterns.md        # UX interaction specifications
├── design-summary.md              # Executive summary
└── other-design-artifacts.*       # Additional files as needed
```

**Design Workflow Process:**
1. **Create issue subdirectory**: `mkdir -p data/design/issue-{number}`
2. **Iterate locally**: Create, refine, and iterate on design documents locally
3. **No repository commits**: Design work products stay local only (`data/` is in .gitignore)
4. **Post to GitHub issue**: Share stable versions via GitHub issue comments/attachments

**GitHub Issue Documentation Pattern:**
```markdown
## Phase X Design Complete - Ready for Review

Brief summary of key decisions and deliverables:

1. **Interactive Mockup** (attached) - HTML file for browser viewing
2. **Architecture Document** (comment below) - Technical specifications
3. **Interaction Patterns** (comment below) - UX behavior definitions

[Key decisions summary...]

Ready for stakeholder review and implementation planning.
```

**Content Organization:**
- **Visual deliverables** (HTML mockups, images): Attach as GitHub issue attachments
- **Textual content** (markdown docs): Post as regular GitHub issue comments
- **Benefits**: Attachments can be downloaded/viewed directly, comments are searchable and linkable

**Design Iteration Process:**
1. Create design documents in `data/design/issue-{number}/`
2. Iterate and refine locally based on feedback
3. Post important checkpoints or final versions to GitHub issue
4. Never commit design work products to repository
5. Maintain audit trail in GitHub issue comments

This workflow keeps the repository clean while providing comprehensive design documentation and stakeholder review capabilities.

5.5. **For Complex Issues - Apply Multi-Phase Strategy** (when applicable):
   - If issue involves multiple aspects, significant trade-offs, or substantial complexity, apply the multi-phase methodology from [Domain Guidelines](dev/domain/domain-guidelines.md#complex-issue-implementation-strategy)
   - Post phase breakdown to GitHub issue before starting implementation
   - Complete Phase 1 fully, commit and push (but don't create PR yet)
   - Update TodoWrite tool with phase completion status
   - Stop and report Phase 1 completion with summary
   - Wait for human feedback before proceeding to subsequent phases
   - Only create PR when all phases complete or explicitly requested

6. **Development environment check** - The virtual environment and necessary environment variables should be set before starting claude. If there is no virtual environment, this is an indication that the environment has not been properly set up. That means the unit test cannot run and code changes cannot be validated.  We shoudl stop the process and fix it.  There is no need to check ever time since this shoudl be rare, but if running tests is failing, that is a good thing to look for.

7. **Do development changes** - Commit to git at logical checkpoints during development

8. **After first commit, push the branch to GitHub** - Use the same branch name as the local one

9. **Run Testing Workflow** - MANDATORY before creating PR (see below)

10. **Create a pull request** - Using the template, only after all tests pass

11. **After pull request is merged** - Clean up and prepare for next work (see Post-PR Cleanup below)

### Testing Workflow (Required Before Pull Requests)

**MANDATORY**: Before creating any pull request, you must run and pass all of these checks:

**NOTE**: All commands run from PROJECT ROOT directory for consistency.

```bash
# 1. Run full unit test suite
make test
# Must show: "OK" with all tests passing

# 2. Run code quality check (only if source code was modified)
make lint
# Must show: no output (clean)
```

**Important**: Do not create pull requests if any of these checks fail. Fix all issues first.

### Pull Request Requirements

Before any pull request can be merged, the following requirements must be met:

1. **Unit Tests**: All unit tests must pass (`make test`)
2. **Code Quality**: flake8 linting with `.flake8-ci` configuration must pass with no violations (if source code modified) (`make lint`)
3. **GitHub CI**: GitHub Actions will automatically verify these requirements and will block PR merging if they fail

These requirements are enforced by GitHub branch protection rules and cannot be bypassed.

For detailed branching conventions and additional workflow information, see `docs/dev/workflow/workflow-guidelines.md`.

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

## Creating GitHub Issues

When creating new GitHub issues, use the appropriate issue template:

### Available Issue Templates
- **Bug Report** (`[Bug]`): For reporting bugs or unexpected behavior
- **Feature Request** (`[Feature]`): For proposing new features or enhancements  
- **Refactor Request** (`[Refactor]`): For improving code quality without changing behavior
- **Ops/Deployment Issue** (`[Ops]`): For infrastructure, CI/CD, or deployment issues
- **Documentation** (`[Docs]`): For documentation improvements
- **Tests** (`[Tests]`): For test-related improvements

### Creating Issues via GitHub CLI
When using `gh issue create`, specify the template with the `--template` flag:
```bash
# Examples:
gh issue create --template bug_report.md --title "[Bug] Description"
gh issue create --template refactor.md --title "[Refactor] Description"
gh issue create --template operations.md --title "[Ops] Description"
```

**Note**: The repository has `blank_issues_enabled: false`, so you must use a template.

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
make test                # Run unit tests
make lint               # Run code quality checks
src/manage.py runserver  # http://127.0.0.1:8411
```

## Project Documentation References

For comprehensive project information, see:

- **Architecture**: [dev/shared/architecture-overview.md](dev/shared/architecture-overview.md) - System design, patterns, and component overview
- **Development Guidelines**: [dev/shared/coding-standards.md](dev/shared/coding-standards.md) - Coding standards, style guide, and conventions
- **Testing**: [dev/testing/testing-guidelines.md](dev/testing/testing-guidelines.md) - Testing patterns, best practices, and anti-patterns
- **Setup**: [dev/Setup.md](dev/Setup.md) - Environment setup and daily development commands
- **Workflow**: [dev/workflow/workflow-guidelines.md](dev/workflow/workflow-guidelines.md) - Branching, commits, and pull request process

## Release Process (Claude-Specific)

When executing the release process documented in `docs/dev/workflow/release-process.md`, use these AI-specific commands and considerations:

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

See `docs/dev/workflow/release-process.md` for the complete process documentation.

## Generated Code Standards (Claude-Specific)

All generated code must comply with the `.flake8-ci` configuration rules. Common issues to avoid:

1. **Final Newlines**: All files must end with a single newline character
2. **Unused Imports**: Remove all unused import statements
3. **Unused Variables**: Remove or prefix unused variables with underscore (`_variable`)
4. **Line Continuation**: Proper indentation for multi-line statements following PEP 8
5. **Line Length**: Respect maximum line length limits defined in `.flake8-ci`

Before submitting code, always run: `make lint` to verify compliance.

## GitHub PR Creation (Claude-Specific)

**CRITICAL**: Use HEREDOC syntax to prevent quoting failures:

```bash
gh pr create --title "Brief Title" --body "$(cat <<'EOF'
[Follow the structure from .github/PULL_REQUEST_TEMPLATE.md]
## Pull Request: [Short Title]

### Issue Link
Closes #123

[Rest of template content]
EOF
)"
```

**Key points:**
- Always use `cat <<'EOF'` with single quotes around EOF
- This prevents variable expansion and special character issues
- Follow the exact structure from `.github/PULL_REQUEST_TEMPLATE.md`

## Django Template Guidelines (Claude-Specific)

Follow Django best practices for template design:

1. **Minimal Business Logic**: Keep business logic out of templates. Complex loops, conditionals, and data processing belong in views or custom template tags/filters.
2. **View Preparation**: Views should prepare all data that templates need. Templates should primarily display pre-processed data.
3. **Simple Conditionals**: Use only simple `{% if %}` statements for display logic. Avoid complex nested loops or data manipulation.
4. **Custom Template Tags**: Create custom template tags or filters for reusable template logic instead of embedding it directly.
5. **Data Structure**: Structure context data in views to match template needs rather than making templates adapt to raw data.

**Good examples:**
```python
# In view
context = {
    'alert': alert,
    'alert_has_visual_content': bool(alert.get_first_image_url()),
    'alert_first_image': alert.get_first_image_url(),
}
```

**Avoid:**
```django
<!-- Complex business logic in template -->
{% for alarm in alert.alarm_list %}
  {% for source_details in alarm.source_details_list %}
    {% if source_details.image_url %}
      <!-- Complex nested logic -->
    {% endif %}
  {% endfor %}
{% endfor %}
```
