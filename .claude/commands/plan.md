---
allowed-tools: Bash, Read, TodoWrite, Grep, Glob
description: Strategic planning and work breakdown for GitHub issues
model: claude-3-5-sonnet-20241120
argument-hint: [issue-number]
---

Strategic planning and work breakdown for GitHub issue #$1:

## Strategic Planning Process

Help plan the work described in GitHub issue #$1 to determine optimal breakdown strategy:

1. **Use TodoWrite to plan strategic analysis** - Track planning phases
   - Read `docs/CLAUDE.md` for AI-specific guidance and project context
   - Follow development philosophy of well-factored solutions

2. **Read GitHub issue completely** - Understand full scope and context:
   - Use `gh issue view $1` to read issue description and all comments
   - Understand business requirements and user needs
   - Identify stated goals and success criteria
   - Note any existing discussion or proposed approaches

3. **Identify information gaps first** - Look for clarification needs:
   - Ambiguous requirements or unclear specifications
   - Missing technical details or constraints
   - Undefined success criteria or acceptance criteria
   - Unclear dependencies on other systems or features
   - Questions about user experience or design intent

4. **Ask clarifying questions** - Before proposing breakdown strategy:
   - What information is missing or unclear?
   - Are there unstated assumptions that need confirmation?
   - What are the priorities if scope needs to be reduced?
   - Are there specific technical constraints to consider?
   - What is the relationship to existing features or planned work?

5. **Analyze work complexity and scope** - After clarification:
   - Assess overall complexity and effort required
   - Identify distinct functional areas or components
   - Understand dependencies between different parts
   - Evaluate technical risk and uncertainty levels

6. **Evaluate isolation potential** - Key strategic question:
   - Can parts of this work deliver independent value?
   - Would partial implementation be useful even if later phases never happen?
   - Are there natural boundaries that could become separate issues?
   - What are the coupling points between different aspects?

7. **Determine breakdown strategy** - Choose optimal approach:

   **Multi-phase within single issue** (when work is tightly coupled):
   - All phases contribute to same core feature
   - Later phases build directly on earlier ones
   - No independent value from partial completion
   - Example: Phase 1 (core functionality), Phase 2 (optimizations), Phase 3 (advanced features)

   **Multi-issue breakdown** (when work can stand independently):
   - Each issue delivers standalone value
   - Issues can be implemented in any order
   - Each issue useful even if others never completed
   - Example: Separate issues for different features that happen to be related

   **Hybrid approach** (when some parts independent, others coupled):
   - Combination of separate issues and multi-phase within issues
   - Independent features as separate issues
   - Related optimizations as phases within issues

8. **Generate strategic plan** - Provide detailed breakdown:
   - Recommended approach with clear rationale
   - Specific phase or issue breakdown with descriptions
   - Dependencies and ordering recommendations
   - Effort estimates and risk assessment
   - Value delivery timeline and milestones
   - If multi-issue approach recommended, provide `/createissue` commands for each issue

9. **Plan Outcome Execution Guidance** - Direct next steps for implementation:
   - **Use `/design` for issues requiring:**
     - Visual mockups or wireframes for UI changes
     - UI interaction specifications and patterns
     - Design decision clarification before implementation
     - User experience flow definition
   - **Use `/execute` for issues with:**
     - Clear technical requirements and approach
     - Defined implementation path
     - No design ambiguity or visual decisions needed
     - Ready for immediate development
   - **Use `/investigate` for issues needing:**
     - Technical research or feasibility analysis
     - Codebase exploration and pattern discovery
     - Integration complexity assessment
     - Architecture decision investigation
   - **Continue planning if:**
     - Additional issue decomposition needed
     - Cross-issue dependencies require coordination
     - Strategic decisions still unclear

**Strategic Planning Goals:**
- Optimize for independent value delivery
- Minimize dependencies and coupling
- Enable flexible prioritization and scheduling
- Reduce risk through incremental approach
- Ensure clear success criteria for each phase/issue

**Planning Target:** GitHub issue #$1
**Output:** Strategic work breakdown with implementation roadmap

**Key Decision Criteria:**
- Can work stand in isolation regardless if following phases ever get done?
- Is there natural separation between functional areas?
- What delivers maximum value with minimum dependencies?

Begin strategic planning analysis now.