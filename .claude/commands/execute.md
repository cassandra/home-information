---
allowed-tools: Bash, Read, Edit, Write, TodoWrite, Grep, Glob, Task
description: Complete issue-to-PR orchestration with intelligent sub-agent coordination
model: claude-sonnet-4-20250514
argument-hint: [issue-number]
---

Complete issue-to-PR orchestration for GitHub issue #$1:

## Full Execution Workflow Orchestration

Execute complete strategic-to-delivery workflow with intelligent coordination:

1. **Use TodoWrite to plan complete execution workflow** - Track end-to-end orchestration
   - Read `docs/CLAUDE.md` for AI-specific guidance and development philosophy
   - Follow well-factored code principles and sub-agent coordination patterns

2. **Phase 1: Strategic Planning** - Execute planning workflow:
   - Read GitHub issue #$1 completely using `gh issue view $1`
   - Identify information gaps and clarification needs
   - Analyze work complexity and breakdown strategy
   - Determine if multi-phase or multi-issue approach needed
   - **CHECKPOINT**: Pause for human clarification if critical questions identified

3. **Pre-execution Validation** - Confirm issue readiness for execution:
   - **ESCALATE to `/plan` if:**
     - Issue spans multiple PRs or requires decomposition
     - Requires major architectural changes
     - Affects multiple apps/systems significantly
     - Epic-level work requiring breakdown
   - **ESCALATE to `/investigate` if:**
     - Implementation approach still unclear after planning
     - Significant technical unknowns remain
     - Requires extensive codebase research
     - Complex integration challenges identified
   - **ESCALATE to `/design` if:**
     - Visual mockups missing for UI changes
     - UI interaction patterns undefined
     - Requests visual improvements without specifications
     - Design decisions still needed
   - **ESCALATE to `/pickup` if:**
     - Single domain/file change with clear solution
     - Bug fix with identified root cause and location
     - Simple enhancement using existing patterns
     - No coordination between technical specialties needed
     - Atomic task suitable for single agent
   - **Continue with execution if:**
     - Multiple technical domains requiring coordination
     - Clear functional boundaries that can be divided among agents
     - Implementation phases with dependencies between specialties
     - Cross-system impacts requiring expert coordination
     - Issue contains artifacts enabling agent specialization

4. **Phase 2: Design Assessment** - Evaluate design requirements:
   - Assess if issue involves both design AND implementation work
   - Look for indicators: "better styling", "improved layout", "enhanced UI"
   - Check for ambiguous visual requirements needing wireframes
   - **CONDITIONAL EXECUTION**: If design-heavy, recommend design phase first
   - **CHECKPOINT**: Pause if design phase recommended - wait for approval

5. **Phase 3: Development Preparation** - Setup and initial analysis:
   - Ensure on latest staging branch: `git checkout staging && git pull origin staging`
   - Assign issue: `gh issue edit $1 --add-assignee @me`
   - Create feature branch with proper naming (bugfix/feature/docs/ops/refactor)
   - Push branch: `git push -u origin [branch-name]`

6. **Phase 4: Intelligent Implementation Coordination** - Parallel sub-agent execution:

   **Use Task tool to launch specialized agents in parallel:**

   **Primary Analysis Phase:**
   - **general-purpose agent**: Broad codebase search and cross-domain discovery
   - **domain-expert agent**: Business logic analysis and requirements understanding

   **Implementation Phase (based on issue type):**
   - **backend-dev agent**: Django models, database, manager classes, system architecture
   - **frontend-dev agent**: Templates, UI components, JavaScript, CSS, responsive design
   - **integration-dev agent**: External APIs, data synchronization, integration patterns
   - **test-engineer agent**: Test strategy, high-value tests, quality assurance

   **Coordination Strategy:**
   - Launch 2-3 agents in parallel based on issue scope
   - Agents work on complementary aspects simultaneously
   - Automatic handoffs between agents for dependencies
   - Progress tracking across all parallel work streams

