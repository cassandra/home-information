---
allowed-tools: Bash, Read, Write, TodoWrite
description: Create pull request following our workflow and template requirements
model: claude-3-5-sonnet-20241022
argument-hint: [title]
---

Create pull request with title "$1" following our workflow from `docs/dev/workflow/workflow-guidelines.md`:

## Pull Request Creation Process

Execute the complete PR creation workflow:

1. **Use TodoWrite to plan PR creation steps** - Track all required checks

2. **MANDATORY pre-PR requirements** - Both must pass before PR creation:
   ```bash
   # Run full test suite (must pass)
   make test

   # Run code quality check (must pass with no output)
   make lint
   ```
   **CRITICAL**: Do not create PR if either check fails. Fix all issues first.

3. **Gather PR information** - Collect required details:
   - Current branch name and recent commits
   - **Detect correct base branch** using `git remote show origin` to find HEAD branch
   - Related GitHub issue number(s)
   - Summary of changes made
   - Testing performed
   - Documentation updates needed

4. **Create PR using GitHub CLI** - Follow exact template from `.github/PULL_REQUEST_TEMPLATE.md`:

   **CRITICAL**: Use file-based approach to prevent escaping failures:
   ```bash
   # Detect the correct base branch from remote HEAD
   BASE_BRANCH=$(git remote show origin | grep 'HEAD branch:' | cut -d' ' -f5)
   if [ -z "$BASE_BRANCH" ]; then
     echo "Warning: Could not detect base branch, falling back to 'main'"
     BASE_BRANCH="main"
   fi
   echo "Using base branch: $BASE_BRANCH"

   # Write PR body to temporary file first
   cat > /tmp/pr_body.md <<'EOF'
   ## Pull Request: [TITLE]

   ### Issue Link
   Closes #[ISSUE_NUMBER]

   ---

   ## Category
   - [ ] **Feature** (New functionality)
   - [ ] **Bugfix** (Fixes an issue)
   - [ ] **Docs** (Documentation updates)
   - [ ] **Ops** (Infrastructure, CI/CD, build tools)
   - [ ] **Tests** (Adding/improving tests)
   - [ ] **Refactor** (Code improvements without changing functionality)
   - [ ] **Tweak** (Minor UI or code improvements)

   ---

   ## Changes Summary
   - [Describe changes made]

   ---

   ## How to Test
   1. [Testing steps]

   ---

   ## Checklist
   - [x] Code follows the project's style guidelines.
   - [x] Unit tests added or updated if necessary.
   - [x] All tests pass (`./manage.py test`).
   - [ ] Docs updated if applicable.
   - [x] No breaking changes introduced.

   ---

   ## Related PRs

   ---

   ## Screenshots (if applicable)

   ---

   ## Additional Notes

   ---

   ### **Ready for Review?**
   - [x] This PR is ready for review and merge.
   - [ ] This PR requires more work before approval.

   ---

   ### **Reviewer(s)**
   @cassandra
   EOF

   # Update placeholders in the file
   sed -i '' "s/\[TITLE\]/$1/g" /tmp/pr_body.md
   sed -i '' "s/\[ISSUE_NUMBER\]/ISSUE_NUMBER/g" /tmp/pr_body.md

   # Create PR using file reference with detected base branch
   gh pr create --title "$1" --body-file /tmp/pr_body.md --base "$BASE_BRANCH"

   # Clean up temporary file
   rm -f /tmp/pr_body.md
   ```

5. **Verify PR creation** - Check that:
   - PR was created successfully
   - Template formatting is correct
   - All required sections are filled
   - Proper category is selected
   - Issue is properly linked

**Requirements:**
- Follow exact workflow from `docs/dev/workflow/workflow-guidelines.md`
- Use exact template from `.github/PULL_REQUEST_TEMPLATE.md`
- **Automatically detect base branch** - Never assume 'main' or 'master', always detect from remote HEAD
- Must pass all pre-PR checks before creation
- Use HEREDOC syntax to prevent formatting issues
- No Claude attribution in PR description

**PR Title:** "$1"

Begin PR creation process now.