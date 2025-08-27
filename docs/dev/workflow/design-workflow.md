# Design Workflow

> **Role**: Process Documentation  
> **Purpose**: Workflow for design-focused issues including UX improvements, UI redesigns, mockups, and wireframes

## Design Work Documentation Process

When working on design-focused GitHub issues (UX improvements, UI redesigns, mockups, wireframes, interaction design):

### Local Work Directory Structure

All design work products are kept local and **never committed to the repository**:

```bash
# All design work goes in data/design (git ignored)
data/design/issue-{number}/
├── mockup.html                    # Interactive HTML mockups
├── architecture.md                # Technical architecture docs  
├── interaction-patterns.md        # UX interaction specifications
├── design-summary.md              # Executive summary
└── other-design-artifacts.*       # Additional files as needed
```

### Design Workflow Process

1. **Create issue subdirectory**: `mkdir -p data/design/issue-{number}`
2. **Iterate locally**: Create, refine, and iterate on design documents locally
3. **No repository commits**: Design work products stay local only (`data/` is in .gitignore)
4. **Post to GitHub issue**: Share stable versions via GitHub issue comments/attachments

### Repository vs GitHub Issue Organization

**Repository Scope** (source of truth):
- Implementation code and templates
- Architecture documentation that affects multiple systems
- Coding standards and technical guidelines

**GitHub Issue Scope** (design iteration and review):
- Design mockups and wireframes
- UX interaction specifications
- Design decision rationale and trade-offs
- Stakeholder review and approval process

### GitHub Issue Documentation Pattern

Use this structure when posting design deliverables:

```markdown
## Phase X Design Complete - Ready for Review

Brief summary of key decisions and deliverables:

1. **Interactive Mockup** (attached) - HTML file for browser viewing
2. **Architecture Document** (comment below) - Technical specifications
3. **Interaction Patterns** (comment below) - UX behavior definitions

### Key Design Decisions
- Decision 1: Rationale
- Decision 2: Rationale
- Decision 3: Rationale

### Implementation Notes
- Technical considerations
- New development required
- Forward compatibility hooks

Ready for stakeholder review and implementation planning.
```

### Content Organization Strategy

**Visual Deliverables** → GitHub Issue Attachments:
- Interactive HTML mockups
- Images, screenshots, diagrams
- **Benefits**: Can be downloaded and viewed directly in browsers

**Textual Content** → GitHub Issue Comments:
- Architecture specifications (markdown)
- Interaction patterns documentation (markdown)
- Design decision rationale (markdown)
- **Benefits**: Searchable, linkable, quotable for discussion

### Design Iteration Workflow

1. **Initial Research**: Analyze current implementation and requirements
2. **Create Local Workspace**: Set up `data/design/issue-{number}/` directory
3. **Design Iteration**: Create and refine mockups and documentation locally
4. **Checkpoint Reviews**: Post important versions to GitHub issue for feedback
5. **Final Documentation**: Post complete deliverables when design is stable
6. **Implementation Handoff**: Provide clear specifications for development phase

### Design Deliverable Types

**HTML Mockups**:
- Interactive demonstrations of proposed UX
- ~700px modal examples with realistic content
- Touch-friendly interaction patterns
- Visual state management examples

**Architecture Documents**:
- Technical implementation approach
- Component reusability strategy
- Template organization and naming
- CSS class naming and namespace planning

**Interaction Patterns**:
- Comprehensive touch interaction flows
- State management behavior
- Error handling patterns
- Accessibility considerations

**Design Summaries**:
- Executive overview of key decisions
- Implementation complexity assessment
- Forward compatibility planning
- Cross-issue relationship documentation

### Multi-Phase Design Strategy

For complex design issues, break work into phases:

**Phase 1 - Design & Architecture**:
- Complete design iteration locally
- Post comprehensive deliverables to GitHub issue
- Get stakeholder approval before implementation

**Phase 2+ - Implementation**:
- Use design deliverables as implementation specification
- Create feature branch for development work
- Follow standard development workflow from approved design

### Integration with Development Workflow

**Branch Strategy**:
- Design phase: Feature branch for any temporary investigation code
- Implementation phase: Same or new feature branch for actual development

**Testing Integration**:
- Design phase: No automated testing required
- Implementation phase: Full test coverage per standard guidelines

**Documentation Updates**:
- Design decisions remain in GitHub issues (audit trail)
- Implementation details go in code and architecture docs per standards

### Quality Assurance

**Design Review Checkpoints**:
- [ ] All deliverables posted to GitHub issue
- [ ] Key design decisions documented with rationale
- [ ] Forward compatibility considerations addressed
- [ ] Implementation complexity assessed
- [ ] Stakeholder approval obtained

**Implementation Readiness**:
- [ ] Clear technical specifications provided
- [ ] Component architecture defined
- [ ] Interaction patterns fully specified
- [ ] Integration points identified

## Benefits of This Workflow

### Repository Cleanliness
- No work-in-progress design artifacts clutter the codebase
- Clear separation between design iteration and implementation
- Source of truth remains focused on implemented solutions

### Design Iteration Efficiency
- Local work allows rapid iteration without commits
- Easy to discard failed approaches
- No merge conflicts during design exploration

### Stakeholder Review Effectiveness
- Visual deliverables easily accessible via attachments
- Comprehensive documentation provides context
- Clear approval gates before implementation work

### Implementation Quality
- Complete specifications reduce implementation ambiguity
- Forward compatibility planning prevents technical debt
- Reusable component strategy improves maintainability

## Related Documentation

- [Workflow Guidelines](workflow-guidelines.md) - Standard development workflow
- [Documentation Standards](documentation-standards.md) - General documentation philosophy
- [Frontend Guidelines](../frontend/frontend-guidelines.md) - UI implementation patterns
- [Architecture Overview](../shared/architecture-overview.md) - System architecture context