---
allowed-tools: Bash, Read, Write, TodoWrite, Grep, Glob
description: Design planning and HTML mockup creation for GitHub issues
model: claude-sonnet-4-20250514
argument-hint: [issue-number]
---

Design planning and HTML mockup creation for GitHub issue #$1:

## Design Phase Process

Execute design-focused work session for planning and mockup creation:

1. **Use TodoWrite to plan design phases** - Track design workflow steps
   - Read `docs/CLAUDE.md` for AI-specific guidance and development philosophy
   - Follow design workflow in `docs/dev/workflow/design-workflow.md`
   - Focus on well-factored design solutions

2. **Read GitHub issue completely** - Understand design requirements:
   - Use `gh issue view $1` to read issue description and all comments
   - Identify visual and UX requirements
   - Understand user needs and interaction goals
   - Note any existing design discussion or wireframes

3. **Orient to design task context** - Review relevant codebase:
   - Search for existing similar UI components or patterns
   - Review current styling and design patterns
   - Understand technical constraints and framework capabilities
   - Identify reusable components or templates

4. **Create design decision questions** - Before starting mockups:
   - What are the key layout and visual hierarchy decisions?
   - What interaction patterns should be used?
   - How should this integrate with existing UI patterns?
   - What are the responsive design requirements?
   - What accessibility considerations need addressing?
   - Are there specific branding or style guidelines to follow?
   - What are the performance constraints for the design?

5. **Ask clarifying questions** - Get design direction before mockup creation:
   - Present the design decision questions for clarification
   - Understand priorities and constraints
   - Clarify any ambiguous UX requirements
   - Confirm target user experience goals

6. **Create HTML mockup** - After design decisions are clarified:
   - Build interactive HTML mockup in `data/design/issue-$1/mockup.html`
   - Use existing CSS patterns and component styles where possible
   - Focus on layout, interaction patterns, and visual hierarchy
   - Make mockup interactive to demonstrate user flows
   - Ensure mockup works across different screen sizes

7. **Iterate on mockup design** - Refine before moving to documentation:
   - Test mockup functionality and user experience
   - Validate against design requirements
   - Ensure consistency with existing design patterns
   - Get feedback and iterate as needed
   - Finalize mockup before proceeding to interaction docs

8. **Create interaction documentation** - After mockup is finalized:
   - Document in `data/design/issue-$1/interaction-patterns.md`
   - Specify user interaction flows and behaviors
   - Define component states and transitions
   - Document accessibility patterns and requirements
   - Specify responsive behavior across breakpoints

9. **Create design summary** - Comprehensive deliverable:
   - Document in `data/design/issue-$1/design-summary.md`
   - Summarize key design decisions and rationale
   - Document component specifications
   - Include implementation guidance for developers
   - Note any dependencies or technical requirements

10. **Post design deliverables to GitHub issue** - Share for review:
    - Attach HTML mockup file to GitHub issue
    - Post interaction patterns as issue comment
    - Post design summary as issue comment
    - Mark as ready for stakeholder review and approval

**Design Workflow Integration:**
- Creates deliverables in `data/design/issue-{number}/` (git ignored)
- Separates design phase from implementation phase
- Provides comprehensive design specifications for implementation
- Follows design patterns established in project

**Design Phase Goals:**
- Create visual and interactive specifications
- Resolve UX and design decisions before implementation
- Provide clear guidance for implementation phase
- Enable design review and approval process

**Key Design Principles:**
- Iterate and finalize HTML mock before interaction docs
- Make design decisions explicit and documented
- Focus on user experience and interaction patterns
- Ensure consistency with existing design system

**Design Target:** GitHub issue #$1
**Output:** HTML mockup + interaction documentation + design summary

**Note:** This is a planning and design task that does not include implementation. The deliverables will guide the separate implementation phase.

Begin design planning and mockup creation now.