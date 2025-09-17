---
allowed-tools: Bash, TodoWrite
description: Create smart commits following our message standards
model: claude-3-5-sonnet-20241022
argument-hint: [commit-message]
---

Create commit with message "$1" following our standards from `docs/dev/workflow/workflow-guidelines.md`:

## Smart Commit Creation Process

Execute standardized commit workflow:

1. **Use TodoWrite to plan commit steps** - Track commit preparation

2. **Review current changes** - Understand what will be committed:
   ```bash
   # Check staged and unstaged changes
   git status
   git diff --cached  # staged changes
   git diff           # unstaged changes
   ```

3. **Stage appropriate files** - Add relevant changes:
   - Review each modified file for relevance
   - Stage files that belong together logically
   - Avoid mixing unrelated changes in single commit
   ```bash
   git add [specific-files]
   # OR for all relevant changes:
   git add .
   ```

4. **Validate commit message** - Ensure follows our standards:
   - **GOOD**: Focus on **what** changed and **why**
   - **GOOD**: "Fix weather module test failures and improve WMO units handling"
   - **GOOD**: "Add support for temperature offset unit arithmetic in Pint"
   - **BAD**: Generic messages like "update code" or "fix bug"
   - **MUST NOT**: Claude Code attribution or co-author tags
   - **MUST NOT**: Implementation details in commit message

5. **Create commit** - Use provided message:
   ```bash
   git commit -m "$1"
   ```

6. **Push to current branch** - Update remote:
   ```bash
   git push
   ```

7. **Verify commit success** - Confirm clean state:
   ```bash
   git status
   # Should show clean working directory
   git log --oneline -1
   # Should show your new commit
   ```

**Commit message standards (from `docs/dev/workflow/workflow-guidelines.md`):**
- Keep commits focused and atomic
- Clear messages about **what** and **why**, not implementation details
- NO Claude attribution or co-author tags
- NO generic messages

**Requirements:**
- Follow exact standards from `docs/dev/workflow/workflow-guidelines.md`
- Stage only relevant files for this logical change
- Use meaningful, descriptive commit message
- Push to current feature branch

**Commit message:** "$1"

Begin commit creation now.