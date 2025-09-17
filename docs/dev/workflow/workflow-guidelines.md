# Workflow Guidelines

## Branching Strategy

- **Main Branch** (`master`): Stable, production-ready code (*do not touch*)
- **Development Branch** (`staging`): Active development, PR target
- **Feature Branches**: Individual development work

## Branch Naming Conventions

| Type     | Issue? | Branch Pattern                      | Notes                |
|----------|--------|-------------------------------------|----------------------|
| feature  | YES    | feature/$(ISSUE_NUM)-${MNEMONIC}    | New development      |
| bugfix   | YES    | bugfix/$(ISSUE_NUM)-${MNEMONIC}     | Bug fixes            |
| docs     | YES    | docs/$(ISSUE_NUM)-${MNEMONIC}       | Documentation        |
| ops      | YES    | ops/$(ISSUE_NUM)-${MNEMONIC}        | Deployment/CI        |
| tests    | NO     | tests/${MNEMONIC}                   | Test-only changes    |
| refactor | YES    | refactor/$(ISSUE_NUM)-${MNEMONIC}   | No behavior changes  |
| tweak    | NO     | tweak/${MNEMONIC}                   | Small obvious fixes  |

## Development Workflow

### 1. Ensure Latest Staging
```bash
git checkout staging
git pull origin staging
```

### 2. Create Feature Branch
```bash
git checkout -b feature/42-entity-icons
```

### 3. Development and Commits
- Make logical commits with clear messages
- Focus on **what** changed and **why**, not implementation details
- Keep commits focused and atomic
- Do not add any extra attributions.
- Do not uses marketing-like language

### 4. Push Branch (at checkpoints and when done)
```bash
git push -u origin feature/42-entity-icons
```

### 5. Create Pull Request
Use pull request template: `.github/PULL_REQUEST_TEMPLATE.md`:

Use GitHub CLI or web interface:
```bash
gh pr create --title "Add entity icon system" --body "$(cat <<'EOF'
## Pull Request: Add Entity Icon System

### Issue Link
Closes #42

### Summary
- Implement standardized icon system for entities
- Add icon template tag with size and styling options
- Update entity templates to use new icon system

### Testing
- [ ] Tests pass
- [ ] Icon rendering verified in UI
- [ ] Multiple size variants tested

### Documentation
- [ ] Updated template documentation
- [ ] Added icon usage examples
EOF
)"
```

## Multi-Phase Implementation Strategy

For complex issues involving multiple aspects or trade-offs:

### Core Methodology

1. **Analyze and Break Down**: Identify distinct phases
   - Phase 1: Simple, reliable solution addressing core issue
   - Phase 2+: Advanced optimizations, UX improvements, edge cases

2. **Implement Incrementally**: Complete phases sequentially  
   - Complete Phase 1 first - ensure issue is FULLY RESOLVED
   - Commit and push Phase 1 (but don't create PR yet)
   - Wait for feedback before proceeding to Phase 2

3. **Communication**: Post investigation findings and phase breakdown to GitHub issue

4. **Benefits**:
   - Early validation of approach
   - Natural checkpoints for review
   - Core functionality before optimizations
   - Independent value delivery per phase

### Key Principles
1. **Always solve core issue first** - Phase 1 must fully resolve the bug
2. **Incremental value delivery** - Each phase independently valuable
3. **Natural stopping points** - Complete phases are good moments for review
4. **No PR until complete** - Unless explicitly asked

## Commit Message Standards

**Good examples:**
```
Fix weather module test failures and improve WMO units handling
Add support for temperature offset unit arithmetic in Pint
Remove invalid AlertUrgency.PAST enum value for weather alerts
```

**MUST NOT:**
- Claude Code attribution or co-author tags
- Implementation details in commit messages

**SHOULD NOT:**
- Generic messages like "update code" or "fix bug"
- Flowery or marketing-like boasts about the changes

## Pre-PR Requirements

**MANDATORY checks before creating any PR:**

```bash

# 1. Run code quality check (must pass with no output)
cd $PROJ_ROOT ; make lint
# 2. Run full test suite (must pass)
cd $PROJ_ROOT ; make test
```

Both checks must pass before PR creation. Fix all issues first. Run `make lint` first because it is faster and any lint changes will also require re-running `make test`.

### PR Review Process

- **Squash and Merge**: Default for most PRs
- **Rebase and Merge**: For well-structured PRs needing commit history

## Post-PR Cleanup

**After PR is merged**, clean up local environment:

1. **Verify PR merged**: `gh pr view --json state,mergedAt`
2. **Switch to staging**: `git checkout staging`  
3. **Pull latest changes**: `git pull origin staging`
4. **Delete feature branch**: `git branch -d feature/42-entity-icons`
5. **Verify clean state**: `git status`

## Release Process Integration

See [Release Process](release-process.md) for detailed release procedures.

## Related Documentation
- Release procedures: [Release Process](release-process.md)
- Rollback procedures: [Rollback Process](rollback-process.md)
- Documentation standards: [Documentation Standards](documentation-standards.md)
- Design procedures: [Design Workflow](design-workflow.md)
