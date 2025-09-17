---
allowed-tools: Bash, Read, TodoWrite, Grep, Glob, Task
description: Systematic response to GitHub pull request feedback
model: claude-3-5-sonnet-20241022
argument-hint: [pr-number]
---

Systematic response to GitHub pull request #$1 feedback:

## PR Feedback Response Process

Focus on responding to feedback on GitHub pull request #$1:

1. **Use TodoWrite to plan feedback response workflow** - Track systematic review response

2. **Review project documentation** - Understand standards and guidelines:
   - Read `docs/CLAUDE.md` for AI behavior patterns and development philosophy
   - Read `docs/dev/workflow/workflow-guidelines.md` for development workflows
   - Read `docs/dev/shared/coding-standards.md` for coding standards
   - Read `docs/dev/testing/testing-guidelines.md` for testing practices
   - Read `docs/dev/shared/architecture-overview.md` for architectural principles

3. **Ensure correct branch state** - Verify working on PR branch:
   ```bash
   # Check current branch and status
   git status
   git branch --show-current

   # Pull latest changes from GitHub if needed
   git pull origin [current-branch]
   ```

4. **Read all PR feedback** - Collect and understand review comments:
   ```bash
   # View PR details and all comments
   gh pr view $1

   # Get detailed review comments
   gh pr view $1 --comments
   ```

5. **Categorize feedback types** - Organize by domain and nature:
   - **Code quality** - Style, patterns, architecture concerns
   - **Logic/functionality** - Business logic, implementation correctness
   - **Testing** - Test coverage, quality, patterns
   - **Documentation** - Comments, docs, README updates
   - **Security** - Security concerns or vulnerabilities
   - **Performance** - Efficiency, optimization suggestions
   - **UI/UX** - Frontend, template, user experience feedback
   - **Questions/clarifications** - Requests for explanation or context

6. **Assess feedback validity** - Evaluate each comment:
   - **Valid and actionable** - Clear improvement that should be implemented
   - **Valid but debatable** - Good point but may have alternative approaches
   - **Needs clarification** - Unclear feedback requiring discussion
   - **Invalid or unnecessary** - Feedback that doesn't align with project standards
   - **Out of scope** - Valid but belongs in separate issue/PR

7. **Create prioritized response plan** - Address most important feedback first:
   - **Priority 1** - Critical issues (security, functionality, breaking changes)
   - **Priority 2** - Important code quality and architecture concerns
   - **Priority 3** - Testing improvements and coverage gaps
   - **Priority 4** - Documentation and clarity improvements
   - **Priority 5** - Style and minor optimization suggestions
   - **Priority 6** - Questions and clarifications

8. **Use specialized analysis for complex feedback** - Get expert assistance:
   - **Use Task tool with domain-expert agent** - Business logic and architecture feedback
   - **Use Task tool with test-engineer agent** - Testing-related feedback
   - **Use Task tool with backend-dev agent** - Django patterns and database feedback
   - **Use Task tool with frontend-dev agent** - UI/template feedback
   - **Use Task tool with code-quality agent** - Code quality and standards feedback

9. **Execute systematic feedback response** - Work through prioritized plan:

   **For each feedback item, choose appropriate response:**

   **Option A: Implement requested change**
   - Make the code/test/documentation change
   - Commit with clear message referencing feedback
   - Verify change addresses the concern completely

   **Option B: Implement alternative solution**
   - Propose and implement better approach
   - Explain reasoning in PR comment reply
   - Ensure solution addresses underlying concern

   **Option C: Provide explanatory reply**
   - Explain why no change is needed
   - Reference project standards or architectural decisions
   - Provide context or rationale for current approach
   - Ask for clarification if feedback is unclear

10. **Validate all responses** - Ensure comprehensive coverage:
    - Every feedback comment has been addressed
    - All code changes maintain quality standards
    - Tests still pass after changes
    - Documentation is updated if needed
    - No regressions introduced

11. **Commit and push updates** - Document feedback responses:
    ```bash
    # Stage and commit changes
    git add .
    git commit -m "Address PR feedback: [summary of changes]"

    # Push updates to PR
    git push
    ```

12. **Follow up on PR** - Ensure review completion:
    - Reply to individual comments as needed
    - Add general PR comment summarizing changes made
    - Request re-review if significant changes made
    - Mark conversations as resolved when appropriate

**Response Strategy Guidelines:**
- Assess validity before responding - don't blindly implement all feedback
- Provide clear rationale when declining to make changes
- Prioritize critical and high-impact feedback first
- Maintain project standards and architectural consistency
- Be collaborative and professional in all responses

**Quality Standards:**
- All changes must follow project coding standards
- Maintain or improve test coverage
- Ensure documentation stays current
- No regressions or breaking changes
- Follow established architectural patterns

**Communication Principles:**
- Be respectful and professional in all responses
- Provide context and reasoning for decisions
- Ask for clarification when feedback is unclear
- Acknowledge good suggestions even if not implementing

**PR Target:** #$1
**Goal:** Systematic and complete response to all review feedback

Begin systematic PR feedback response now.