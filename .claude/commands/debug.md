---
allowed-tools: Bash, Read, TodoWrite, Grep, Glob, Task
description: Debug issues with AI-assisted analysis and troubleshooting
model: claude-3-5-sonnet-20250115
argument-hint: [description]
---

Debug issue: "$1"

## AI-Assisted Debugging Process

Execute systematic debugging approach:

1. **Use TodoWrite to plan debugging investigation** - Track analysis steps
   - Read `docs/CLAUDE.md` for AI escalation patterns and sub-agent coordination
   - Follow 3-attempt escalation rule for difficult problems

2. **Gather initial information** - Collect debugging context:
   ```bash
   # Check current system state
   git status
   git branch --show-current

   # Check recent logs if applicable
   # (Adapt based on issue type - web logs, test output, etc.)
   ```

3. **Search for related patterns** - Find similar issues:
   - Use Grep to search for error messages in codebase
   - Look for similar function names or patterns
   - Check test files for related test cases
   - Search documentation for known issues

4. **Use specialized debugging agents** - Get expert analysis:
   - **Use Task tool with general-purpose agent**: Broad pattern search and cross-domain analysis
   - **Use Task tool with backend-dev agent**: Django/database debugging (if applicable)
   - **Use Task tool with frontend-dev agent**: Template/JavaScript debugging (if applicable)
   - **Use Task tool with integration-dev agent**: External API/integration debugging (if applicable)
   - **Use Task tool with test-engineer agent**: Test failure analysis (if applicable)

5. **Analyze error patterns** - Identify:
   - Root cause candidates
   - Common failure points
   - Related components that might be affected
   - Similar issues resolved in the past
   - Configuration or environment factors

6. **Generate debugging strategy** - Create action plan:
   - Step-by-step investigation approach
   - Diagnostic commands to run
   - Code sections to examine
   - Tests to run for validation
   - Potential quick fixes to try

7. **Identify debugging approaches** - Suggest multiple strategies:
   - **Immediate fixes**: Quick solutions if obvious
   - **Systematic investigation**: Detailed debugging steps
   - **Isolation testing**: Ways to isolate the problem
   - **Logging/instrumentation**: How to gather more data
   - **Rollback options**: Safe ways to revert if needed

8. **Provide troubleshooting guidance** - Include:
   - Most likely causes ranked by probability
   - Diagnostic steps with expected outcomes
   - Commands to run for further investigation
   - Warning signs to watch for
   - When to escalate or seek additional help

**Debugging target:** "$1"
**Goal:** Systematic analysis and actionable troubleshooting plan

**Common debugging areas to investigate:**
- Configuration files and environment variables
- Recent code changes that might be related
- Dependencies and external service status
- Database state and migrations
- Log files and error messages
- Test results and coverage

Begin debugging investigation now.