---
allowed-tools: Bash, Read, Edit, TodoWrite, Grep, Glob, Task
description: Deep investigation and analysis of GitHub issues for implementation planning
model: claude-3-5-sonnet-20241022
argument-hint: [issue-number]
---

Deep investigation and implementation planning for GitHub issue #$1:

## Investigation Process for #$1

Perform comprehensive codebase analysis and implementation planning:

1. **Use TodoWrite to plan investigation phases** - Track analytical work
   - Read `docs/CLAUDE.md` for AI-specific guidance and sub-agent coordination patterns
   - Follow development philosophy of well-factored solutions

2. **Read GitHub issue completely** - Use `gh issue view $1` to understand:
   - Full issue description and requirements
   - All comments and discussion history
   - Labels, assignees, and project context
   - Related issues or dependencies

3. **Codebase research using specialized agents** - Use Task tool with appropriate agents:
   - **general-purpose agent**: For broad code searches and cross-domain discovery
   - **domain-expert agent**: For business logic analysis
   - **backend-dev agent**: For Django model/database analysis
   - **frontend-dev agent**: For template/UI analysis
   - **integration-dev agent**: For external API analysis

4. **Comprehensive code analysis** - Identify:
   - Relevant files, classes, and functions
   - Current implementation patterns
   - Dependencies and integration points
   - Existing test coverage
   - Similar functionality elsewhere in codebase

5. **Design-heavy issue detection** - Check if issue involves both design AND implementation:
   - Look for requests for "better styling", "improved layout", "enhanced UI"
   - Identify ambiguous visual requirements
   - Assess if wireframes/mockups needed
   - Recommend issue splitting if applicable (per `docs/dev/workflow/workflow-guidelines.md`)

6. **Implementation strategy planning** - Following `docs/dev/workflow/workflow-guidelines.md`:
   - Plan multi-phase approach if complex
   - Phase 1: Simple, reliable solution addressing core issue
   - Phase 2+: Advanced optimizations, UX improvements
   - Identify natural stopping points for review

7. **Impact assessment** - Analyze:
   - Breaking changes potential
   - Performance implications
   - Security considerations
   - Testing requirements

8. **Post comprehensive findings to GitHub issue** - Include:
   - Summary of investigation findings
   - Detailed implementation approach
   - Key files/components to be modified
   - Multi-phase breakdown if applicable
   - Design/implementation splitting recommendation if needed
   - If issue splitting recommended, provide specific `/createissue` commands
   - Questions or concerns requiring clarification
   - Estimated complexity and timeline

9. **Investigation Outcome Recommendations** - Guide next steps based on findings:
   - **Recommend `/plan` if analysis reveals:**
     - Multi-phase implementation needed across multiple PRs
     - Epic-level work requiring issue decomposition
     - Cross-cutting changes affecting multiple systems
     - Work breakdown structure needed for complex features
   - **Recommend `/design` if analysis reveals:**
     - UI/UX decisions requiring mockups or wireframes
     - Visual design specifications missing
     - Interaction patterns need clarification
     - Ambiguous styling or layout requirements
   - **Recommend `/execute` if analysis reveals:**
     - Clear implementation path identified
     - All technical questions resolved
     - Requirements well-defined and single-PR scope
     - Ready for immediate development
   - **Recommend continued `/investigate` if analysis reveals:**
     - Additional research domains identified
     - More technical unknowns discovered
     - Need for deeper integration analysis

**Investigation target:** GitHub issue #$1
**Goal:** Complete technical analysis and implementation roadmap

Begin deep investigation now.