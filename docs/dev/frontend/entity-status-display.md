# Entity Status Display

## Quick Reference

### Key Files
- **CSS**: Status colors defined in CSS custom properties (`:root` section)
- **JavaScript**: `polling.js` handles real-time updates via `/api/status`
- **Templates**: Entity elements need `data-entity-id` attributes for updates
- **Backend**: `StatusDisplayManager` calculates display states from sensor data

## Overview

The entity status display system provides visual feedback for entity states through dynamic CSS classes, SVG styling, and real-time updates. This document covers the frontend implementation details for displaying entity status visually.

## Visual Display Implementation

Entity visual representation is implemented through three main approaches:

### 1. CSS Class Mapping

The system takes normalized sensor values and applies them as CSS class names to SVG elements. This allows CSS rules to dynamically adjust visual display for well-known sensor values.

```css
/* Entity state CSS classes */
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

.entity-svg.state-unknown {
  fill: var(--status-unknown);
  fill-opacity: 0.2;
}
```

### 2. Predefined Icon Variants

For well-known sensor values, the system can swap between predefined SVG icons to represent different states:

```html
<!-- Base entity icon -->
<use href="#icon-motion-sensor-idle" class="entity-icon" />

<!-- Active state icon -->
<use href="#icon-motion-sensor-active" class="entity-icon" />
```

### 3. Color Scheme Mapping

The system maps sensor values to color schemes applied via SVG fill, stroke, and opacity attributes. This is predominantly used for area entities (closed SVG paths) to show activity levels.

```javascript
// Color scheme application
function applyColorScheme(element, colorData) {
    element.style.fill = colorData.fillColor;
    element.style.stroke = colorData.strokeColor;
    element.style.opacity = colorData.opacity;
    element.style.strokeWidth = colorData.strokeWidth;
}
```

## Status Color System

### Color Variables

Define status colors using CSS custom properties:

```css
:root {
  /* Status colors following traffic light metaphor */
  --status-active: #dc3545;      /* Red - Active/Alert */
  --status-recent: #fd7e14;      /* Orange - Recently active */
  --status-past: #ffc107;        /* Yellow - Past activity */
  --status-idle: #28a745;        /* Green - Idle/Safe */
  --status-unknown: #6c757d;     /* Gray - Unknown/Offline */
}
```

### Visual State Progression

The value decaying system creates a visual "cooling off" effect through color transitions:

**Color Progression**: Active (red) → Recent (orange) → Past (yellow) → Idle (green/gray)

```css
/* Smooth transitions between states */
.entity-svg {
  transition: fill 0.3s ease, opacity 0.3s ease;
}

/* State-specific styling with opacity variations */
.entity-active { 
  fill: var(--status-active); 
  opacity: 1.0; 
}
.entity-recent { 
  fill: var(--status-recent); 
  opacity: 0.8; 
}
.entity-past { 
  fill: var(--status-past); 
  opacity: 0.6; 
}
.entity-idle { 
  fill: var(--status-idle); 
  opacity: 0.4; 
}
```

## Client-Server Status Updates

### Polling System Implementation

The JavaScript `polling.js` module handles real-time status updates through server polling:

### Server Response Format

The server returns status updates in a standardized JSON format:

### Element Targeting and Updates

The polling system uses CSS class names and data attributes to target elements:

## Workflow 1: Adding Status Display to New Entity Template

**Scenario**: You have a new entity type (smart thermostat) that needs status display functionality in location views.

**Step-by-Step Implementation:**

1. **Plan the Visual States** (Domain consideration)
   ```python
   # Thermostat states we want to display:
   # - heating (red) - actively heating
   # - cooling (blue) - actively cooling  
   # - idle (green) - maintaining temperature
   # - offline (gray) - no communication
   ```

2. **Define Status CSS Classes** ([CSS Class Mapping](#css-class-mapping))
   ```css
   /* Add to your CSS file */
   .entity-svg.thermostat-heating {
     fill: var(--status-active);
     stroke: #cc0000;
   }
   
   .entity-svg.thermostat-cooling {
     fill: #0066cc;
     stroke: #004499;
   }
   
   .entity-svg.thermostat-idle {
     fill: var(--status-idle);
     stroke: #006600;
   }
   
   .entity-svg.thermostat-offline {
     fill: var(--status-unknown);
     stroke: #666666;
   }
   ```

3. **Update Backend Status Logic** ([Server Response Format](#server-response-format))
   ```python
   # In your entity model or status manager
   class ThermostatStatusCalculator:
       def get_status_css_classes(self, thermostat_entity):
           current_state = thermostat_entity.get_current_state('hvac_mode')
           
           if not current_state or current_state.is_stale():
               return ['thermostat-offline']
           
           mode = current_state.value
           if mode == 'heating':
               return ['thermostat-heating']
           elif mode == 'cooling':
               return ['thermostat-cooling']
           elif mode == 'idle':
               return ['thermostat-idle']
           else:
               return ['thermostat-offline']
   ```

4. **Update Template Integration** ([Template Integration](#template-integration))
   ```django
   <!-- In your location view template -->
   <g class="entity-group" data-entity-id="{{ thermostat.id }}">
     <use href="#icon-thermostat" 
          class="entity-svg {{ thermostat.get_status_css_classes|join:' ' }}"
          transform="translate({{ thermostat.position.x }}, {{ thermostat.position.y }})"/>
   </g>
   ```

5. **Test Status Updates** ([Polling System Implementation](#polling-system-implementation))
   ```javascript
   // Verify polling picks up thermostat status changes
   // Check browser Network tab for /api/status requests
   // Manually trigger state change and observe visual update
   ```

**Expected Result**: Thermostat icons change color in real-time based on heating/cooling state.

## Related Documentation
- Status calculation logic: [Domain Guidelines](../domain/domain-guidelines.md#status-display-system)
- Style guidelines: [Style Guidelines](style-guidelines.md)
- Template conventions: [Template Conventions](template-conventions.md)
- Frontend patterns: [Frontend Guidelines](frontend-guidelines.md)
