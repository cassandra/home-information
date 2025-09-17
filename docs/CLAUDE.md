# CLAUDE.md

This file provides AI-specific guidance for Claude Code when working with this repository.

## Development Philosophy - Our Prime Directive

In all code we write, we strive for extremely well factored code. We are thoughtful about responsibility boundaries, encapsulation, readability and maintainability. We do not write the first code we can think of to solve the problem - we find a well factored version that does the job.

## Custom Command Ecosystem

This project has extensive custom commands for workflow automation. Use them proactively:

### Strategic & Planning Commands
- **`/plan 123`** - Strategic work breakdown and issue planning
- **`/design 123`** - Design phase with HTML mockups and interaction docs
- **`/createissue type "title"`** - Create GitHub issues with proper templates

### Development Execution Commands
- **`/execute 123`** - Complete issue-to-PR orchestration with sub-agent coordination
- **`/pickup 123`** - Issue assignment and branch setup
- **`/investigate 123`** - Deep codebase analysis and implementation planning

### Quality & Maintenance Commands
- **`/commit "message"`** - Smart commits following project standards
- **`/review`** - Pre-PR quality preparation with expert analysis
- **`/pr "title"`** - Pull request creation with proper template
- **`/respond 112`** - Systematic PR feedback response
- **`/fixtests`** - Test failure analysis and remediation
- **`/cleanup branch`** - Post-merge branch cleanup

### Specialized Commands
- **`/debug "issue"`** - AI-assisted debugging and troubleshooting
- **`/refactor Class`** - Expert refactoring planning
- **`/release 1.2.3`** - Complete release process automation
- **`/icon "concept"`** - Find existing icon or create new one

**Command files:** `.claude/commands/*.md` contain detailed specifications.

## AI-Specific Guidelines

### TodoWrite Tool Usage (Mandatory)
- **ALWAYS use TodoWrite** for complex tasks and multi-step work
- Plan before executing, track progress throughout
- Mark tasks completed immediately when finished
- Break down complex issues into trackable phases

### Sub-Agent Coordination
- **Use specialized agents proactively** - they provide expert-level analysis
- **Launch agents in parallel** when possible for efficiency
- **Be specific about scope** - detailed context yields better results
- **Chain agents** - use output from one as input to another

**Available agents:** `general-purpose`, `backend-dev`, `frontend-dev`, `domain-expert`, `test-engineer`, `integration-dev`, `code-quality`

### Project Documentation Structure
- **Authoritative docs:** `docs/dev/` contains official workflow, testing, and coding standards
- **Commands reference these docs** - don't duplicate content
- **When in doubt:** Check `docs/dev/workflow/workflow-guidelines.md` for process questions

### AI Behavior Patterns
- **Quality over speed** - use well-factored solutions, not first working code
- **Reference documentation** - commands point to authoritative sources
- **Escalate when stuck** - pause after 3 attempts on difficult problems
- **No Claude attribution** - keep commit messages and PR descriptions project-focused

## Core Development Standards

### Essential Technical Requirements
- **All files must end with newline** (prevents W391 linting failures)
- **All imports at file top** (never inside functions/methods)
- **Use `/bin/rm` not `rm`** (avoid interactive prompts)

### Quality Gates (Enforced by Commands)
- **`make lint`** must show no output before any PR
- **`make test`** must pass before any PR
- **Use project templates** for PRs and follow `.github/PULL_REQUEST_TEMPLATE.md`
- **Use project templates** for Issues and follow those in `.github/ISSUE_TEMPLATE/*`

### Workflow Integration
- **Start with commands** - use `/execute 123` for standard workflows
- **Use individual commands** for precise control or unusual cases
- **Follow command guidance** - they reference authoritative documentation
- **Trust the process** - commands implement project best practices

## Key Project References

- **Project Structure** `docs/dev/shared/project-structure.md`
- **Workflows:** `docs/dev/workflow/workflow-guidelines.md`
- **Testing:** `docs/dev/testing/testing-guidelines.md`
- **Coding Standards:** `docs/dev/shared/coding-standards.md`
- **Architecture:** `docs/dev/shared/architecture-overview.md`

Commands automatically reference these documents - no need to read them manually unless working outside command workflows.
