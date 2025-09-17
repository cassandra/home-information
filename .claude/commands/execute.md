---
allowed-tools: Bash, Read, Edit, Write, TodoWrite, Grep, Glob, Task
description: Complete issue-to-PR orchestration with intelligent sub-agent coordination
model: claude-3-5-sonnet-20241022
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

3. **Phase 2: Design Assessment** - Evaluate design requirements:
   - Assess if issue involves both design AND implementation work
   - Look for indicators: "better styling", "improved layout", "enhanced UI"
   - Check for ambiguous visual requirements needing wireframes
   - **CONDITIONAL EXECUTION**: If design-heavy, recommend design phase first
   - **CHECKPOINT**: Pause if design phase recommended - wait for approval

4. **Phase 3: Development Preparation** - Setup and initial analysis:
   - Ensure on latest staging branch: `git checkout staging && git pull origin staging`
   - Assign issue: `gh issue edit $1 --add-assignee @me`
   - Create feature branch with proper naming (bugfix/feature/docs/ops/refactor)
   - Push branch: `git push -u origin [branch-name]`

5. **Phase 4: Intelligent Implementation Coordination** - Parallel sub-agent execution:

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

6. **Phase 5: Quality Orchestration** - Systematic quality validation:

   **Quality Gates (must pass before proceeding):**
   ```bash
   # Run mandatory quality checks
   make test    # Must pass completely
   make lint    # Must show no output
   ```

   **Expert Review Coordination:**
   - **Use Task tool with test-engineer agent**: Review test coverage and quality
   - **Use Task tool with domain-expert agent**: Validate business logic implementation
   - **Use Task tool with code-quality agent**: Review architecture and coding standards

   **Quality Validation:**
   - All tests passing with comprehensive coverage
   - Code quality standards met
   - Architecture and patterns aligned
   - Documentation updated appropriately

7. **Phase 6: PR Creation** - Automated pull request generation:
   - Generate PR title based on issue and implementation
   - Create comprehensive PR description following template
   - Use HEREDOC syntax for GitHub CLI: `gh pr create --title "..." --body "$(cat <<'EOF' ... EOF)"`
   - Include proper issue linking: `Closes #$1`
   - Select appropriate category and fill testing section

8. **Phase 7: Post-Creation Validation** - Verify successful completion:
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
- **Quality checkpoint**: After implementation, before PR creation
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