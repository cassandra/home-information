# Business Logic

## Status Display Logic

Visual representation based on sensor readings:
- CSS class mapping from sensor values
- Color scheme calculation for SVG elements  
- Icon variant selection based on state

For frontend implementation of visual display including CSS classes, colors, and status updates, see [Entity Status Display](../frontend/entity-status-display.md).

## Value Decaying System

Temporal status calculation for activity-based entities:
- Active → Recent → Past → Idle progression
- Configurable time thresholds
- Visual "cooling off" effect

## Entity State Priority

Multiple sensor priority resolution:
- Location view type determines priority order
- Highest priority state controls visual display
- Different priorities for security vs climate views

## Collection Aggregation

Logical grouping with aggregate status:
- Status calculation from member entities
- Critical/Active/Idle hierarchy
- Positioned and unpositioned entity support

## Security State Transitions

Business rules for security system states:
- State transition validation
- Notification requirements
- Auto-change permissions

## Related Documentation
- Domain guidelines: [Domain Guidelines](domain-guidelines.md)
- Entity patterns: [Entity Patterns](entity-patterns.md)