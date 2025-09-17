---
allowed-tools: Bash, TodoWrite
description: Post-PR branch cleanup following our safety procedures
model: claude-3-5-sonnet-20241120
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
   # If uncommitted changes exist, HALT with recovery guidance:
   if ! git diff-index --quiet HEAD --; then
     echo "❌ SAFETY CHECK FAILED: Uncommitted changes detected"
     echo "These changes were made after PR merge (workflow violation)"
     echo ""
     echo "Recovery options:"
     echo "1. Commit to staging: git add . && git commit -m 'Post-merge fix'"
     echo "2. Create new branch: git switch -c fix/post-merge-changes"
     echo "3. Discard changes: git restore ."
     echo "4. Stash for later: git stash push -m 'Post-merge changes'"
     echo ""
     echo "After handling changes, re-run: /cleanup $1"
     exit 1
   fi
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
- **For uncommitted changes**: Use the provided recovery options to handle changes properly
- **For non-merged PR**: Wait for PR to be merged before cleanup
- **For wrong branch**: Switch to correct feature branch first
- Re-run `/cleanup $1` after addressing the issue

Begin cleanup process now.