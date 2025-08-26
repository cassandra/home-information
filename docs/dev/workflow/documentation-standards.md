# Documentation Standards

## Documentation Philosophy

Documentation comes in two flavors: work-in-progress and source of truth. All work-in-progress docs live outside the repository in GitHub issues, commit messages and PR requests.

In-repository documentation comes in two types: markdown (`docs` directory) and in code modules (everywhere else).

**No Redundancy**: A markdown document should not repeat what is in code. Refer to the code for details if needing to discuss the module at a higher-level.

**Appropriate Location**: Implementaion details for a single module belong as comments in the module.  Markdown is for higher-level explanation and inter-module interaction patterns and concepts.

### Role-Based Organization

Documentation is organized by specialist roles:
- **Shared**: Common reference material used across roles
- **Testing**: Testing patterns, anti-patterns, and best practices
- **Frontend-UI**: Templates, styling, JavaScript, and UI patterns
- **Backend**: Django models, views, business logic, and architecture
- **Integrations**: External service integration patterns and gateways
- **Domain**: Domain modeling, business rules, and core concepts
- **Process-Docs**: Workflow, releases, setup, and procedures

### Documentation Structure

Each role-specific document follows this format:

```markdown
# Document Title

> **Role**: [Specialist Role]  
> **Purpose**: [Brief description of document purpose]

## Main Content Sections

### Subsection Headers
Use H3 for major subsections within content.

## Related Documentation
- Link to related documents in other roles
- Link to relevant shared reference material
```

## Cross-Reference Management

### Linking Between Roles

Use relative paths for cross-role references:

```markdown
## Related Documentation
- Testing patterns: [Testing Patterns](../testing/testing-patterns.md)
- Backend integration: [Backend Guidelines](../backend/backend-guidelines.md)
- Shared concepts: [Architecture Overview](../shared/architecture-overview.md)
```

### Maintaining Link Integrity

When updating documentation:
1. Check for broken cross-references
2. Update links when moving or renaming files
3. Ensure bidirectional linking where appropriate

## Writing Standards

### Clarity and Conciseness
- Write for the target specialist role
- Assume domain knowledge appropriate to the role
- Provide concrete examples over abstract concepts
- Use code examples to illustrate patterns

### Code Examples

Use proper syntax highlighting and context:

```python
# Good - includes context and explanation
class EntityManager(models.Manager):
    def active(self):
        """Get only active entities"""
        return self.filter(is_active=True)
```

### Formatting Conventions

- Use **bold** for important concepts
- Use `code formatting` for filenames, commands, and code elements
- Use > blockquotes for role/purpose headers
- Use bullet points for lists, numbered lists for procedures

## Content Organization

### Document Length
- Keep documents focused on their specific role
- Split large documents into logical subsections
- Cross-reference related content in other roles rather than duplicating

### Information Hierarchy
1. **Primary**: Information essential to the role
2. **Secondary**: Helpful context and related patterns
3. **Reference**: Links to detailed information in other roles

### Avoiding Duplication

- Keep common standards in shared/ directory
- Reference shared content rather than duplicating
- Use cross-references to maintain single source of truth

## Maintenance Procedures

### Regular Reviews
- Review documentation quarterly for accuracy
- Update examples when code patterns change
- Verify cross-references remain valid

### Version Control
- All documentation changes go through pull request process
- Include documentation updates with related code changes
- Treat documentation as first-class code

### Deprecation Process
1. Mark deprecated patterns with clear warnings
2. Provide migration paths to new approaches
3. Remove deprecated content after appropriate transition period

## Agent-Friendly Guidelines

### Context Efficiency
- Each role's documentation should be self-contained enough for AI agents
- Cross-references provide necessary context without overwhelming detail
- Examples should be complete and executable

### Searchability
- Use consistent terminology across documents
- Include relevant keywords in headers and content
- Provide clear section headers for easy navigation

## Related Documentation
- Workflow guidelines: [Workflow Guidelines](workflow-guidelines.md)
- All role-specific documentation serves as examples of these standards
