---
allowed-tools: Bash, Read, TodoWrite
description: Create GitHub issues using proper templates and conventions
model: claude-3-5-sonnet-20250115
argument-hint: [type] [title]
---

Create GitHub issue of type "$1" with title "$2" using proper templates and conventions:

## GitHub Issue Creation Process

Execute standardized issue creation with proper templates:

1. **Use TodoWrite to plan issue creation** - Track template selection and validation

2. **Validate issue type and template** - Ensure proper template selection:

   **Available Issue Types and Templates:**
   ```bash
   # Template Mapping
   bug        → .github/ISSUE_TEMPLATE/bug_report.md
   feature    → .github/ISSUE_TEMPLATE/feature_request.md
   docs       → .github/ISSUE_TEMPLATE/documentation.md
   ops        → .github/ISSUE_TEMPLATE/operations.md
   refactor   → .github/ISSUE_TEMPLATE/refactor.md
   tests      → .github/ISSUE_TEMPLATE/tests.md
   ```

3. **Validate title format** - Ensure proper title conventions:
   ```bash
   # Title Format Examples
   bug:      "[Bug] Weather service timeout in production"
   feature:  "[Feature] Add weather alerts system"
   docs:     "[Docs] Update API documentation for weather endpoints"
   ops:      "[Ops] Improve Docker build performance"
   refactor: "[Refactor] Consolidate entity status logic"
   tests:    "[Tests] Add integration tests for weather service"
   ```

4. **Create issue using GitHub CLI** - Use proper template syntax with error handling:
   ```bash
   # Map issue type to template filename
   case "$1" in
     bug) TEMPLATE="bug_report.md" ;;
     feature) TEMPLATE="feature_request.md" ;;
     docs) TEMPLATE="documentation.md" ;;
     ops) TEMPLATE="operations.md" ;;
     refactor) TEMPLATE="refactor.md" ;;
     tests) TEMPLATE="tests.md" ;;
     *) echo "Invalid issue type: $1"; exit 1 ;;
   esac

   # Create issue with proper template
   gh issue create --template "$TEMPLATE" --title "$2"
   ```

   **Template to File Mapping:**
   ```bash
   # Issue type → Template file
   bug       → bug_report.md
   feature   → feature_request.md
   docs      → documentation.md
   ops       → operations.md
   refactor  → refactor.md
   tests     → tests.md
   ```

5. **Verify issue creation** - Confirm successful creation:
   ```bash
   # Get the created issue number
   gh issue list --limit 1 --state open
   ```

6. **Provide issue information** - Return issue details:
   - Issue number for reference
   - Issue URL for direct access
   - Corresponding branch naming pattern
   - Next steps for development

## Issue Type Guidelines

### **Bug Reports** (`bug`)
- **Template**: `bug_report.md`
- **Title**: `[Bug] Description of the problem`
- **Label**: `bug`
- **Branch**: `bugfix/##-description`
- **Use for**: Unexpected behavior, errors, failures

### **Feature Requests** (`feature`)
- **Template**: `feature_request.md`
- **Title**: `[Feature] Description of new functionality`
- **Label**: `enhancement`
- **Branch**: `feature/##-description`
- **Use for**: New functionality, enhancements, capabilities

### **Documentation** (`docs`)
- **Template**: `documentation.md`
- **Title**: `[Docs] Description of documentation need`
- **Branch**: `docs/##-description`
- **Use for**: Documentation improvements, guides, explanations

### **Operations** (`ops`)
- **Template**: `operations.md`
- **Title**: `[Ops] Description of infrastructure/deployment need`
- **Branch**: `ops/##-description`
- **Use for**: CI/CD, deployment, infrastructure, tooling

### **Refactoring** (`refactor`)
- **Template**: `refactor.md`
- **Title**: `[Refactor] Description of code improvement`
- **Branch**: `refactor/##-description`
- **Use for**: Code quality improvements without behavior changes

### **Testing** (`tests`)
- **Template**: `tests.md`
- **Title**: `[Tests] Description of testing improvement`
- **Branch**: `tests/description` (no issue number required)
- **Use for**: Test coverage, test quality, testing infrastructure

## Integration with Planning Workflows

### **Multi-Issue Breakdown** (from `/plan` command)
When `/plan` recommends splitting work into multiple issues:
```bash
# Create related issues in sequence
/createissue feature "Weather alerts core system"
/createissue feature "Weather alerts UI components"
/createissue docs "Weather alerts API documentation"
```

### **Design-Heavy Issue Splitting** (from `/investigate` command)
When `/investigate` identifies design + implementation split:
```bash
# Create design phase issue
/createissue feature "Weather dashboard - Design & Wireframes"
# Implementation issue created after design approval
/createissue feature "Weather dashboard - Implementation"
```

## Quality Validation

### **Title Format Validation**
- **Must include type prefix**: `[Bug]`, `[Feature]`, etc.
- **Descriptive and specific**: Avoid generic titles
- **Consistent with template conventions**

### **Template Selection Validation**
- **Verify template exists**: Check `.github/ISSUE_TEMPLATE/` directory
- **Match issue type to template**: Ensure proper template mapping
- **Follow label conventions**: Templates automatically apply correct labels

### **Branch Naming Preparation**
Provide corresponding branch naming guidance:
```bash
# For the created issue #123
git checkout -b feature/123-weather-alerts
git checkout -b bugfix/123-timeout-fix
git checkout -b docs/123-api-documentation
```

## Error Handling

### **Invalid Issue Type**
If `$1` doesn't match available templates:
- List available issue types
- Suggest closest match
- Provide template selection guidance

### **Invalid Title Format**
If `$2` doesn't follow conventions:
- Show expected format for issue type
- Provide title formatting examples
- Suggest improvements

### **GitHub CLI Issues**
If `gh issue create` fails:
- Verify GitHub authentication
- Check repository permissions
- Validate template file existence

**Command Integration:**
- Integrates with `/plan` for multi-issue strategies
- Supports `/investigate` issue splitting recommendations
- Prepares for `/pickup` workflow execution

**Issue Type:** $1
**Title:** "$2"
**Template:** $1.md (from `.github/ISSUE_TEMPLATE/`)

Begin GitHub issue creation process now.