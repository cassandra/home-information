# Entity Status Display

## Quick Reference

### Common Tasks
- **Add new status color** → [Update CSS variables](#status-color-system) → Modify `:root` color definitions
- **Change status progression** → [Update color classes](#visual-state-progression) → Modify state-specific CSS
- **Fix polling issues** → [Check polling system](#polling-system-implementation) → Verify `/api/status` endpoint
- **Update entity styling** → [Modify CSS classes](#css-class-mapping) → Edit `.entity-svg` rules
- **Test status changes** → [Use synthetic data](#server-response-format) → Create test entities with different states

### Key Files
- **CSS**: Status colors defined in CSS custom properties (`:root` section)
- **JavaScript**: `polling.js` handles real-time updates via `/api/status`
- **Templates**: Entity elements need `data-entity-id` attributes for updates
- **Backend**: `StatusDisplayManager` calculates display states from sensor data

### Quick Fixes
| Problem | Solution | Location |
|---------|----------|----------|
| Colors not updating | Check CSS class application | [CSS Class Mapping](#css-class-mapping) |
| Polling not working | Verify StatusPoller initialization | [Polling System](#polling-system-implementation) |
| SVG elements not styling | Add proper CSS selectors | [SVG Element Handling](#svg-element-handling) |
| Status stuck on old value | Check server response format | [Server Response Format](#server-response-format) |


## Real-World Workflow Examples

### Workflow 1: Adding Status Display to New Entity Template

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

---

### Workflow 2: Debugging Status Colors Not Updating

**Scenario**: Entity status colors were working, but stopped updating after a recent template change.

**Systematic Debugging Process:**

1. **Quick Diagnostic** ([Quick Reference](#quick-reference))
   ```bash
   # Check browser dev tools - Elements tab
   # Look for data-entity-id attribute and CSS classes on entity elements
   ```

2. **Verify CSS Class Application** ([Troubleshooting - CSS Classes Not Applied](#status-colors-not-updating))
   ```javascript
   // In browser console:
   const element = document.querySelector('[data-entity-id="123"]');
   console.log('Element found:', element);
   console.log('Current classes:', element.classList);
   console.log('Data attribute:', element.getAttribute('data-entity-id'));
   ```

3. **Check Polling System** ([Troubleshooting - Polling System](#polling-system-not-working))
   ```javascript
   // Verify StatusPoller is running
   console.log('StatusPoller:', window.statusPoller);
   
   // Check network requests
   // Browser Dev Tools → Network → Filter by '/api/status'
   // Should see requests every 5 seconds
   ```

4. **Test Server Response** ([Server Response Format](#server-response-format))
   ```bash
   # Test API endpoint directly
   curl http://localhost:8411/api/status
   # Should return JSON with entities object containing your entity ID
   ```

5. **Verify CSS Variables** ([Status Color System](#status-color-system))
   ```css
   /* Check these are defined in your CSS */
   :root {
     --status-active: #dc3545;
     --status-idle: #28a745;
     /* ... other status colors */
   }
   ```

6. **Fix Template Structure** ([Template Integration](#template-integration))
   ```django
   <!-- Ensure proper structure -->
   <g data-entity-id="{{ entity.id }}">  <!-- Must have data-entity-id -->
     <path class="entity-svg {{ entity.get_status_css_classes }}">  <!-- Must have CSS classes -->
   </g>
   ```

**Common Resolution**: Missing `data-entity-id` attribute or incorrect CSS class application.

---

### Workflow 3: Implementing Custom Status Progression

**Scenario**: Create a custom "warming up" status for heating systems that shows a gradual color transition.

**Implementation Steps:**

1. **Design Color Progression** ([Visual State Progression](#visual-state-progression))
   ```css
   /* Define custom progression: cold → warming → warm → hot */
   .heating-system.state-cold { 
     fill: #4a90e2; 
     opacity: 0.6; 
   }
   .heating-system.state-warming { 
     fill: #f5a623; 
     opacity: 0.7; 
   }
   .heating-system.state-warm { 
     fill: #e94b3c; 
     opacity: 0.8; 
   }
   .heating-system.state-hot { 
     fill: #d0021b; 
     opacity: 1.0; 
   }
   ```

2. **Implement Transition Logic** ([Client-Server Status Updates](#client-server-status-updates))
   ```javascript
   class HeatingStatusManager {
     updateHeatingDisplay(entityId, temperature, targetTemp) {
       const element = document.querySelector(`[data-entity-id="${entityId}"]`);
       
       // Calculate heating state based on temperature difference
       const tempDiff = targetTemp - temperature;
       let statusClass;
       
       if (tempDiff > 5) statusClass = 'state-cold';
       else if (tempDiff > 2) statusClass = 'state-warming';
       else if (tempDiff > 0.5) statusClass = 'state-warm';
       else statusClass = 'state-hot';
       
       // Apply with smooth transition
       element.classList.remove('state-cold', 'state-warming', 'state-warm', 'state-hot');
       element.classList.add(statusClass);
     }
   }
   ```

3. **Add Smooth Transitions** ([Performance Considerations](#performance-considerations))
   ```css
   .heating-system {
     transition: fill 2s ease-in-out, opacity 1s ease-in-out;
   }
   ```

4. **Test Progression** ([Testing](#testing))
   ```javascript
   // Test all state transitions
   const heatingManager = new HeatingStatusManager();
   const testCases = [
     { temp: 65, target: 72 }, // Should be cold
     { temp: 69, target: 72 }, // Should be warming  
     { temp: 71, target: 72 }, // Should be warm
     { temp: 72, target: 72 }  // Should be hot
   ];
   
   testCases.forEach(test => {
     heatingManager.updateHeatingDisplay('test-heater', test.temp, test.target);
   });
   ```

**Expected Result**: Heating system icons smoothly transition through color progression as they approach target temperature.

---

### Workflow 4: Performance Optimization for Many Entities

**Scenario**: Location view with 100+ entities is experiencing slow status updates and browser lag.

**Optimization Process:**

1. **Identify Performance Bottlenecks** ([Performance Considerations](#performance-considerations))
   ```javascript
   // Measure update performance
   console.time('status-update');
   statusPoller.updateEntityStates(largeStatusData);
   console.timeEnd('status-update');
   ```

2. **Implement Batched Updates** ([Performance - Batch Updates](#performance-issues))
   ```javascript
   class OptimizedStatusPoller extends StatusPoller {
     updateEntityStates(statusData) {
       const updates = Object.entries(statusData.entities);
       
       // Process in batches to avoid blocking UI
       const batchSize = 20;
       let currentBatch = 0;
       
       const processBatch = () => {
         const start = currentBatch * batchSize;
         const end = Math.min(start + batchSize, updates.length);
         
         for (let i = start; i < end; i++) {
           const [entityId, stateData] = updates[i];
           this.updateEntityDisplay(entityId, stateData);
         }
         
         currentBatch++;
         
         if (end < updates.length) {
           requestAnimationFrame(processBatch);
         }
       };
       
       processBatch();
     }
   }
   ```

3. **Reduce Polling Frequency** ([Performance - Reduce Polling](#performance-issues))
   ```javascript
   // Adaptive polling based on entity count
   const entityCount = Object.keys(statusData.entities).length;
   const pollInterval = entityCount > 50 ? 10000 : 5000; // 10s vs 5s
   
   const statusPoller = new OptimizedStatusPoller(pollInterval);
   ```

4. **Optimize CSS Transitions** ([CSS Animation Optimization](#css-animation-optimization))
   ```css
   /* Use transform and opacity instead of color changes where possible */
   .entity-svg {
     transition: opacity 0.3s ease, transform 0.3s ease;
     /* Avoid: transition: fill 0.3s ease; // Expensive! */
   }
   
   .entity-svg.performance-optimized {
     transform: translateZ(0); /* Force hardware acceleration */
     will-change: transform, opacity;
   }
   ```

**Expected Result**: Smooth status updates even with 100+ entities, no UI blocking.

## Common Patterns Library

### Standard Entity Status Templates

#### Basic SVG Entity with Status Classes
```django
<!-- Standard pattern for positioned entity icons -->
<g class="entity-group" data-entity-id="{{ entity.id }}">
  <use href="#icon-{{ entity.entity_type.name.lower }}" 
       class="entity-svg {{ entity.get_status_css_classes|join:' ' }}"
       transform="translate({{ entity.position.x }}, {{ entity.position.y }}) 
                  scale({{ entity.position.scale|default:1.0 }}) 
                  rotate({{ entity.position.rotation|default:0 }})"/>
</g>
```

#### Path Entity with Dynamic Styling
```django
<!-- Standard pattern for area/path-based entities -->
<g class="entity-group" data-entity-id="{{ entity.id }}">
  <path class="entity-path {{ entity.get_status_css_classes|join:' ' }}"
        d="{{ entity.path.svg_path }}"
        style="fill: {{ entity.get_status_fill }};
               stroke: {{ entity.get_status_stroke }};
               opacity: {{ entity.get_status_opacity }}"/>
</g>
```

#### Entity Status Card (Non-SVG)
```django
<!-- Standard pattern for entity cards in lists/grids -->
<div class="entity-card" data-entity-id="{{ entity.id }}">
  <div class="status-indicator {{ entity.get_status_css_classes|join:' ' }}"
       style="background-color: {{ entity.get_status_color }}"></div>
  <span class="entity-name">{{ entity.name }}</span>
  <span class="entity-state">{{ entity.get_current_display_state }}</span>
</div>
```

### Standard CSS Status Classes

#### Basic Status Color Scheme
```css
/* Standard status color variables */
:root {
  --status-active: #dc3545;    /* Red - Active/Alert */
  --status-recent: #fd7e14;    /* Orange - Recently active */
  --status-past: #ffc107;      /* Yellow - Past activity */
  --status-idle: #28a745;      /* Green - Idle/Safe */
  --status-unknown: #6c757d;   /* Gray - Unknown/Offline */
}

/* Basic entity status classes */
.entity-svg.state-active {
  fill: var(--status-active);
  stroke: #b02a37;
  opacity: 1.0;
}

.entity-svg.state-recent {
  fill: var(--status-recent);
  stroke: #cc6200;
  opacity: 0.8;
}

.entity-svg.state-past {
  fill: var(--status-past);
  stroke: #cc9a00;
  opacity: 0.6;
}

.entity-svg.state-idle {
  fill: var(--status-idle);
  stroke: #1e7e34;
  opacity: 0.4;
}

.entity-svg.state-unknown {
  fill: var(--status-unknown);
  stroke: #545b62;
  opacity: 0.3;
}
```

#### Smooth Status Transitions
```css
/* Standard transition pattern for status changes */
.entity-svg, .entity-path {
  transition: fill 0.3s ease-in-out, 
              stroke 0.3s ease-in-out, 
              opacity 0.3s ease-in-out;
}

/* Pulse animation for active states */
@keyframes status-pulse {
  0% { opacity: 0.8; }
  50% { opacity: 1.0; }
  100% { opacity: 0.8; }
}

.entity-svg.state-active.pulse-enabled {
  animation: status-pulse 2s ease-in-out infinite;
}
```

#### Device-Type Specific Patterns
```css
/* Motion sensor specific styling */
.entity-svg.motion-sensor.state-active {
  fill: #dc3545;
  filter: drop-shadow(0 0 4px rgba(220, 53, 69, 0.6));
}

/* Door sensor specific styling */
.entity-svg.door-sensor.state-active {
  fill: #dc3545;
  stroke-width: 3;
}

/* Temperature sensor color gradient */
.entity-svg.temperature-sensor.temp-hot {
  fill: #dc3545;  /* Hot - red */
}
.entity-svg.temperature-sensor.temp-warm {
  fill: #fd7e14;  /* Warm - orange */
}
.entity-svg.temperature-sensor.temp-cool {
  fill: #17a2b8;  /* Cool - blue */
}
.entity-svg.temperature-sensor.temp-cold {
  fill: #007bff;  /* Cold - dark blue */
}
```

### Standard JavaScript Polling Implementation

#### Basic StatusPoller Class
```javascript
// Standard polling implementation pattern
class StatusPoller {
  constructor(options = {}) {
    this.pollInterval = options.pollInterval || 5000;
    this.endpoint = options.endpoint || '/api/status';
    this.isPolling = false;
    this.errorCount = 0;
    this.maxErrors = 3;
  }
  
  start() {
    if (this.isPolling) return;
    this.isPolling = true;
    this.errorCount = 0;
    this.poll();
  }
  
  stop() {
    this.isPolling = false;
  }
  
  async poll() {
    if (!this.isPolling) return;
    
    try {
      const response = await fetch(this.endpoint);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      
      const statusData = await response.json();
      this.updateEntityStates(statusData);
      this.errorCount = 0; // Reset error count on success
    } catch (error) {
      console.error('Status polling failed:', error);
      this.errorCount++;
      
      if (this.errorCount >= this.maxErrors) {
        console.error('Too many polling errors, stopping poller');
        this.stop();
        return;
      }
    }
    
    if (this.isPolling) {
      setTimeout(() => this.poll(), this.pollInterval);
    }
  }
  
  updateEntityStates(statusData) {
    if (!statusData.entities) return;
    
    Object.entries(statusData.entities).forEach(([entityId, stateData]) => {
      this.updateEntityDisplay(entityId, stateData);
    });
  }
  
  updateEntityDisplay(entityId, stateData) {
    const elements = document.querySelectorAll(`[data-entity-id="${entityId}"]`);
    elements.forEach(element => {
      this.applyStatusClasses(element, stateData.cssClasses);
      this.applyColorScheme(element, stateData.colorScheme);
    });
  }
  
  applyStatusClasses(element, cssClasses) {
    // Remove existing status classes
    const existingClasses = Array.from(element.classList).filter(c => 
      c.startsWith('state-') || c.startsWith('temp-') || c.startsWith('priority-')
    );
    element.classList.remove(...existingClasses);
    
    // Apply new status classes
    if (cssClasses && cssClasses.length) {
      element.classList.add(...cssClasses);
    }
  }
  
  applyColorScheme(element, colorScheme) {
    if (!colorScheme) return;
    
    if (element.tagName.toLowerCase() === 'path' || element.tagName.toLowerCase() === 'use') {
      element.style.fill = colorScheme.fill || '';
      element.style.stroke = colorScheme.stroke || '';
      element.style.opacity = colorScheme.opacity || '';
    } else if (element.classList.contains('status-indicator')) {
      element.style.backgroundColor = colorScheme.fill || '';
      element.style.borderColor = colorScheme.stroke || '';
      element.style.opacity = colorScheme.opacity || '';
    }
  }
}
```

#### Standard Initialization Pattern
```javascript
// Standard way to initialize status polling
document.addEventListener('DOMContentLoaded', function() {
  // Initialize status poller if entity elements exist
  if (document.querySelectorAll('[data-entity-id]').length > 0) {
    window.statusPoller = new StatusPoller({
      pollInterval: 5000,
      endpoint: '/api/status'
    });
    window.statusPoller.start();
  }
  
  // Cleanup on page unload
  window.addEventListener('beforeunload', function() {
    if (window.statusPoller) {
      window.statusPoller.stop();
    }
  });
});
```

### Standard Backend Response Patterns

#### Standard Server Response Format
```python
# Standard format for /api/status endpoint responses
{
    "timestamp": "2025-01-15T10:30:00Z",
    "entities": {
        "entity_123": {
            "cssClasses": ["state-active", "priority-high"],
            "colorScheme": {
                "fill": "#dc3545",
                "stroke": "#b02a37", 
                "opacity": "0.8"
            },
            "displayState": "Motion Detected",
            "lastUpdated": "2025-01-15T10:29:45Z"
        },
        "entity_456": {
            "cssClasses": ["state-idle"],
            "colorScheme": {
                "fill": "#28a745",
                "stroke": "#1e7e34",
                "opacity": "0.4"
            },
            "displayState": "No Motion",
            "lastUpdated": "2025-01-15T10:25:12Z"
        }
    }
}
```

#### Standard Django Model Methods
```python
# Standard methods for Entity models to support status display
class Entity(models.Model):
    def get_status_css_classes(self):
        """Return CSS classes for current status"""
        status_manager = StatusDisplayManager(self)
        return status_manager.get_css_classes()
    
    def get_status_color(self):
        """Return fill color for current status"""
        status_manager = StatusDisplayManager(self)
        return status_manager.get_fill_color()
    
    def get_status_display_data(self):
        """Return complete status data for API responses"""
        status_manager = StatusDisplayManager(self)
        return {
            'cssClasses': status_manager.get_css_classes(),
            'colorScheme': {
                'fill': status_manager.get_fill_color(),
                'stroke': status_manager.get_stroke_color(),
                'opacity': status_manager.get_opacity()
            },
            'displayState': status_manager.get_display_state(),
            'lastUpdated': self.get_last_updated_timestamp()
        }
```

### Common Entity Status Testing Patterns

#### Standard Test Fixtures
```python
# Standard test setup for entity status testing
class EntityStatusTestCase(TestCase):
    def setUp(self):
        self.location = Location.objects.create(name='Test Location')
        
        # Create test entities with different types
        self.motion_sensor = Entity.objects.create(
            name='Test Motion Sensor',
            entity_type=EntityType.MOTION_SENSOR,
            location=self.location
        )
        
        self.door_sensor = Entity.objects.create(
            name='Test Door Sensor', 
            entity_type=EntityType.DOOR_SENSOR,
            location=self.location
        )
        
        # Create EntityPosition for icon entities
        EntityPosition.objects.create(
            entity=self.motion_sensor,
            x=100, y=150, scale=1.0, rotation=0
        )
    
    def create_test_state(self, entity, state_type, value, timestamp=None):
        """Helper to create test entity states"""
        timestamp = timestamp or timezone.now()
        return EntityState.objects.create(
            entity=entity,
            state_type=state_type,
            value=value,
            timestamp=timestamp
        )
    
    def assert_status_response(self, response, entity_id, expected_classes):
        """Helper to assert status API response format"""
        self.assertSuccessResponse(response)
        self.assertJsonResponse(response)
        
        data = response.json()
        self.assertIn('entities', data)
        self.assertIn(entity_id, data['entities'])
        
        entity_data = data['entities'][entity_id]
        self.assertIn('cssClasses', entity_data)
        self.assertIn('colorScheme', entity_data)
        
        for css_class in expected_classes:
            self.assertIn(css_class, entity_data['cssClasses'])
```

#### Standard JavaScript Testing Pattern
```javascript
// Standard pattern for testing status updates in browser
function testEntityStatusUpdates() {
    // Mock status data
    const mockStatusData = {
        timestamp: new Date().toISOString(),
        entities: {
            'entity_123': {
                cssClasses: ['state-active', 'priority-high'],
                colorScheme: {
                    fill: '#dc3545',
                    stroke: '#b02a37',
                    opacity: '0.8'
                }
            }
        }
    };
    
    // Test status application
    const statusPoller = new StatusPoller();
    statusPoller.updateEntityStates(mockStatusData);
    
    // Verify DOM updates
    const element = document.querySelector('[data-entity-id="entity_123"]');
    console.assert(element.classList.contains('state-active'), 'Active class not applied');
    console.assert(element.style.fill === 'rgb(220, 53, 69)', 'Fill color not applied');
    
    console.log('Entity status update test passed');
}
```

## Performance Optimization Guide

### Overview

Entity status display can become a performance bottleneck when dealing with many entities, frequent updates, or complex visual effects. This guide provides strategies to maintain smooth, responsive status displays even under heavy load.

### Performance Monitoring and Profiling

#### Measuring Status Update Performance
```javascript
// Monitor status update timing
class StatusPerformanceMonitor {
    constructor() {
        this.updateTimes = [];
        this.maxSamples = 100;
    }
    
    measureUpdate(updateFunction) {
        const start = performance.now();
        updateFunction();
        const end = performance.now();
        
        this.updateTimes.push(end - start);
        if (this.updateTimes.length > this.maxSamples) {
            this.updateTimes.shift();
        }
        
        // Log warnings for slow updates
        const updateTime = end - start;
        if (updateTime > 16) { // More than one frame at 60fps
            console.warn(`Slow status update: ${updateTime.toFixed(2)}ms`);
        }
    }
    
    getAverageUpdateTime() {
        if (this.updateTimes.length === 0) return 0;
        return this.updateTimes.reduce((a, b) => a + b, 0) / this.updateTimes.length;
    }
    
    reportPerformance() {
        console.log(`Status Update Performance:
            Average: ${this.getAverageUpdateTime().toFixed(2)}ms
            Max: ${Math.max(...this.updateTimes).toFixed(2)}ms
            Min: ${Math.min(...this.updateTimes).toFixed(2)}ms
            Samples: ${this.updateTimes.length}`);
    }
}
```

#### Browser DevTools Profiling
```javascript
// Enable performance tracking in development
if (process.env.NODE_ENV === 'development') {
    // Mark status update cycles for performance timeline
    function markStatusUpdate() {
        performance.mark('status-update-start');
    }
    
    function measureStatusUpdate() {
        performance.mark('status-update-end');
        performance.measure('status-update', 'status-update-start', 'status-update-end');
    }
    
    // Use in StatusPoller
    markStatusUpdate();
    this.updateEntityStates(statusData);
    measureStatusUpdate();
}
```

### DOM Update Optimization

#### Batched DOM Modifications
```javascript
// Optimized StatusPoller with batched DOM updates
class OptimizedStatusPoller extends StatusPoller {
    updateEntityStates(statusData) {
        const updates = Object.entries(statusData.entities);
        const batchSize = 20; // Process 20 entities at a time
        
        // Use requestAnimationFrame to avoid blocking UI
        this.processBatch(updates, 0, batchSize);
    }
    
    processBatch(updates, startIndex, batchSize) {
        const endIndex = Math.min(startIndex + batchSize, updates.length);
        
        // Process current batch
        for (let i = startIndex; i < endIndex; i++) {
            const [entityId, stateData] = updates[i];
            this.updateEntityDisplay(entityId, stateData);
        }
        
        // Schedule next batch if more entities remain
        if (endIndex < updates.length) {
            requestAnimationFrame(() => {
                this.processBatch(updates, endIndex, batchSize);
            });
        }
    }
    
    // Minimize DOM reads and writes
    updateEntityDisplay(entityId, stateData) {
        const elements = this.cachedElements[entityId] || 
                        this.cacheEntityElements(entityId);
        
        elements.forEach(element => {
            // Batch style updates
            this.batchStyleUpdate(element, stateData);
        });
    }
    
    cacheEntityElements(entityId) {
        const elements = document.querySelectorAll(`[data-entity-id="${entityId}"]`);
        this.cachedElements = this.cachedElements || {};
        this.cachedElements[entityId] = Array.from(elements);
        return this.cachedElements[entityId];
    }
    
    batchStyleUpdate(element, stateData) {
        // Collect all style changes before applying
        const styleUpdates = {};
        
        if (stateData.colorScheme) {
            styleUpdates.fill = stateData.colorScheme.fill;
            styleUpdates.stroke = stateData.colorScheme.stroke;
            styleUpdates.opacity = stateData.colorScheme.opacity;
        }
        
        // Apply all changes at once
        Object.assign(element.style, styleUpdates);
        
        // Update classes in single operation
        if (stateData.cssClasses) {
            this.applyStatusClasses(element, stateData.cssClasses);
        }
    }
}
```

#### Virtual Entity Rendering
```javascript
// Only render entities in visible viewport
class VirtualizedStatusDisplay {
    constructor(svgElement, options = {}) {
        this.svgElement = svgElement;
        this.visibleEntities = new Set();
        this.hiddenEntities = new Set();
        this.viewBox = this.parseViewBox(svgElement.getAttribute('viewBox'));
        this.options = {
            cullingMargin: options.cullingMargin || 50, // Render margin outside viewport
            ...options
        };
        
        // Monitor viewport changes
        this.svgElement.addEventListener('viewportChanged', (e) => {
            this.updateViewBox(e.detail.viewBox);
        });
    }
    
    updateViewBox(newViewBox) {
        this.viewBox = newViewBox;
        this.updateEntityVisibility();
    }
    
    updateEntityVisibility() {
        const entities = this.svgElement.querySelectorAll('[data-entity-id]');
        
        entities.forEach(entity => {
            const isVisible = this.isEntityVisible(entity);
            const entityId = entity.getAttribute('data-entity-id');
            
            if (isVisible && this.hiddenEntities.has(entityId)) {
                // Entity became visible
                this.showEntity(entity, entityId);
            } else if (!isVisible && this.visibleEntities.has(entityId)) {
                // Entity became hidden
                this.hideEntity(entity, entityId);
            }
        });
    }
    
    isEntityVisible(entity) {
        const bbox = entity.getBBox();
        const margin = this.options.cullingMargin;
        
        return !(
            bbox.x + bbox.width < this.viewBox.x - margin ||
            bbox.x > this.viewBox.x + this.viewBox.width + margin ||
            bbox.y + bbox.height < this.viewBox.y - margin ||
            bbox.y > this.viewBox.y + this.viewBox.height + margin
        );
    }
    
    showEntity(entity, entityId) {
        entity.style.display = 'block';
        this.visibleEntities.add(entityId);
        this.hiddenEntities.delete(entityId);
    }
    
    hideEntity(entity, entityId) {
        entity.style.display = 'none';
        this.hiddenEntities.add(entityId);
        this.visibleEntities.delete(entityId);
    }
}
```

### Memory Management

#### Element Reference Caching
```javascript
// Efficient element caching with memory management
class EntityElementCache {
    constructor(maxCacheSize = 1000) {
        this.cache = new Map();
        this.accessOrder = [];
        this.maxCacheSize = maxCacheSize;
    }
    
    get(entityId) {
        if (this.cache.has(entityId)) {
            // Move to end of access order (LRU)
            this.accessOrder = this.accessOrder.filter(id => id !== entityId);
            this.accessOrder.push(entityId);
            return this.cache.get(entityId);
        }
        return null;
    }
    
    set(entityId, elements) {
        // Evict oldest entries if cache is full
        if (this.cache.size >= this.maxCacheSize) {
            const oldest = this.accessOrder.shift();
            this.cache.delete(oldest);
        }
        
        this.cache.set(entityId, elements);
        this.accessOrder.push(entityId);
    }
    
    clear() {
        this.cache.clear();
        this.accessOrder = [];
    }
    
    // Clean up references to removed entities
    cleanup() {
        const validEntityIds = new Set();
        document.querySelectorAll('[data-entity-id]').forEach(el => {
            validEntityIds.add(el.getAttribute('data-entity-id'));
        });
        
        // Remove cached elements for entities that no longer exist
        for (const [entityId] of this.cache) {
            if (!validEntityIds.has(entityId)) {
                this.cache.delete(entityId);
                this.accessOrder = this.accessOrder.filter(id => id !== entityId);
            }
        }
    }
}
```

#### Memory Leak Prevention
```javascript
// Prevent memory leaks in long-running applications
class LeakPreventionStatusPoller extends StatusPoller {
    constructor(options = {}) {
        super(options);
        this.cleanupInterval = options.cleanupInterval || 60000; // 1 minute
        this.startCleanupTimer();
    }
    
    startCleanupTimer() {
        setInterval(() => {
            this.performCleanup();
        }, this.cleanupInterval);
    }
    
    performCleanup() {
        // Clean up element cache
        if (this.elementCache) {
            this.elementCache.cleanup();
        }
        
        // Remove orphaned event listeners
        this.removeOrphanedListeners();
        
        // Force garbage collection in development
        if (typeof gc !== 'undefined') {
            gc();
        }
    }
    
    removeOrphanedListeners() {
        // Track and remove event listeners for removed entities
        const currentEntityIds = new Set();
        document.querySelectorAll('[data-entity-id]').forEach(el => {
            currentEntityIds.add(el.getAttribute('data-entity-id'));
        });
        
        // Clean up listeners for removed entities
        if (this.entityListeners) {
            Object.keys(this.entityListeners).forEach(entityId => {
                if (!currentEntityIds.has(entityId)) {
                    delete this.entityListeners[entityId];
                }
            });
        }
    }
    
    stop() {
        super.stop();
        
        // Clean up all references
        if (this.elementCache) {
            this.elementCache.clear();
        }
        
        this.entityListeners = {};
    }
}
```

### CSS Performance Optimization

#### Hardware Acceleration
```css
/* Force GPU acceleration for status animations */
.entity-svg, .entity-path {
    transform: translateZ(0); /* Force hardware acceleration */
    will-change: fill, stroke, opacity; /* Hint browser about changing properties */
}

/* Use transform and opacity for animations (GPU-friendly) */
.entity-svg.status-transition {
    transition: transform 0.3s ease, opacity 0.3s ease;
}

/* Avoid expensive properties in animations */
.entity-svg.avoid-expensive {
    /* AVOID: animating these properties */
    /* transition: width 0.3s ease, height 0.3s ease, background-size 0.3s ease; */
    
    /* PREFER: animating these properties */
    transition: transform 0.3s ease, opacity 0.3s ease;
}
```

#### CSS Containment
```css
/* Use CSS containment to limit reflow/repaint scope */
.entity-group {
    contain: layout style paint;
}

.location-view-container {
    contain: layout;
}

/* Optimize for large entity lists */
.entity-collection {
    contain: layout style paint;
    will-change: transform;
}
```

#### Efficient CSS Selectors
```css
/* FAST: Use class selectors */
.entity-svg.state-active { fill: #dc3545; }

/* SLOWER: Avoid complex descendant selectors */
.location-view .entity-group .entity-svg.state-active { fill: #dc3545; }

/* FAST: Specific attribute selectors */
[data-entity-type="motion_sensor"].state-active { fill: #dc3545; }

/* SLOWER: Universal selectors */
* .state-active { fill: #dc3545; }
```

### Network Optimization

#### Intelligent Polling Strategies
```javascript
// Adaptive polling based on system load and entity count
class AdaptiveStatusPoller extends StatusPoller {
    constructor(options = {}) {
        super(options);
        this.baseInterval = options.pollInterval || 5000;
        this.minInterval = options.minInterval || 1000;
        this.maxInterval = options.maxInterval || 30000;
        this.entityCount = 0;
        this.systemLoad = 0;
    }
    
    calculateOptimalInterval() {
        // Adjust based on entity count
        let interval = this.baseInterval;
        
        if (this.entityCount > 100) {
            interval *= 1.5; // Slower polling for many entities
        } else if (this.entityCount > 50) {
            interval *= 1.2;
        }
        
        // Adjust based on system performance
        if (this.systemLoad > 0.8) {
            interval *= 2; // Much slower when system is loaded
        } else if (this.systemLoad > 0.6) {
            interval *= 1.5;
        }
        
        return Math.max(this.minInterval, Math.min(this.maxInterval, interval));
    }
    
    measureSystemLoad() {
        // Simple performance measurement
        const start = performance.now();
        
        // Simulate work
        for (let i = 0; i < 1000; i++) {
            Math.random();
        }
        
        const end = performance.now();
        const expected = 1; // Expected time for the work in ms
        this.systemLoad = Math.min(1, (end - start) / expected);
    }
    
    async poll() {
        this.measureSystemLoad();
        
        try {
            const response = await fetch('/api/status');
            const statusData = await response.json();
            
            this.entityCount = Object.keys(statusData.entities || {}).length;
            this.updateEntityStates(statusData);
            
            this.errorCount = 0;
        } catch (error) {
            console.error('Status polling failed:', error);
            this.errorCount++;
        }
        
        // Use adaptive interval
        const interval = this.calculateOptimalInterval();
        
        if (this.isPolling) {
            setTimeout(() => this.poll(), interval);
        }
    }
}
```

#### Delta Updates
```javascript
// Only send changes since last update
class DeltaStatusPoller extends StatusPoller {
    constructor(options = {}) {
        super(options);
        this.lastUpdateTimestamp = null;
        this.entityStates = new Map();
    }
    
    async poll() {
        try {
            const url = this.lastUpdateTimestamp 
                ? `/api/status?since=${this.lastUpdateTimestamp}`
                : '/api/status';
                
            const response = await fetch(url);
            const statusData = await response.json();
            
            if (statusData.entities) {
                this.processDeltas(statusData);
                this.lastUpdateTimestamp = statusData.timestamp;
            }
        } catch (error) {
            console.error('Delta polling failed:', error);
        }
    }
    
    processDeltas(statusData) {
        Object.entries(statusData.entities).forEach(([entityId, newState]) => {
            const currentState = this.entityStates.get(entityId);
            
            // Only update if state actually changed
            if (!currentState || this.hasStateChanged(currentState, newState)) {
                this.updateEntityDisplay(entityId, newState);
                this.entityStates.set(entityId, newState);
            }
        });
    }
    
    hasStateChanged(oldState, newState) {
        return JSON.stringify(oldState.cssClasses) !== JSON.stringify(newState.cssClasses) ||
               JSON.stringify(oldState.colorScheme) !== JSON.stringify(newState.colorScheme);
    }
}
```

### Large Dataset Handling

#### Pagination and Lazy Loading
```javascript
// Handle thousands of entities with pagination
class PaginatedStatusDisplay {
    constructor(svgElement, options = {}) {
        this.svgElement = svgElement;
        this.pageSize = options.pageSize || 50;
        this.visiblePages = new Set();
        this.entityPages = new Map();
        this.currentViewport = null;
    }
    
    paginateEntities() {
        const entities = this.svgElement.querySelectorAll('[data-entity-id]');
        const pages = [];
        
        // Group entities by spatial locality
        const spatialGroups = this.groupEntitiesSpatially(entities);
        
        spatialGroups.forEach((group, index) => {
            const pageId = `page-${index}`;
            pages.push({
                id: pageId,
                entities: group,
                bounds: this.calculateGroupBounds(group)
            });
        });
        
        return pages;
    }
    
    groupEntitiesSpatially(entities) {
        // Use spatial hashing to group nearby entities
        const spatialHash = new Map();
        const cellSize = 100; // SVG units
        
        Array.from(entities).forEach(entity => {
            const bbox = entity.getBBox();
            const cellX = Math.floor(bbox.x / cellSize);
            const cellY = Math.floor(bbox.y / cellSize);
            const cellKey = `${cellX},${cellY}`;
            
            if (!spatialHash.has(cellKey)) {
                spatialHash.set(cellKey, []);
            }
            spatialHash.get(cellKey).push(entity);
        });
        
        return Array.from(spatialHash.values());
    }
    
    updateVisiblePages(viewBox) {
        this.currentViewport = viewBox;
        const pages = this.paginateEntities();
        
        pages.forEach(page => {
            const isVisible = this.isPageVisible(page.bounds, viewBox);
            
            if (isVisible && !this.visiblePages.has(page.id)) {
                this.loadPage(page);
            } else if (!isVisible && this.visiblePages.has(page.id)) {
                this.unloadPage(page);
            }
        });
    }
    
    isPageVisible(bounds, viewBox) {
        return !(
            bounds.right < viewBox.x ||
            bounds.left > viewBox.x + viewBox.width ||
            bounds.bottom < viewBox.y ||
            bounds.top > viewBox.y + viewBox.height
        );
    }
    
    loadPage(page) {
        // Enable status updates for entities in this page
        page.entities.forEach(entity => {
            entity.style.display = 'block';
            this.enableStatusUpdates(entity);
        });
        
        this.visiblePages.add(page.id);
    }
    
    unloadPage(page) {
        // Disable status updates for entities in this page
        page.entities.forEach(entity => {
            entity.style.display = 'none';
            this.disableStatusUpdates(entity);
        });
        
        this.visiblePages.delete(page.id);
    }
}
```

### Browser Compatibility Optimization

#### Performance Feature Detection
```javascript
// Adapt performance strategies based on browser capabilities
class BrowserOptimizedStatusPoller extends StatusPoller {
    constructor(options = {}) {
        super(options);
        this.browserCapabilities = this.detectCapabilities();
        this.adaptToBrowser();
    }
    
    detectCapabilities() {
        return {
            hasRequestAnimationFrame: typeof requestAnimationFrame !== 'undefined',
            hasIntersectionObserver: typeof IntersectionObserver !== 'undefined',
            hasWebGL: this.hasWebGLSupport(),
            supportsCSSSContainment: CSS.supports('contain', 'layout'),
            supportsWillChange: CSS.supports('will-change', 'transform'),
            isLowEndDevice: this.detectLowEndDevice()
        };
    }
    
    hasWebGLSupport() {
        try {
            const canvas = document.createElement('canvas');
            return !!(canvas.getContext('webgl') || canvas.getContext('experimental-webgl'));
        } catch (e) {
            return false;
        }
    }
    
    detectLowEndDevice() {
        // Heuristics for low-end device detection
        const memoryGB = navigator.deviceMemory || 4;
        const cores = navigator.hardwareConcurrency || 4;
        return memoryGB < 2 || cores < 4;
    }
    
    adaptToBrowser() {
        if (this.browserCapabilities.isLowEndDevice) {
            // Reduce update frequency and batch size
            this.pollInterval *= 2;
            this.batchSize = 10;
        }
        
        if (!this.browserCapabilities.hasRequestAnimationFrame) {
            // Fallback to setTimeout for older browsers
            this.useSetTimeoutForUpdates = true;
        }
        
        if (!this.browserCapabilities.supportsCSSSContainment) {
            // Disable some optimizations that require CSS containment
            this.disableContainmentOptimizations = true;
        }
    }
}
```

### Performance Monitoring Integration

#### Real-User Monitoring (RUM)
```javascript
// Integration with performance monitoring services
class MonitoredStatusPoller extends StatusPoller {
    constructor(options = {}) {
        super(options);
        this.performanceMetrics = {
            updateTimes: [],
            errorCounts: {},
            memoryUsage: []
        };
    }
    
    updateEntityDisplay(entityId, stateData) {
        const start = performance.now();
        
        try {
            super.updateEntityDisplay(entityId, stateData);
            
            const duration = performance.now() - start;
            this.recordMetric('updateTime', duration);
            
        } catch (error) {
            this.recordError('updateDisplay', error);
            throw error;
        }
    }
    
    recordMetric(type, value) {
        if (!this.performanceMetrics[type]) {
            this.performanceMetrics[type] = [];
        }
        
        this.performanceMetrics[type].push({
            value,
            timestamp: Date.now()
        });
        
        // Keep only recent metrics (last 5 minutes)
        const cutoff = Date.now() - 5 * 60 * 1000;
        this.performanceMetrics[type] = this.performanceMetrics[type]
            .filter(metric => metric.timestamp > cutoff);
    }
    
    recordError(operation, error) {
        if (!this.performanceMetrics.errorCounts[operation]) {
            this.performanceMetrics.errorCounts[operation] = 0;
        }
        this.performanceMetrics.errorCounts[operation]++;
        
        // Send to monitoring service
        if (typeof gtag !== 'undefined') {
            gtag('event', 'status_display_error', {
                operation,
                error_message: error.message
            });
        }
    }
    
    getPerformanceReport() {
        const report = {
            averageUpdateTime: this.calculateAverage('updateTime'),
            maxUpdateTime: this.calculateMax('updateTime'),
            errorRate: this.calculateErrorRate(),
            memoryTrend: this.calculateMemoryTrend()
        };
        
        return report;
    }
}
```

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

```javascript
// Status polling implementation
class StatusPoller {
    constructor(pollInterval = 5000) {
        this.pollInterval = pollInterval;
        this.isPolling = false;
    }
    
    start() {
        if (this.isPolling) return;
        this.isPolling = true;
        this.poll();
    }
    
    async poll() {
        try {
            const response = await fetch('/api/status');
            const statusData = await response.json();
            this.updateEntityStates(statusData);
        } catch (error) {
            console.error('Status polling failed:', error);
        }
        
        if (this.isPolling) {
            setTimeout(() => this.poll(), this.pollInterval);
        }
    }
    
    updateEntityStates(statusData) {
        // Update entity visual states based on server response
        Object.entries(statusData.entities).forEach(([entityId, stateData]) => {
            this.updateEntityDisplay(entityId, stateData);
        });
    }
    
    updateEntityDisplay(entityId, stateData) {
        const elements = document.querySelectorAll(`[data-entity-id="${entityId}"]`);
        elements.forEach(element => {
            this.applyStatusClasses(element, stateData.cssClasses);
            this.applyColorScheme(element, stateData.colorScheme);
        });
    }
}
```

### Server Response Format

The server returns status updates in a standardized JSON format:

```javascript
{
  "timestamp": "2025-01-15T10:30:00Z",
  "entities": {
    "entity_123": {
      "cssClasses": ["state-active", "priority-high"],
      "colorScheme": {
        "fill": "#dc3545",
        "stroke": "#b02a37",
        "opacity": 0.8
      },
      "iconVariant": "motion-active"
    }
  }
}
```

### Element Targeting and Updates

The polling system uses CSS class names and data attributes to target elements:

```javascript
function applyStatusClasses(element, cssClasses) {
    // Remove existing state classes
    element.classList.remove(...element.classList);
    
    // Apply new state classes
    element.classList.add(...cssClasses);
}

function applyColorScheme(element, colorScheme) {
    if (element.tagName === 'path' || element.tagName === 'g') {
        // SVG element styling
        element.style.fill = colorScheme.fill;
        element.style.stroke = colorScheme.stroke;
        element.style.opacity = colorScheme.opacity;
    } else if (element.tagName === 'div') {
        // HTML element styling for non-SVG displays
        element.style.backgroundColor = colorScheme.fill;
        element.style.borderColor = colorScheme.stroke;
        element.style.opacity = colorScheme.opacity;
    }
}
```

## SVG Element Handling

### SVG Path and Group Elements

Standard handling for SVG `g` and `path` tags:

```html
<g class="entity-group" data-entity-id="123">
  <path class="entity-svg state-idle" d="M10,10 L50,10 L50,50 L10,50 Z"/>
</g>
```

```javascript
// SVG-specific styling
function styleSvgElement(element, stateData) {
    element.setAttribute('class', `entity-svg ${stateData.cssClasses.join(' ')}`);
    element.style.fill = stateData.colorScheme.fill;
    element.style.stroke = stateData.colorScheme.stroke;
}
```

### Special Case Handling

#### Select Tags (Controllers)

Special handling for controller select elements:

```javascript
function updateControllerSelect(selectElement, stateData) {
    // Update select styling to reflect entity state
    selectElement.className = `form-control ${stateData.cssClasses.join(' ')}`;
    
    // Update associated label or indicator
    const indicator = selectElement.nextElementSibling;
    if (indicator && indicator.classList.contains('status-indicator')) {
        indicator.style.backgroundColor = stateData.colorScheme.fill;
    }
}
```

#### DIV Elements (Non-SVG Display)

For entity status in Collection Views or status modals:

```html
<div class="entity-status-card" data-entity-id="123">
  <div class="status-indicator"></div>
  <span class="entity-name">Motion Sensor</span>
</div>
```

```javascript
function updateStatusCard(cardElement, stateData) {
    const indicator = cardElement.querySelector('.status-indicator');
    indicator.className = `status-indicator ${stateData.cssClasses.join(' ')}`;
    indicator.style.backgroundColor = stateData.colorScheme.fill;
}
```

## Template Integration

### Django Template Setup

Templates must include proper class names and data attributes:

```django
<!-- SVG entity representation -->
<g class="entity-group" data-entity-id="{{ entity.id }}">
  <path class="entity-svg {{ entity.get_status_css_classes }}" 
        d="{{ entity.get_svg_path }}"
        style="fill: {{ entity.get_status_color }}"/>
</g>

<!-- Non-SVG entity representation -->
<div class="entity-card" data-entity-id="{{ entity.id }}">
  <div class="status-indicator {{ entity.get_status_css_classes }}"
       style="background-color: {{ entity.get_status_color }}"></div>
  <span class="entity-name">{{ entity.name }}</span>
</div>
```

### Template Context Requirements

Views must provide status data in the context:

```python
# In Django view
context = {
    'entity': entity,
    'status_classes': entity.get_status_css_classes(),
    'status_color': entity.get_status_color(),
    'status_data': entity.get_status_display_data(),
}
```

## Performance Considerations

### Efficient DOM Updates

Minimize DOM manipulation for better performance:

```javascript
// Batch DOM updates
function batchUpdateEntities(statusUpdates) {
    // Use DocumentFragment for batch updates
    const fragment = document.createDocumentFragment();
    
    statusUpdates.forEach(update => {
        const element = document.querySelector(`[data-entity-id="${update.entityId}"]`);
        if (element) {
            // Apply updates without triggering reflow
            requestAnimationFrame(() => {
                this.applyStatusUpdate(element, update.stateData);
            });
        }
    });
}
```

### CSS Animation Optimization

Use transform and opacity for smooth animations:

```css
.entity-svg {
  transition: opacity 0.3s ease, transform 0.3s ease;
  /* Avoid animating expensive properties like width, height, color */
}

.entity-svg.state-transition {
  transform: scale(1.1);
  opacity: 0.9;
}
```

## Troubleshooting

### Status Colors Not Updating

**Symptoms**: Entity colors remain static, don't reflect current state
**Root Causes & Solutions**:

1. **CSS Classes Not Applied**
   ```bash
   # Check browser dev tools - Elements tab
   # Look for data-entity-id attribute and CSS classes
   ```
   - **Fix**: Ensure `StatusPoller.applyStatusClasses()` is called
   - **Verify**: Check `element.classList` contains expected state classes

2. **CSS Variables Not Defined**
   ```css
   /* Verify these exist in your CSS */
   :root {
     --status-active: #dc3545;
     --status-recent: #fd7e14;
     /* ... other status colors */
   }
   ```
   - **Fix**: Add missing CSS custom properties
   - **Test**: Use browser dev tools to verify computed styles

3. **CSS Selectors Too Specific**
   ```css
   /* BAD - too specific, won't be overridden */
   .location-view .entity-svg.state-active { fill: red !important; }
   
   /* GOOD - proper specificity */
   .entity-svg.state-active { fill: var(--status-active); }
   ```

### Polling System Not Working

**Symptoms**: Status never updates, even when backend state changes
**Diagnostic Steps**:

1. **Check Network Tab**
   ```bash
   # Browser Dev Tools → Network Tab
   # Look for periodic /api/status requests
   # Should see requests every 5 seconds (default)
   ```

2. **Verify StatusPoller Initialization**
   ```javascript
   // Check browser console for errors
   console.log('StatusPoller initialized:', window.statusPoller);
   
   // Manually test polling
   if (window.statusPoller) {
       window.statusPoller.poll();
   }
   ```

3. **Check Server Response**
   ```bash
   # Manually test the endpoint
   curl http://localhost:8411/api/status
   
   # Should return JSON with entities object
   ```

**Common Fixes**:
- **StatusPoller not started**: Call `statusPoller.start()` in DOMContentLoaded
- **URL incorrect**: Verify `/api/status` endpoint exists and returns valid JSON
- **JavaScript errors**: Check browser console for exceptions stopping polling

### SVG Elements Not Styling

**Symptoms**: SVG paths/groups don't change appearance with status updates
**Diagnostic Approach**:

1. **Verify Element Selection**
   ```javascript
   // Test in browser console
   const elements = document.querySelectorAll('[data-entity-id="123"]');
   console.log('Found elements:', elements.length);
   ```

2. **Check SVG Structure**
   ```html
   <!-- Required structure -->
   <g class="entity-group" data-entity-id="123">
     <path class="entity-svg state-idle" d="..."/>
   </g>
   ```

3. **Test CSS Application**
   ```javascript
   // Manually apply CSS class
   element.classList.add('state-active');
   // Should see visual change immediately
   ```

**Solutions**:
- **Missing data-entity-id**: Add to parent group or path element
- **Wrong element type**: Use proper selectors for `g` vs `path` elements  
- **CSS inheritance issues**: Check if parent elements are blocking style inheritance

### Template Integration Issues

**Symptoms**: New entity templates don't show status updates
**Checklist**:

1. **Required Attributes**
   ```django
   <!-- MUST have data-entity-id -->
   <g data-entity-id="{{ entity.id }}">
     <!-- MUST have status CSS classes -->
     <path class="entity-svg {{ entity.get_status_css_classes }}">
   </g>
   ```

2. **Context Data**
   ```python
   # View must provide status data
   context = {
       'entity': entity,
       'status_classes': entity.get_status_css_classes(),
       'status_color': entity.get_status_color(),
   }
   ```

3. **Template Includes**
   ```django
   <!-- Ensure polling.js is loaded -->
   {% load static %}
   <script src="{% static 'js/polling.js' %}"></script>
   ```

### Performance Issues

**Symptoms**: Slow status updates, browser lag with many entities
**Solutions**:

1. **Throttle DOM Updates**
   ```javascript
   // Use requestAnimationFrame for smooth updates
   requestAnimationFrame(() => {
       this.applyStatusUpdate(element, statusData);
   });
   ```

2. **Batch Updates**
   ```javascript
   // Process all status updates in single pass
   Object.entries(statusData.entities).forEach(([entityId, data]) => {
       this.scheduleUpdate(entityId, data);
   });
   ```

3. **Reduce Polling Frequency**
   ```javascript
   // Increase interval for non-critical entities
   const statusPoller = new StatusPoller(10000); // 10 seconds
   ```

### Browser Compatibility Issues

**Symptoms**: Status display works in some browsers but not others
**Common Issues**:

1. **CSS Custom Properties (IE/Edge)**
   ```css
   /* Fallback for older browsers */
   .entity-svg.state-active {
     fill: #dc3545; /* fallback */
     fill: var(--status-active, #dc3545);
   }
   ```

2. **SVG Styling (Safari)**
   ```css
   /* Safari sometimes needs explicit SVG styling */
   .entity-svg {
     -webkit-transform: translateZ(0); /* Force hardware acceleration */
   }
   ```

3. **Fetch API (IE)**
   ```javascript
   // Use polyfill or XMLHttpRequest for IE support
   if (!window.fetch) {
       // Load fetch polyfill or use XMLHttpRequest
   }
   ```

## Related Documentation
- Status calculation logic: [Domain Guidelines](../domain/domain-guidelines.md#status-display-system)
- Style guidelines: [Style Guidelines](style-guidelines.md)
- Template conventions: [Template Conventions](template-conventions.md)
- Frontend patterns: [Frontend Guidelines](frontend-guidelines.md)