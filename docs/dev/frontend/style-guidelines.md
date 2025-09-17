# Style Guidelines

## Design Targets

**Primary**: Tablet landscape mode with touch screen
**Secondary**: Laptop/desktop
**Minimum**: Phone landscape mode (not portrait)

## Responsive Design

### Breakpoints
Bootstrap 4 breakpoints with tablet-first approach:
- **768px+ (md)**: Primary target - tablets
- **992px+ (lg)**: Desktops
- **1200px+ (xl)**: Large desktops

### Touch-Friendly Requirements
- **Minimum touch target**: 44x44px for all interactive elements
- **No hover dependencies**: Use click/tap interactions
- **Adequate spacing**: Between clickable elements
- **Standard gestures**: Swipe, pinch-zoom for SVGs

## Color System & Variables

### Status Colors (Traffic Light Pattern)
```css
:root {
  --status-active: #dc3545;    /* Red - Active/Alert */
  --status-recent: #fd7e14;    /* Orange - Recently active */
  --status-past: #ffc107;      /* Yellow - Past activity */
  --status-idle: #28a745;      /* Green - Idle/Safe */
  --status-unknown: #6c757d;   /* Gray - Unknown/Offline */
}
```

### Entity State Visualization
CSS classes for SVG entity styling:
- `.entity-svg.state-active` - Red with 0.8 opacity
- `.entity-svg.state-recent` - Orange with 0.6 opacity
- `.entity-svg.state-past` - Yellow with 0.4 opacity
- `.entity-svg.state-idle` - Green with 0.3 opacity

## Component Classes

### Layout Components
- `.hi-card` - Standard card styling with shadow and padding
- `.hi-card--clickable` - Clickable card with hover effects
- `.hi-toolbar` - Flexbox toolbar with actions
- `.hi-toolbar__actions` - Action buttons container

### Icon Integration
- `.hi-icon-left` - Icon positioned left of text
- `.hi-icon-right` - Icon positioned right of text
- `.hi-icon-only` - Icon without text
- `.hi-icon-spin` - Spinning animation for loading

### Interactive Elements
- `.entity-clickable` - Cursor pointer for SVG elements
- `.entity-selected` - Dashed stroke for selected entities
- `.loading-spinner` - Rotating spinner animation

## Form Styling

### Touch Optimization
- **Minimum height**: 44px for all form controls
- **Font size**: 16px minimum (prevents iOS zoom)
- **Spacing**: 1.5rem margin between form groups
- **Select padding**: Extra right padding for dropdown arrow

## Performance Guidelines

### Animation Best Practices
- **Use**: `opacity` and `transform` for smooth animations
- **Avoid**: `transition: all` - specify properties explicitly
- **Timing**: 0.3s standard transition duration

### Accessibility Features
- **Focus indicators**: 2px outline with offset
- **High contrast support**: Media query for `prefers-contrast: high`
- **Keyboard navigation**: Visible focus states

## Key CSS Files
- `src/hi/static/css/base.css` - Core styles and variables
- `src/hi/static/css/components.css` - Component-specific styles
- `src/hi/static/css/entity.css` - Entity state visualization

## Related Documentation
- [Icon System](icon-system.md)
- [Frontend Guidelines](frontend-guidelines.md)
- [Template Conventions](template-conventions.md)