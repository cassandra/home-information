---
allowed-tools: Bash, Read, TodoWrite, Grep
description: Pick up a GitHub issue following our development workflow
model: claude-3-5-sonnet-20241022
argument-hint: [issue-number]
---

Pick up GitHub issue #$1 following our development workflow from docs/dev/workflow/workflow-guidelines.md:

## Issue Pickup Process for #$1

Execute the complete issue pickup workflow:

1. **Use TodoWrite to plan the pickup process** - Track all workflow steps
   - Read `docs/CLAUDE.md` for development philosophy and workflow integration
   - Focus on well-factored solutions and quality over speed

2. **Read the GitHub issue and all comments** - Understand requirements, context, and discussion using `gh issue view $1`

3. **Ensure on latest staging branch** - MANDATORY safety step:
   - Verify current branch and working directory status
   - Switch to staging: `git checkout staging`
   - Pull latest: `git pull origin staging`
   - Verify clean state: `git status`

4. **Assign issue to yourself** - Use: `gh issue edit $1 --add-assignee @me`

5. **Create feature branch immediately** - Use proper naming from `docs/dev/workflow/workflow-guidelines.md`:
   - Determine branch type from issue labels/content (feature/bugfix/docs/ops/refactor)
   - Create branch: `git checkout -b [type]/$1-[mnemonic]`
   - Push branch: `git push -u origin [branch-name]`

6. **Investigation and planning** - Research the codebase:
   - Search for relevant code, components, and files
   - Identify affected areas and dependencies
   - Understand current implementation
   - Plan implementation approach

7. **Post investigation comment to GitHub issue** - Document:
   - Summary of investigation findings
   - Proposed implementation approach
   - Key files/components to be modified
   - Any questions or concerns identified
   - Multi-phase strategy if applicable (following workflow-guidelines.md)

**Critical requirements:**
- Follow exact workflow from `docs/dev/workflow/workflow-guidelines.md`
- Follow branch naming conventions from `docs/dev/workflow/workflow-guidelines.md`
- Create feature branch BEFORE any investigation work
- Always verify clean working directory before branch operations
- Post comprehensive investigation findings to GitHub issue

**Issue to pick up:** #$1

Begin the pickup process now.