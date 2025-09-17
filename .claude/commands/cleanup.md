---
allowed-tools: Bash, TodoWrite
description: Post-PR branch cleanup following our safety procedures
model: claude-3-5-sonnet-20241022
argument-hint: [feature-branch-name]
---

Post-PR cleanup for merged feature branch "$1" following `docs/dev/workflow/workflow-guidelines.md`:

## Post-PR Cleanup Process

Execute safe branch cleanup after PR merge:

1. **Use TodoWrite to plan cleanup steps** - Track safety-critical operations

2. **MANDATORY Safety Checks** - Execute verification steps before any cleanup:

   ```bash
   # 1. Verify current branch is the feature branch (not staging/master)
   git branch --show-current
   # Must show: $1 (or other feature branch pattern)
   # STOP if output shows: staging, master, main
   ```

   ```bash
   # 2. Verify working directory is clean (no uncommitted changes)
   git status
   # Must show: "nothing to commit, working tree clean"
   # STOP if there are uncommitted changes - commit or stash them first
   ```

   ```bash
   # 3. Verify the PR is actually merged
   gh pr view --json state,mergedAt
   # Must show: "state": "MERGED" and "mergedAt": with timestamp
   # STOP if state is not "MERGED"
   ```

3. **Cleanup Actions** - Only proceed if all safety checks pass:

   ```bash
   # 4. Switch to staging branch
   git checkout staging
   ```

   ```bash
   # 5. Sync with latest remote changes
   git pull origin staging
   ```

   ```bash
   # 6. Delete the merged feature branch
   git branch -d $1
   ```

   ```bash
   # 7. Verify clean final state
   git status
   # Should show: "On branch staging" and "nothing to commit, working tree clean"
   ```

4. **Final verification** - Confirm environment is ready for next work:
   - On staging branch with latest changes
   - Working directory clean
   - Feature branch successfully deleted
   - Ready for next `/pickup` command

**Critical safety requirements:**
- Follow exact process from `docs/dev/workflow/workflow-guidelines.md`
- NEVER proceed if safety checks fail
- Address any issues (commit changes, wait for PR merge, etc.) before cleanup
- Verify each step before proceeding to next

**Feature branch to clean up:** "$1"

**If any safety check fails:**
- DO NOT proceed with cleanup actions
- Address the issue first (commit changes, wait for PR merge, etc.)
- Re-run verification before attempting cleanup

Begin cleanup process now.