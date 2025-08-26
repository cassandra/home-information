# Style Guidelines

## Responsiveness

The predominant use of this app is in a tablet in landscape mode with a touch screen. Secondary usage would be a laptop or desktop. For mobile (phone) devices, we only need for it to render well enough to be usable in the phone's landscape mode. We can assume that we do not have to support very narrow widths of a phone in portrait mode.

### Breakpoint Strategy

```scss
// Bootstrap 4 breakpoints we use
// Small devices (landscape phones, 576px and up)
@media (min-width: 576px) { ... }

// Medium devices (tablets, 768px and up) - PRIMARY TARGET
@media (min-width: 768px) { ... }

// Large devices (desktops, 992px and up)
@media (min-width: 992px) { ... }

// Extra large devices (large desktops, 1200px and up)
@media (min-width: 1200px) { ... }
```

### Touch-Friendly Design

1. **Minimum Touch Target**: 44x44px for all interactive elements
2. **Spacing**: Adequate spacing between clickable elements
3. **Hover States**: Don't rely on hover - use click/tap interactions
4. **Gestures**: Support standard touch gestures (swipe, pinch-zoom for SVGs)

## Color System

### Status Colors

Consistent color usage for entity states:

```css
:root {
  /* Status colors following traffic light metaphor */
  --status-active: #dc3545;      /* Red - Active/Alert */
  --status-recent: #fd7e14;      /* Orange - Recently active */
  --status-past: #ffc107;        /* Yellow - Past activity */
  --status-idle: #28a745;        /* Green - Idle/Safe */
  --status-unknown: #6c757d;     /* Gray - Unknown/Offline */
  
  /* Alert levels */
  --alert-critical: #dc3545;     /* Red */
  --alert-warning: #ffc107;      /* Yellow */
  --alert-info: #17a2b8;        /* Cyan */
  --alert-success: #28a745;      /* Green */
}
```

### Theme Variables

```css
:root {
  /* Primary palette */
  --primary: #007bff;
  --secondary: #6c757d;
  --success: #28a745;
  --info: #17a2b8;
  --warning: #ffc107;
  --danger: #dc3545;
  
  /* UI elements */
  --border-color: #dee2e6;
  --shadow: 0 0.125rem 0.25rem rgba(0,0,0,0.075);
  --shadow-lg: 0 1rem 3rem rgba(0,0,0,0.175);
}
```

## Component Styling

### Cards and Panels

```css
.hi-card {
  background: white;
  border: 1px solid var(--border-color);
  border-radius: 0.25rem;
  box-shadow: var(--shadow);
  padding: 1rem;
  margin-bottom: 1rem;
}

.hi-card--clickable {
  cursor: pointer;
  transition: box-shadow 0.2s;
}

.hi-card--clickable:hover {
  box-shadow: var(--shadow-lg);
}
```

### Buttons

Extend Bootstrap buttons with consistent icon usage:

```css
.btn {
  display: inline-flex;
  align-items: center;
  min-height: 44px; /* Touch-friendly */
  padding: 0.5rem 1rem;
}

.hi-icon-left {
  margin-right: 0.5rem;
}

.hi-icon-right {
  margin-left: 0.5rem;
}
```

### Forms

Touch-optimized form controls:

```css
.form-control {
  min-height: 44px;
  font-size: 16px; /* Prevents zoom on iOS */
}

.form-group {
  margin-bottom: 1.5rem; /* More spacing for touch */
}

select.form-control {
  padding-right: 2rem; /* Room for dropdown arrow */
}
```

## SVG Styling

### Entity State Visualization

```css
/* Base entity styling */
.entity-svg {
  transition: fill 0.3s, stroke 0.3s, opacity 0.3s;
}

/* State-based styling */
.entity-svg.state-active {
  fill: var(--status-active);
  fill-opacity: 0.8;
}

.entity-svg.state-recent {
  fill: var(--status-recent);
  fill-opacity: 0.6;
}

.entity-svg.state-past {
  fill: var(--status-past);
  fill-opacity: 0.4;
}

.entity-svg.state-idle {
  fill: var(--status-idle);
  fill-opacity: 0.3;
}
```

### Interactive SVG Elements

```css
.entity-clickable {
  cursor: pointer;
}

.entity-clickable:hover {
  stroke: var(--primary);
  stroke-width: 2;
}

.entity-selected {
  stroke: var(--primary);
  stroke-width: 3;
  stroke-dasharray: 5,5;
}
```

## Layout Patterns

### Grid System

Use Bootstrap's grid with tablet-first approach:

```html
<!-- Tablet-optimized layout -->
<div class="row">
  <div class="col-md-8">
    <!-- Main content - larger on tablet -->
  </div>
  <div class="col-md-4">
    <!-- Sidebar - narrower on tablet -->
  </div>
</div>
```

### Flex Utilities

Use flexbox for component layouts:

```css
.hi-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem;
  background: #f8f9fa;
  border-bottom: 1px solid var(--border-color);
}

.hi-toolbar__actions {
  display: flex;
  gap: 0.5rem;
}
```

## Animation and Transitions

### Performance Considerations

```css
/* Use transform and opacity for smooth animations */
.modal {
  transition: opacity 0.3s, transform 0.3s;
}

.modal.show {
  opacity: 1;
  transform: translateY(0);
}

/* Avoid animating expensive properties */
/* Bad: transition: all 0.3s; */
/* Good: transition: opacity 0.3s, transform 0.3s; */
```

### Loading States

```css
.loading-spinner {
  display: inline-block;
  width: 1rem;
  height: 1rem;
  border: 2px solid #f3f3f3;
  border-top: 2px solid var(--primary);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}
```

## Accessibility

### Focus Indicators

```css
/* Visible focus for keyboard navigation */
:focus {
  outline: 2px solid var(--primary);
  outline-offset: 2px;
}

/* Remove outline for mouse users */
:focus:not(:focus-visible) {
  outline: none;
}
```

### High Contrast Support

```css
@media (prefers-contrast: high) {
  :root {
    --border-color: #000;
    --shadow: 0 0 0 1px #000;
  }
  
  .btn {
    border: 2px solid currentColor;
  }
}
```

## Print Styles

```css
@media print {
  /* Hide navigation and controls */
  .hi-toolbar,
  .hi-sidebar,
  .btn-group {
    display: none !important;
  }
  
  /* Ensure content fits on page */
  .hi-main-content {
    width: 100%;
    margin: 0;
  }
  
  /* Avoid page breaks in cards */
  .hi-card {
    page-break-inside: avoid;
  }
}
```

## Related Documentation
- Icon system: [Icon System](icon-system.md)
- Frontend guidelines: [Frontend Guidelines](frontend-guidelines.md)
- Template conventions: [Template Conventions](template-conventions.md)
- UI testing: [UI Testing](ui-testing.md)