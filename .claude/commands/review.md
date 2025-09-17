---
allowed-tools: Bash, Read, TodoWrite, Task
description: Prepare code for review with quality checks and analysis
model: claude-3-5-sonnet-20250115
argument-hint:
---

Prepare current code for review following our quality standards:

## Code Review Preparation Process

Execute comprehensive review preparation:

1. **Use TodoWrite to plan review preparation** - Track all quality checks
   - Read `docs/CLAUDE.md` for AI behavior patterns and quality standards
   - Use sub-agent coordination for expert analysis

2. **Run mandatory quality checks** - Both must pass:
   ```bash
   # Run full test suite (must pass)
   make test
   ```
   ```bash
   # Run code quality check (must pass with no output)
   make lint
   ```
   **CRITICAL**: Address any failures before proceeding

3. **Generate change summary** - Document what was modified:
   ```bash
   # Show recent commits on current branch
   git log --oneline --graph -10

   # Show diff against staging branch
   git diff staging...HEAD

   # Show changed files
   git diff --name-only staging...HEAD
   ```

4. **Use specialized review agents** - Get expert analysis:
   - **Use Task tool with test-engineer agent**: Review test coverage and quality
   - **Use Task tool with domain-expert agent**: Analyze business logic changes
   - **Use Task tool with backend-dev agent**: Review Django patterns (if applicable)
   - **Use Task tool with frontend-dev agent**: Review template/UI changes (if applicable)

5. **Identify potential issues** - Look for:
   - Code quality concerns
   - Security vulnerabilities
   - Performance implications
   - Breaking changes
   - Missing tests
   - Documentation gaps

6. **Create review checklist** - Generate actionable items:
   - Code quality improvements needed
   - Test coverage gaps to address
   - Documentation updates required
   - Security considerations
   - Performance optimizations
   - Breaking change documentation

7. **Generate review summary** - Provide comprehensive overview:
   - Summary of changes made
   - Key components modified
   - Business impact assessment
   - Quality metrics (tests passing, lint clean)
   - Potential risks or concerns
   - Reviewer guidance and focus areas

**Review preparation goals:**
- Ensure code meets our quality standards
- Identify potential issues before PR creation
- Provide comprehensive change documentation
- Generate reviewer guidance

**Current branch:** [Will be determined from git status]

Begin review preparation now.