7. **Phase 5: Quality Orchestration** - Systematic quality validation:

   **Quality Gates (must pass before proceeding):**
   ```bash
   # Run mandatory quality checks
   make test    # Must pass completely
   make lint    # Must show no output
   ```

   **Specialized Code Review** - Launch focused agents based on implementation domains:

   **Determine which agents to use based on what was implemented:**
   - **backend-dev agent** (if database, models, managers, or Django backend code): Review Django patterns, database operations, backend architecture, and manager implementations
   - **frontend-dev agent** (if templates, UI, CSS, JavaScript): Review template structure, frontend patterns, accessibility, and responsive design
   - **integration-dev agent** (if APIs, external services, data sync): Review integration patterns, API design, data transformation, and external service coordination
   - **test-engineer agent** (always for significant implementations): Review test coverage, test quality, testing patterns, and validation strategies
   - **domain-expert agent** (if business logic or domain rules): Review business rule implementation, domain modeling, and requirement compliance
   - **code-quality agent** (always): Review coding standards compliance, file organization, import structure, and adherence to project conventions from docs/CLAUDE.md

   **Agent-Specific Review Focus:**
   Each agent should focus ONLY on their area of expertise:

   - **backend-dev**: Django ORM usage, database patterns, manager architecture, system design
   - **frontend-dev**: UI patterns, accessibility, responsive design, JavaScript quality
   - **integration-dev**: API patterns, data synchronization, external service integration
   - **test-engineer**: Test coverage, testing strategies, test quality and maintainability
   - **domain-expert**: Business logic correctness, domain rule implementation, requirement fulfillment
   - **code-quality**: Coding standards, file structure, imports, naming conventions, documentation quality

   **Launch agents in parallel with specific scope:**
   ```
   Task: backend-dev - "Review only Django backend patterns and database operations"
   Task: test-engineer - "Review only test coverage and testing approach"
   Task: code-quality - "Review only coding standards and project convention compliance"
   ```

   **MANDATORY CHECKPOINT**: After code review completion, PAUSE execution and present review results to user for examination before proceeding with commit/PR creation.

8. **Phase 6: User Review Checkpoint** - Mandatory pause for human review:
   - Present all agent review results to user
   - Summarize key findings and recommendations
   - **PAUSE**: Wait for explicit user approval before proceeding
   - Address any concerns or make requested changes
   - Only proceed to Phase 7 after user approval

9. **Phase 7: PR Creation** - Automated pull request generation (only after user approval):
   - Use `/commit` command to create a properly formatted commit with issue context
   - Use `/pr` command to create pull request with standard template
   - This ensures consistent formatting and automatic issue linking
   - The `/pr` command handles `Closes #$1` automatically
   - Example: `/pr bugfix/205-monitoring 205`

10. **Phase 8: Post-Creation Validation** - Verify successful completion:
    - Confirm PR created successfully
    - Verify all GitHub Actions pass
    - Check PR template formatting
    - Provide PR URL for review

**Orchestration Intelligence:**

**Conditional Execution Paths:**
- **Simple issues**: Direct implementation without design phase
- **Design-heavy issues**: Mandatory design phase before implementation
- **Multi-phase issues**: Implement Phase 1 only, wait for feedback

**Agent Coordination Patterns:**
- **Backend + Test**: Parallel development with testing
- **Frontend + Domain**: UI implementation with business logic validation
- **Integration + Backend**: External APIs with data layer
- **Full Team**: Complex issues requiring all specializations

**Quality Gates and Checkpoints:**
- **Strategic checkpoint**: After planning, before implementation
- **Design checkpoint**: After design assessment, before development
- **Quality checkpoint**: After implementation, before code review
- **Review checkpoint**: After code review, before PR creation (MANDATORY PAUSE)
- **Completion checkpoint**: After PR creation, before handoff

**Error Recovery:**
- Automatic rollback on quality gate failures
- Pause and escalate on unresolvable conflicts
- Graceful degradation for partial completions

**Execution Principles:**
- **Well-factored solutions**: Find thoughtful, maintainable solutions, not first working code
- **Parallel when possible**: Multiple agents working simultaneously
- **Sequential when necessary**: Dependencies and handoffs
- **Quality first**: No shortcuts on testing or standards
- **Human collaboration**: Strategic checkpoints for guidance
- **Intelligent routing**: Right agents for right work types

**Execution Target:** GitHub issue #$1
**Goal:** Complete strategic-to-delivery workflow with PR ready for review

**Success Criteria:**
- Issue fully analyzed and planned
- Implementation complete and tested
- All quality gates passed
- PR created with proper documentation
- Ready for code review and merge

Begin complete execution orchestration now.