---
allowed-tools: Bash, Read, TodoWrite, Grep, Glob, Task
description: Plan and execute refactoring with expert analysis
model: claude-3-5-sonnet-20241120
argument-hint: [target] (e.g., ClassName, module_name, or file_path)
---

Plan refactoring for: "$1"

## Expert Refactoring Planning Process

Execute comprehensive refactoring analysis and planning:

1. **Use TodoWrite to plan refactoring phases** - Track analysis and implementation
   - Read `docs/CLAUDE.md` for development philosophy and well-factored code principles
   - Use specialized agents for expert refactoring analysis

2. **Analyze current implementation** - Understand existing code:
   - Search for target: "$1" across codebase
   - Identify all usages and dependencies
   - Understand current patterns and structure
   - Document existing behavior and interfaces

3. **Use specialized refactoring agents** - Get expert analysis:
   - **Use Task tool with domain-expert agent**: Analyze business logic and responsibilities
   - **Use Task tool with backend-dev agent**: Django patterns, database design, architecture
   - **Use Task tool with test-engineer agent**: Test impact assessment and strategy
   - **Use Task tool with general-purpose agent**: Broad dependency and cross-domain analysis
   - **Use Task tool with code-quality agent**: Architecture compliance and quality assessment

4. **Identify refactoring opportunities** - Find improvement areas:
   - Code duplication and consolidation opportunities
   - Single Responsibility Principle violations
   - Coupling and cohesion issues
   - Performance bottlenecks
   - Maintainability concerns
   - Testing gaps

5. **Assess refactoring impact** - Evaluate scope and risk:
   - Files and components affected
   - Breaking change potential
   - Test coverage requirements
   - Performance implications
   - Migration complexity
   - Rollback considerations

6. **Plan refactoring phases** - Following workflow-guidelines.md multi-phase strategy:
   - **Phase 1**: Core structural improvements (no behavior changes)
   - **Phase 2**: Interface improvements and optimizations
   - **Phase 3**: Advanced features and enhancements
   - Each phase should be independently valuable

7. **Create implementation strategy** - Detailed execution plan:
   - Step-by-step refactoring sequence
   - Safe transformation techniques
   - Test-driven refactoring approach
   - Validation checkpoints
   - Rollback strategies

8. **Generate refactoring deliverables** - Provide comprehensive plan:
   - Current state analysis and pain points
   - Target architecture and improvements
   - Phase-by-phase implementation plan
   - Risk assessment and mitigation strategies
   - Testing strategy for each phase
   - Success metrics and validation criteria

**Refactoring guidelines:**
- Maintain existing behavior (no functional changes in Phase 1)
- Ensure comprehensive test coverage
- Use incremental, safe transformations
- Plan for rollback at each phase
- Document architectural decisions

**Refactoring target:** "$1"
**Goal:** Well-factored code following our architecture principles

**Key considerations from `docs/CLAUDE.md`:**
- Extremely well factored code
- Thoughtful responsibility boundaries
- Proper encapsulation
- Readability and maintainability
- Find well factored solutions, not just first working solutions

Begin refactoring analysis now.