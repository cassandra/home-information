# SVG Coordinate Operations

## Quick Reference

### Common Tasks
- **Convert SVG to screen coords** → [Use coordinate transform](#screen-position-calculation) → `calculate_entity_position()`
- **Handle mouse clicks** → [Screen to SVG conversion](#interactive-coordinate-conversion) → `screenToSvgCoordinates()`
- **Implement zoom controls** → [Viewport controller](#zoom-and-pan-operations) → `SvgViewportController`
- **Position entities dynamically** → [Entity positioning](#entity-positioning-and-scaling) → `updateEntityPosition()`
- **Debug coordinate issues** → [Check coordinate systems](#coordinate-system-types) → Verify SVG vs screen vs viewport

### Key JavaScript Classes
- **`SvgCoordinateTransform`**: Converts between coordinate systems
- **`SvgInteractionHandler`**: Handles mouse events and SVG interactions  
- **`SvgViewportController`**: Manages zoom, pan, and viewport transforms
- **`EntityPositionManager`**: Updates entity positions based on viewport

### Quick Fixes
| Problem | Solution | Location |
|---------|----------|----------|
| Click detection wrong | Check coordinate conversion | [Interactive Coordinate](#interactive-coordinate-conversion) |
| Entity positions wrong | Verify viewBox parsing | [Screen Position](#screen-position-calculation) |
| Zoom not working | Initialize viewport controller | [Zoom Operations](#zoom-and-pan-operations) |
| Performance issues | Use requestAnimationFrame | [Performance](#efficient-coordinate-calculations) |

### Coordinate System Quick Guide
```
Mouse Click (screen pixels)
    ↓ getBoundingClientRect()
SVG Viewport Coordinates  
    ↓ getScreenCTM().inverse()
SVG Document Coordinates
    ↓ viewBox transformation
Entity Local Coordinates
```

### Common Coordinate Conversions
- **Screen → SVG**: `element.createSVGPoint()` + `getScreenCTM().inverse()`
- **SVG → Screen**: `(svg_coord - viewbox_origin) * scale_factor`
- **Viewport → Entity**: Apply entity transform matrix


## Real-World Workflow Examples

### Workflow 1: Implementing Click-to-Details for Location Entities

**Scenario**: Users should be able to click on any entity in a location view to open a details modal with current status and controls.

**Complete Implementation:**

1. **Set Up SVG Event Handling** ([Interactive Coordinate Conversion](#interactive-coordinate-conversion))
   ```javascript
   class EntityClickHandler {
       constructor(svgElement) {
           this.svgElement = svgElement;
           this.setupEventListeners();
       }
       
       setupEventListeners() {
           this.svgElement.addEventListener('click', (event) => {
               const entityElement = event.target.closest('[data-entity-id]');
               if (entityElement) {
                   const entityId = entityElement.getAttribute('data-entity-id');
                   this.handleEntityClick(event, entityId);
               }
           });
       }
       
       handleEntityClick(event, entityId) {
           // Convert screen click to SVG coordinates for context
           const svgCoords = this.screenToSvgCoordinates(event.clientX, event.clientY);
           
           // Open entity details modal
           this.openEntityModal(entityId, svgCoords);
       }
       
       screenToSvgCoordinates(screenX, screenY) {
           const rect = this.svgElement.getBoundingClientRect();
           const svgPoint = this.svgElement.createSVGPoint();
           svgPoint.x = screenX - rect.left;
           svgPoint.y = screenY - rect.top;
           
           const ctm = this.svgElement.getScreenCTM().inverse();
           return svgPoint.matrixTransform(ctm);
       }
   }
   ```

2. **Template Setup for Clickable Entities** ([Template Integration](#template-integration))
   ```django
   <!-- Ensure all entities have proper data attributes -->
   <svg id="location-svg" viewBox="0 0 1000 800">
     <g id="main-group">
       <!-- Icon entities -->
       {% for entity in icon_entities %}
         <g class="entity-group" data-entity-id="{{ entity.id }}" data-entity-name="{{ entity.name }}">
           <use href="#icon-{{ entity.entity_type.name.lower }}"
                transform="translate({{ entity.position.x }}, {{ entity.position.y }})"/>
         </g>
       {% endfor %}
       
       <!-- Path entities -->
       {% for entity in path_entities %}
         <path class="entity-path" 
               data-entity-id="{{ entity.id }}" 
               data-entity-name="{{ entity.name }}"
               d="{{ entity.path.svg_path }}"/>
       {% endfor %}
     </g>
   </svg>
   ```

3. **Handle Edge Cases** ([Troubleshooting - Click Detection](#click-detection-not-working))
   ```javascript
   class RobustEntityClickHandler extends EntityClickHandler {
       handleEntityClick(event, entityId) {
           // Prevent event bubbling issues
           event.stopPropagation();
           
           // Validate entity exists
           if (!this.validateEntity(entityId)) {
               console.warn('Invalid entity clicked:', entityId);
               return;
           }
           
           // Handle coordinate conversion errors
           try {
               const svgCoords = this.screenToSvgCoordinates(event.clientX, event.clientY);
               this.openEntityModal(entityId, svgCoords);
           } catch (error) {
               console.error('Coordinate conversion failed:', error);
               // Fallback: open modal without coordinate context
               this.openEntityModal(entityId, null);
           }
       }
       
       validateEntity(entityId) {
           // Check if entity element still exists
           return document.querySelector(`[data-entity-id="${entityId}"]`) !== null;
       }
   }
   ```

4. **Initialize Click Handling** ([Template Integration](#template-integration))
   ```javascript
   // Initialize when DOM is ready
   document.addEventListener('DOMContentLoaded', function() {
       const locationSvg = document.getElementById('location-svg');
       if (locationSvg) {
           window.entityClickHandler = new RobustEntityClickHandler(locationSvg);
           console.log('Entity click handling initialized');
       }
   });
   ```

**Expected Result**: Clicking any entity opens a details modal, with reliable coordinate conversion and error handling.

---

### Workflow 2: Implementing Zoom and Pan Controls

**Scenario**: Large location views need zoom and pan functionality for better navigation, especially on mobile devices.

**Implementation Process:**

1. **Create Viewport Controller** ([Zoom and Pan Operations](#zoom-and-pan-operations))
   ```javascript
   class LocationViewportController {
       constructor(svgElement) {
           this.svgElement = svgElement;
           this.mainGroup = svgElement.querySelector('#main-group');
           this.currentZoom = 1.0;
           this.currentPan = { x: 0, y: 0 };
           this.isDragging = false;
           this.lastPanPoint = null;
           
           this.setupControls();
           this.setupMouseHandling();
           this.setupTouchHandling();
       }
       
       setupControls() {
           // Create zoom control buttons
           const controlsHtml = `
               <div class="viewport-controls">
                   <button id="zoom-in" class="btn btn-sm btn-outline-primary">+</button>
                   <button id="zoom-out" class="btn btn-sm btn-outline-primary">−</button>
                   <button id="zoom-fit" class="btn btn-sm btn-outline-secondary">Fit</button>
               </div>
           `;
           
           this.svgElement.parentElement.insertAdjacentHTML('beforeend', controlsHtml);
           
           // Attach event listeners
           document.getElementById('zoom-in').addEventListener('click', () => this.zoomIn());
           document.getElementById('zoom-out').addEventListener('click', () => this.zoomOut());
           document.getElementById('zoom-fit').addEventListener('click', () => this.zoomToFit());
       }
   ```

2. **Implement Zoom Functions** ([Zoom Operations](#zoom-and-pan-operations))
   ```javascript
       zoomIn(factor = 1.2) {
           this.currentZoom = Math.min(this.currentZoom * factor, 5.0); // Max 5x zoom
           this.applyTransform();
       }
       
       zoomOut(factor = 0.8) {
           this.currentZoom = Math.max(this.currentZoom * factor, 0.1); // Min 0.1x zoom
           this.applyTransform();
       }
       
       zoomToFit() {
           // Calculate bounding box of all entities
           const entities = this.svgElement.querySelectorAll('[data-entity-id]');
           if (entities.length === 0) return;
           
           let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
           
           entities.forEach(entity => {
               const bbox = entity.getBBox();
               minX = Math.min(minX, bbox.x);
               minY = Math.min(minY, bbox.y);
               maxX = Math.max(maxX, bbox.x + bbox.width);
               maxY = Math.max(maxY, bbox.y + bbox.height);
           });
           
           // Add padding
           const padding = 50;
           const contentWidth = maxX - minX + (padding * 2);
           const contentHeight = maxY - minY + (padding * 2);
           
           // Calculate zoom to fit
           const svgRect = this.svgElement.getBoundingClientRect();
           const scaleX = svgRect.width / contentWidth;
           const scaleY = svgRect.height / contentHeight;
           this.currentZoom = Math.min(scaleX, scaleY);
           
           // Center the content
           this.currentPan = {
               x: -(minX - padding) * this.currentZoom,
               y: -(minY - padding) * this.currentZoom
           };
           
           this.applyTransform();
       }
   ```

3. **Add Pan Support** ([Pan Operations](#zoom-and-pan-operations))
   ```javascript
       setupMouseHandling() {
           this.svgElement.addEventListener('mousedown', (event) => {
               if (event.button === 1 || (event.button === 0 && event.ctrlKey)) {
                   this.startPan(event.clientX, event.clientY);
                   event.preventDefault();
               }
           });
           
           document.addEventListener('mousemove', (event) => {
               if (this.isDragging) {
                   this.updatePan(event.clientX, event.clientY);
               }
           });
           
           document.addEventListener('mouseup', () => {
               this.endPan();
           });
           
           // Mouse wheel zoom
           this.svgElement.addEventListener('wheel', (event) => {
               event.preventDefault();
               const delta = event.deltaY > 0 ? 0.9 : 1.1;
               this.zoomAt(event.clientX, event.clientY, delta);
           });
       }
       
       startPan(clientX, clientY) {
           this.isDragging = true;
           this.lastPanPoint = { x: clientX, y: clientY };
           this.svgElement.style.cursor = 'grabbing';
       }
       
       updatePan(clientX, clientY) {
           if (!this.isDragging || !this.lastPanPoint) return;
           
           const deltaX = clientX - this.lastPanPoint.x;
           const deltaY = clientY - this.lastPanPoint.y;
           
           this.currentPan.x += deltaX;
           this.currentPan.y += deltaY;
           
           this.lastPanPoint = { x: clientX, y: clientY };
           this.applyTransform();
       }
   ```

4. **Mobile Touch Support** ([Touch and Mobile Issues](#touch-and-mobile-issues))
   ```javascript
       setupTouchHandling() {
           let lastTouchDistance = 0;
           
           this.svgElement.addEventListener('touchstart', (event) => {
               if (event.touches.length === 1) {
                   // Single touch - pan
                   const touch = event.touches[0];
                   this.startPan(touch.clientX, touch.clientY);
               } else if (event.touches.length === 2) {
                   // Two finger - zoom
                   const touch1 = event.touches[0];
                   const touch2 = event.touches[1];
                   lastTouchDistance = this.getTouchDistance(touch1, touch2);
               }
               event.preventDefault();
           });
           
           this.svgElement.addEventListener('touchmove', (event) => {
               if (event.touches.length === 1 && this.isDragging) {
                   const touch = event.touches[0];
                   this.updatePan(touch.clientX, touch.clientY);
               } else if (event.touches.length === 2) {
                   const touch1 = event.touches[0];
                   const touch2 = event.touches[1];
                   const currentDistance = this.getTouchDistance(touch1, touch2);
                   
                   if (lastTouchDistance > 0) {
                       const scale = currentDistance / lastTouchDistance;
                       this.currentZoom *= scale;
                       this.applyTransform();
                   }
                   
                   lastTouchDistance = currentDistance;
               }
               event.preventDefault();
           });
       }
   ```

**Expected Result**: Smooth zoom and pan controls work on both desktop and mobile, with proper touch gesture support.

---

### Workflow 3: Dynamic Entity Positioning Based on Real-Time Data

**Scenario**: Entities need to move to new positions based on real-time location updates (e.g., tracking mobile devices or vehicles).

**Implementation Steps:**

1. **Create Position Update Manager** ([Entity Positioning and Scaling](#entity-positioning-and-scaling))
   ```javascript
   class DynamicEntityPositioner {
       constructor(svgElement) {
           this.svgElement = svgElement;
           this.positionCache = new Map();
           this.animationQueue = [];
           this.isAnimating = false;
       }
       
       updateEntityPosition(entityId, newPosition, animate = true) {
           const element = this.svgElement.querySelector(`[data-entity-id="${entityId}"]`);
           if (!element) {
               console.warn('Entity not found for positioning:', entityId);
               return;
           }
           
           const currentPos = this.getCurrentPosition(element);
           
           if (animate) {
               this.animateToPosition(element, currentPos, newPosition);
           } else {
               this.setPosition(element, newPosition);
           }
           
           // Cache new position
           this.positionCache.set(entityId, newPosition);
       }
       
       getCurrentPosition(element) {
           // Parse current transform to get position
           const transform = element.getAttribute('transform') || '';
           const match = transform.match(/translate\(([^,]+),\s*([^)]+)\)/);
           
           if (match) {
               return {
                   x: parseFloat(match[1]),
                   y: parseFloat(match[2])
               };
           }
           
           return { x: 0, y: 0 };
       }
   ```

2. **Implement Smooth Animation** ([Performance Considerations](#performance-considerations))
   ```javascript
       animateToPosition(element, fromPos, toPos, duration = 1000) {
           const startTime = performance.now();
           
           const animate = (currentTime) => {
               const elapsed = currentTime - startTime;
               const progress = Math.min(elapsed / duration, 1);
               
               // Easing function (ease-out)
               const easeOut = 1 - Math.pow(1 - progress, 3);
               
               const currentX = fromPos.x + (toPos.x - fromPos.x) * easeOut;
               const currentY = fromPos.y + (toPos.y - fromPos.y) * easeOut;
               
               this.setPosition(element, { x: currentX, y: currentY });
               
               if (progress < 1) {
                   requestAnimationFrame(animate);
               }
           };
           
           requestAnimationFrame(animate);
       }
       
       setPosition(element, position) {
           // Preserve other transform properties (scale, rotation)
           const currentTransform = element.getAttribute('transform') || '';
           const scale = this.extractTransformValue(currentTransform, 'scale') || 1;
           const rotation = this.extractTransformValue(currentTransform, 'rotate') || 0;
           
           const newTransform = `translate(${position.x}, ${position.y}) scale(${scale}) rotate(${rotation})`;
           element.setAttribute('transform', newTransform);
       }
   ```

3. **Handle Real-Time Updates** ([Performance - Batch Updates](#performance-issues))
   ```javascript
       processBatchPositionUpdates(positionUpdates) {
           // Group updates to avoid excessive DOM manipulation
           const batchSize = 10;
           let currentBatch = 0;
           
           const processBatch = () => {
               const start = currentBatch * batchSize;
               const end = Math.min(start + batchSize, positionUpdates.length);
               
               for (let i = start; i < end; i++) {
                   const update = positionUpdates[i];
                   this.updateEntityPosition(update.entityId, update.position, update.animate);
               }
               
               currentBatch++;
               
               if (end < positionUpdates.length) {
                   requestAnimationFrame(processBatch);
               }
           };
           
           processBatch();
       }
   ```

4. **Integration with Status Updates** ([Client-Server Integration](../entity-status-display.md#client-server-status-updates))
   ```javascript
   // Extend existing status polling to include position updates
   class EnhancedStatusPoller extends StatusPoller {
       constructor(svgElement) {
           super();
           this.positioner = new DynamicEntityPositioner(svgElement);
       }
       
       updateEntityStates(statusData) {
           // Handle standard status updates
           super.updateEntityStates(statusData);
           
           // Handle position updates if included
           if (statusData.positions) {
               const positionUpdates = Object.entries(statusData.positions).map(
                   ([entityId, posData]) => ({
                       entityId,
                       position: posData.position,
                       animate: posData.animate !== false
                   })
               );
               
               this.positioner.processBatchPositionUpdates(positionUpdates);
           }
       }
   }
   ```

**Expected Result**: Entities smoothly animate to new positions based on real-time data, with efficient batching and performance optimization.

---

### Workflow 4: Troubleshooting Coordinate Transformation Issues

**Scenario**: After a template change, entity click detection stopped working, and zoom controls behave erratically.

**Systematic Debugging:**

1. **Diagnose Click Detection** ([Troubleshooting - Click Detection](#click-detection-not-working))
   ```javascript
   // Debug click detection step by step
   function debugClickDetection(event) {
       console.group('Click Detection Debug');
       
       // 1. Check if event reaches handler
       console.log('Click event:', event);
       console.log('Click target:', event.target);
       
       // 2. Check entity element selection
       const entityElement = event.target.closest('[data-entity-id]');
       console.log('Entity element found:', entityElement);
       
       if (entityElement) {
           console.log('Entity ID:', entityElement.getAttribute('data-entity-id'));
       }
       
       // 3. Test coordinate conversion
       try {
           const svgElement = document.getElementById('location-svg');
           const handler = new SvgInteractionHandler(svgElement);
           const svgCoords = handler.screenToSvgCoordinates(event.clientX, event.clientY);
           console.log('SVG coordinates:', svgCoords);
       } catch (error) {
           console.error('Coordinate conversion failed:', error);
       }
       
       console.groupEnd();
   }
   
   // Temporarily attach debug handler
   document.getElementById('location-svg').addEventListener('click', debugClickDetection);
   ```

2. **Check SVG Structure** ([Template Integration](#template-integration))
   ```javascript
   function validateSvgStructure() {
       const svg = document.getElementById('location-svg');
       console.group('SVG Structure Validation');
       
       // Check required elements
       console.log('SVG element:', svg);
       console.log('Main group:', svg?.querySelector('#main-group'));
       console.log('ViewBox:', svg?.getAttribute('viewBox'));
       console.log('Entities with data-entity-id:', svg?.querySelectorAll('[data-entity-id]').length);
       
       // Check for common issues
       const entitiesWithoutIds = svg?.querySelectorAll('.entity-group:not([data-entity-id])');
       if (entitiesWithoutIds?.length > 0) {
           console.warn('Entities missing data-entity-id:', entitiesWithoutIds);
       }
       
       console.groupEnd();
   }
   
   validateSvgStructure();
   ```

3. **Test Coordinate Transformation Matrix** ([Troubleshooting - Transform Matrix](#entity-positions-incorrect))
   ```javascript
   function debugCoordinateTransformation() {
       const svg = document.getElementById('location-svg');
       console.group('Coordinate Transformation Debug');
       
       try {
           // Test SVG DOM APIs
           console.log('createSVGPoint available:', typeof svg.createSVGPoint === 'function');
           console.log('getScreenCTM available:', typeof svg.getScreenCTM === 'function');
           
           // Test actual transformation
           const ctm = svg.getScreenCTM();
           console.log('Current CTM:', ctm);
           
           if (ctm) {
               console.log('CTM values:', {
                   a: ctm.a, b: ctm.b, c: ctm.c,
                   d: ctm.d, e: ctm.e, f: ctm.f
               });
               
               // Test point transformation
               const testPoint = svg.createSVGPoint();
               testPoint.x = 100;
               testPoint.y = 100;
               
               const transformedPoint = testPoint.matrixTransform(ctm.inverse());
               console.log('Test coordinate transformation:', {
                   screen: { x: 100, y: 100 },
                   svg: { x: transformedPoint.x, y: transformedPoint.y }
               });
           }
           
       } catch (error) {
           console.error('Coordinate transformation error:', error);
       }
       
       console.groupEnd();
   }
   
   debugCoordinateTransformation();
   ```

4. **Fix Common Issues** ([Common Fixes](#click-detection-not-working))
   ```javascript
   // Fix missing data-entity-id attributes
   function fixMissingDataAttributes() {
       const entitiesWithoutIds = document.querySelectorAll('.entity-group:not([data-entity-id])');
       
       entitiesWithoutIds.forEach((element, index) => {
           // Generate temporary ID for debugging
           const tempId = `temp-entity-${index}`;
           element.setAttribute('data-entity-id', tempId);
           console.warn(`Added temporary data-entity-id: ${tempId}`);
       });
   }
   
   // Reset viewport transformation if corrupted
   function resetViewportTransform() {
       const mainGroup = document.querySelector('#main-group');
       if (mainGroup) {
           mainGroup.setAttribute('transform', 'translate(0,0) scale(1)');
           console.log('Reset viewport transform to default');
       }
   }
   
   // Apply fixes
   fixMissingDataAttributes();
   resetViewportTransform();
   ```

**Expected Result**: Systematic debugging identifies and resolves coordinate transformation issues, restoring full functionality.

## Common Patterns Library

### Standard Coordinate Transformation Classes

#### Basic SVG Coordinate Transform
```javascript
// Standard class for coordinate system conversions
class SvgCoordinateTransform {
    constructor(svgElement) {
        this.svgElement = svgElement;
        this.viewBox = this.parseViewBox(svgElement.getAttribute('viewBox'));
    }
    
    parseViewBox(viewBoxStr) {
        if (!viewBoxStr) return { x: 0, y: 0, width: 100, height: 100 };
        
        const [x, y, width, height] = viewBoxStr.split(' ').map(Number);
        return { x, y, width, height };
    }
    
    // Screen coordinates to SVG coordinates
    screenToSvg(screenPoint) {
        const rect = this.svgElement.getBoundingClientRect();
        const svgPoint = this.svgElement.createSVGPoint();
        
        svgPoint.x = screenPoint.x - rect.left;
        svgPoint.y = screenPoint.y - rect.top;
        
        return svgPoint.matrixTransform(
            this.svgElement.getScreenCTM().inverse()
        );
    }
    
    // SVG coordinates to screen coordinates
    svgToScreen(svgPoint) {
        const screenPoint = svgPoint.matrixTransform(
            this.svgElement.getScreenCTM()
        );
        
        const rect = this.svgElement.getBoundingClientRect();
        return {
            x: screenPoint.x + rect.left,
            y: screenPoint.y + rect.top
        };
    }
    
    // Entity local coordinates to SVG coordinates
    entityToSvg(entityCoord, transform) {
        const matrix = this.parseTransform(transform);
        return {
            x: entityCoord.x * matrix.scaleX + matrix.translateX,
            y: entityCoord.y * matrix.scaleY + matrix.translateY
        };
    }
    
    parseTransform(transformStr) {
        const translate = transformStr.match(/translate\(([^)]+)\)/);
        const scale = transformStr.match(/scale\(([^)]+)\)/);
        const rotate = transformStr.match(/rotate\(([^)]+)\)/);
        
        let translateX = 0, translateY = 0, scaleX = 1, scaleY = 1, rotation = 0;
        
        if (translate) {
            [translateX, translateY] = translate[1].split(',').map(Number);
        }
        
        if (scale) {
            const scaleValues = scale[1].split(',').map(Number);
            scaleX = scaleValues[0];
            scaleY = scaleValues[1] || scaleX;
        }
        
        if (rotate) {
            rotation = Number(rotate[1]);
        }
        
        return { translateX, translateY, scaleX, scaleY, rotation };
    }
}
```

#### Standard SVG Interaction Handler
```javascript
// Standard class for handling SVG mouse and touch interactions
class SvgInteractionHandler {
    constructor(svgElement, options = {}) {
        this.svgElement = svgElement;
        this.coordinateTransform = new SvgCoordinateTransform(svgElement);
        this.isInteracting = false;
        this.lastInteractionPoint = null;
        
        // Configuration options
        this.options = {
            enableClick: options.enableClick !== false,
            enableDrag: options.enableDrag !== false,
            clickThreshold: options.clickThreshold || 5,
            ...options
        };
        
        this.bindEvents();
    }
    
    bindEvents() {
        if (this.options.enableClick) {
            this.svgElement.addEventListener('click', (e) => this.handleClick(e));
        }
        
        if (this.options.enableDrag) {
            this.svgElement.addEventListener('mousedown', (e) => this.handleMouseDown(e));
            document.addEventListener('mousemove', (e) => this.handleMouseMove(e));
            document.addEventListener('mouseup', (e) => this.handleMouseUp(e));
            
            // Touch events for mobile
            this.svgElement.addEventListener('touchstart', (e) => this.handleTouchStart(e));
            document.addEventListener('touchmove', (e) => this.handleTouchMove(e));
            document.addEventListener('touchend', (e) => this.handleTouchEnd(e));
        }
    }
    
    handleClick(event) {
        const svgPoint = this.coordinateTransform.screenToSvg({
            x: event.clientX,
            y: event.clientY
        });
        
        const clickedElement = this.findEntityAt(svgPoint);
        if (clickedElement) {
            this.onEntityClick(clickedElement, svgPoint, event);
        } else {
            this.onBackgroundClick(svgPoint, event);
        }
    }
    
    findEntityAt(svgPoint) {
        // Find the topmost entity element at the given SVG coordinate
        const elements = document.elementsFromPoint(
            svgPoint.x, svgPoint.y
        ).filter(el => 
            el.closest('[data-entity-id]') && 
            el.closest('svg') === this.svgElement
        );
        
        return elements.length > 0 ? elements[0].closest('[data-entity-id]') : null;
    }
    
    onEntityClick(entityElement, svgPoint, originalEvent) {
        const entityId = entityElement.getAttribute('data-entity-id');
        const entityType = entityElement.getAttribute('data-entity-type');
        
        // Emit custom event
        this.svgElement.dispatchEvent(new CustomEvent('entityClick', {
            detail: {
                entityId,
                entityType,
                svgCoordinates: svgPoint,
                screenCoordinates: { x: originalEvent.clientX, y: originalEvent.clientY },
                element: entityElement
            }
        }));
    }
    
    onBackgroundClick(svgPoint, originalEvent) {
        this.svgElement.dispatchEvent(new CustomEvent('backgroundClick', {
            detail: {
                svgCoordinates: svgPoint,
                screenCoordinates: { x: originalEvent.clientX, y: originalEvent.clientY }
            }
        }));
    }
    
    // Touch event handling
    handleTouchStart(event) {
        if (event.touches.length === 1) {
            const touch = event.touches[0];
            this.handleMouseDown({
                clientX: touch.clientX,
                clientY: touch.clientY,
                target: event.target,
                preventDefault: () => event.preventDefault()
            });
        }
    }
    
    handleTouchMove(event) {
        if (event.touches.length === 1) {
            const touch = event.touches[0];
            this.handleMouseMove({
                clientX: touch.clientX,
                clientY: touch.clientY
            });
        }
    }
    
    handleTouchEnd(event) {
        this.handleMouseUp({});
    }
}
```

#### Standard Viewport Controller
```javascript
// Standard class for managing SVG zoom and pan operations
class SvgViewportController {
    constructor(svgElement, options = {}) {
        this.svgElement = svgElement;
        this.currentTransform = { scale: 1, translateX: 0, translateY: 0 };
        this.originalViewBox = this.parseViewBox(svgElement.getAttribute('viewBox'));
        
        this.options = {
            minScale: options.minScale || 0.1,
            maxScale: options.maxScale || 10,
            zoomSpeed: options.zoomSpeed || 0.1,
            enablePan: options.enablePan !== false,
            enableZoom: options.enableZoom !== false,
            ...options
        };
        
        this.bindEvents();
    }
    
    parseViewBox(viewBoxStr) {
        if (!viewBoxStr) return { x: 0, y: 0, width: 100, height: 100 };
        const [x, y, width, height] = viewBoxStr.split(' ').map(Number);
        return { x, y, width, height };
    }
    
    bindEvents() {
        if (this.options.enableZoom) {
            this.svgElement.addEventListener('wheel', (e) => this.handleWheel(e));
        }
        
        if (this.options.enablePan) {
            let isPanning = false;
            let startPoint = null;
            let startTransform = null;
            
            this.svgElement.addEventListener('mousedown', (e) => {
                if (e.button === 1 || (e.button === 0 && e.ctrlKey)) { // Middle mouse or Ctrl+click
                    isPanning = true;
                    startPoint = { x: e.clientX, y: e.clientY };
                    startTransform = { ...this.currentTransform };
                    e.preventDefault();
                }
            });
            
            document.addEventListener('mousemove', (e) => {
                if (isPanning && startPoint) {
                    const dx = (e.clientX - startPoint.x) / this.currentTransform.scale;
                    const dy = (e.clientY - startPoint.y) / this.currentTransform.scale;
                    
                    this.currentTransform.translateX = startTransform.translateX + dx;
                    this.currentTransform.translateY = startTransform.translateY + dy;
                    
                    this.updateViewBox();
                    e.preventDefault();
                }
            });
            
            document.addEventListener('mouseup', (e) => {
                if (isPanning) {
                    isPanning = false;
                    startPoint = null;
                    startTransform = null;
                }
            });
        }
    }
    
    handleWheel(event) {
        event.preventDefault();
        
        const rect = this.svgElement.getBoundingClientRect();
        const centerX = (event.clientX - rect.left) / rect.width;
        const centerY = (event.clientY - rect.top) / rect.height;
        
        const scaleDelta = event.deltaY > 0 ? 
            (1 - this.options.zoomSpeed) : 
            (1 + this.options.zoomSpeed);
        
        this.zoomAt(centerX, centerY, scaleDelta);
    }
    
    zoomAt(centerX, centerY, scaleDelta) {
        const newScale = Math.max(
            this.options.minScale,
            Math.min(this.options.maxScale, this.currentTransform.scale * scaleDelta)
        );
        
        if (newScale !== this.currentTransform.scale) {
            // Calculate new translation to keep zoom centered
            const scaleChange = newScale / this.currentTransform.scale;
            
            const viewBoxCenterX = this.originalViewBox.x + centerX * this.originalViewBox.width;
            const viewBoxCenterY = this.originalViewBox.y + centerY * this.originalViewBox.height;
            
            this.currentTransform.translateX = viewBoxCenterX - 
                (viewBoxCenterX - this.currentTransform.translateX) * scaleChange;
            this.currentTransform.translateY = viewBoxCenterY - 
                (viewBoxCenterY - this.currentTransform.translateY) * scaleChange;
            
            this.currentTransform.scale = newScale;
            this.updateViewBox();
        }
    }
    
    updateViewBox() {
        const width = this.originalViewBox.width / this.currentTransform.scale;
        const height = this.originalViewBox.height / this.currentTransform.scale;
        
        const x = this.currentTransform.translateX - width / 2;
        const y = this.currentTransform.translateY - height / 2;
        
        this.svgElement.setAttribute('viewBox', `${x} ${y} ${width} ${height}`);
        
        // Emit transform change event
        this.svgElement.dispatchEvent(new CustomEvent('viewportChanged', {
            detail: {
                scale: this.currentTransform.scale,
                translateX: this.currentTransform.translateX,
                translateY: this.currentTransform.translateY,
                viewBox: { x, y, width, height }
            }
        }));
    }
    
    // Public API methods
    zoomIn() {
        this.zoomAt(0.5, 0.5, 1 + this.options.zoomSpeed);
    }
    
    zoomOut() {
        this.zoomAt(0.5, 0.5, 1 - this.options.zoomSpeed);
    }
    
    resetView() {
        this.currentTransform = { scale: 1, translateX: 0, translateY: 0 };
        this.svgElement.setAttribute('viewBox', 
            `${this.originalViewBox.x} ${this.originalViewBox.y} ${this.originalViewBox.width} ${this.originalViewBox.height}`
        );
        this.updateViewBox();
    }
    
    fitToContent() {
        // Calculate bounding box of all visible entities
        const entities = this.svgElement.querySelectorAll('[data-entity-id]');
        if (entities.length === 0) return;
        
        let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
        
        entities.forEach(entity => {
            const bbox = entity.getBBox();
            minX = Math.min(minX, bbox.x);
            minY = Math.min(minY, bbox.y);
            maxX = Math.max(maxX, bbox.x + bbox.width);
            maxY = Math.max(maxY, bbox.y + bbox.height);
        });
        
        const padding = Math.min(maxX - minX, maxY - minY) * 0.1;
        const contentWidth = maxX - minX + padding * 2;
        const contentHeight = maxY - minY + padding * 2;
        
        this.svgElement.setAttribute('viewBox', 
            `${minX - padding} ${minY - padding} ${contentWidth} ${contentHeight}`
        );
    }
}
```

### Standard Entity Positioning Patterns

#### Entity Position Manager
```javascript
// Standard class for managing entity positions and transforms
class EntityPositionManager {
    constructor(svgElement) {
        this.svgElement = svgElement;
        this.coordinateTransform = new SvgCoordinateTransform(svgElement);
    }
    
    updateEntityPosition(entityId, position, options = {}) {
        const entityElement = this.svgElement.querySelector(
            `[data-entity-id="${entityId}"]`
        );
        
        if (!entityElement) {
            console.warn(`Entity ${entityId} not found in SVG`);
            return;
        }
        
        const transform = this.buildTransform(position, options);
        const targetElement = entityElement.querySelector('use, path') || entityElement;
        
        if (options.animate) {
            this.animateTransform(targetElement, transform, options.duration || 300);
        } else {
            targetElement.setAttribute('transform', transform);
        }
        
        // Update data attributes for tracking
        entityElement.setAttribute('data-x', position.x);
        entityElement.setAttribute('data-y', position.y);
        if (position.scale) entityElement.setAttribute('data-scale', position.scale);
        if (position.rotation) entityElement.setAttribute('data-rotation', position.rotation);
    }
    
    buildTransform(position, options = {}) {
        const { x, y, scale = 1, rotation = 0 } = position;
        const transforms = [];
        
        transforms.push(`translate(${x}, ${y})`);
        
        if (scale !== 1) {
            transforms.push(`scale(${scale})`);
        }
        
        if (rotation !== 0) {
            transforms.push(`rotate(${rotation})`);
        }
        
        return transforms.join(' ');
    }
    
    animateTransform(element, newTransform, duration) {
        const currentTransform = element.getAttribute('transform') || '';
        
        // Create animation element
        const animateTransform = document.createElementNS(
            'http://www.w3.org/2000/svg', 
            'animateTransform'
        );
        
        animateTransform.setAttribute('attributeName', 'transform');
        animateTransform.setAttribute('attributeType', 'XML');
        animateTransform.setAttribute('type', 'transform');
        animateTransform.setAttribute('from', currentTransform);
        animateTransform.setAttribute('to', newTransform);
        animateTransform.setAttribute('dur', `${duration}ms`);
        animateTransform.setAttribute('fill', 'freeze');
        
        element.appendChild(animateTransform);
        
        // Clean up animation after completion
        setTimeout(() => {
            element.setAttribute('transform', newTransform);
            if (animateTransform.parentNode) {
                animateTransform.parentNode.removeChild(animateTransform);
            }
        }, duration);
    }
    
    getEntityPosition(entityId) {
        const entityElement = this.svgElement.querySelector(
            `[data-entity-id="${entityId}"]`
        );
        
        if (!entityElement) return null;
        
        return {
            x: parseFloat(entityElement.getAttribute('data-x')) || 0,
            y: parseFloat(entityElement.getAttribute('data-y')) || 0,
            scale: parseFloat(entityElement.getAttribute('data-scale')) || 1,
            rotation: parseFloat(entityElement.getAttribute('data-rotation')) || 0
        };
    }
    
    moveEntity(entityId, deltaX, deltaY, options = {}) {
        const currentPosition = this.getEntityPosition(entityId);
        if (!currentPosition) return;
        
        const newPosition = {
            ...currentPosition,
            x: currentPosition.x + deltaX,
            y: currentPosition.y + deltaY
        };
        
        this.updateEntityPosition(entityId, newPosition, options);
    }
    
    scaleEntity(entityId, scaleFactor, options = {}) {
        const currentPosition = this.getEntityPosition(entityId);
        if (!currentPosition) return;
        
        const newPosition = {
            ...currentPosition,
            scale: currentPosition.scale * scaleFactor
        };
        
        this.updateEntityPosition(entityId, newPosition, options);
    }
}
```

### Standard Template Integration Patterns

#### Basic SVG Template Structure
```django
<!-- Standard SVG structure for location views -->
<div class="location-view-container">
  <svg id="location-svg" 
       class="location-view-svg"
       viewBox="{{ viewbox.x }} {{ viewbox.y }} {{ viewbox.width }} {{ viewbox.height }}"
       xmlns="http://www.w3.org/2000/svg">
    
    <!-- Background layers -->
    <defs>
      <!-- Entity icon definitions -->
      {% for entity_type in entity_types_with_icons %}
        <symbol id="icon-{{ entity_type.name.lower }}" 
                viewBox="{{ entity_type.get_viewbox }}">
          {% include entity_type.get_icon_template %}
        </symbol>
      {% endfor %}
      
      <!-- Common patterns and gradients -->
      <pattern id="grid-pattern" patternUnits="userSpaceOnUse" width="10" height="10">
        <path d="M 10 0 L 0 0 0 10" fill="none" stroke="#e0e0e0" stroke-width="0.5"/>
      </pattern>
    </defs>
    
    <!-- Background grid (optional) -->
    {% if show_grid %}
      <rect width="100%" height="100%" fill="url(#grid-pattern)"/>
    {% endif %}
    
    <!-- Floor plan background -->
    {% if location.background_image %}
      <image href="{{ location.background_image.url }}" 
             width="{{ viewbox.width }}" 
             height="{{ viewbox.height }}"/>
    {% endif %}
    
    <!-- Path-based entities (rooms, zones) -->
    {% for entity in path_entities %}
      <g class="entity-group" 
         data-entity-id="{{ entity.id }}" 
         data-entity-type="{{ entity.entity_type.name.lower }}">
        <path class="entity-path {{ entity.get_status_css_classes|join:' ' }}"
              d="{{ entity.path.svg_path }}"
              style="{{ entity.get_path_styling }}"/>
      </g>
    {% endfor %}
    
    <!-- Icon-based entities (sensors, devices) -->
    {% for entity in positioned_entities %}
      <g class="entity-group" 
         data-entity-id="{{ entity.id }}" 
         data-entity-type="{{ entity.entity_type.name.lower }}">
        <use href="#icon-{{ entity.entity_type.name.lower }}" 
             class="entity-svg {{ entity.get_status_css_classes|join:' ' }}"
             transform="translate({{ entity.position.x }}, {{ entity.position.y }}) 
                        scale({{ entity.position.scale|default:1.0 }}) 
                        rotate({{ entity.position.rotation|default:0 }})"/>
      </g>
    {% endfor %}
    
    <!-- Overlay elements -->
    <g class="overlay-group">
      <!-- Selection indicators -->
      <circle id="selection-indicator" 
              class="selection-circle" 
              r="25" 
              fill="none" 
              stroke="#007bff" 
              stroke-width="2"
              style="display: none"/>
      
      <!-- Temporary drawing elements -->
      <g id="temp-drawings"></g>
    </g>
  </svg>
  
  <!-- SVG Controls -->
  <div class="svg-controls">
    <button id="zoom-in" class="btn btn-sm btn-outline-secondary">
      <i class="fas fa-search-plus"></i>
    </button>
    <button id="zoom-out" class="btn btn-sm btn-outline-secondary">
      <i class="fas fa-search-minus"></i>
    </button>
    <button id="fit-content" class="btn btn-sm btn-outline-secondary">
      <i class="fas fa-expand-arrows-alt"></i>
    </button>
    <button id="reset-view" class="btn btn-sm btn-outline-secondary">
      <i class="fas fa-home"></i>
    </button>
  </div>
</div>
```

#### Standard JavaScript Initialization
```javascript
// Standard pattern for initializing SVG coordinate operations
document.addEventListener('DOMContentLoaded', function() {
    const svgElement = document.getElementById('location-svg');
    if (!svgElement) return;
    
    // Initialize coordinate systems
    const coordinateTransform = new SvgCoordinateTransform(svgElement);
    const interactionHandler = new SvgInteractionHandler(svgElement, {
        enableClick: true,
        enableDrag: false
    });
    const viewportController = new SvgViewportController(svgElement, {
        minScale: 0.1,
        maxScale: 5.0,
        enablePan: true,
        enableZoom: true
    });
    const positionManager = new EntityPositionManager(svgElement);
    
    // Bind control buttons
    document.getElementById('zoom-in')?.addEventListener('click', () => {
        viewportController.zoomIn();
    });
    
    document.getElementById('zoom-out')?.addEventListener('click', () => {
        viewportController.zoomOut();
    });
    
    document.getElementById('fit-content')?.addEventListener('click', () => {
        viewportController.fitToContent();
    });
    
    document.getElementById('reset-view')?.addEventListener('click', () => {
        viewportController.resetView();
    });
    
    // Handle entity interactions
    svgElement.addEventListener('entityClick', function(event) {
        const { entityId, svgCoordinates, element } = event.detail;
        
        // Show selection indicator
        const indicator = document.getElementById('selection-indicator');
        indicator.setAttribute('cx', svgCoordinates.x);
        indicator.setAttribute('cy', svgCoordinates.y);
        indicator.style.display = 'block';
        
        // Open entity details modal
        openEntityDetailsModal(entityId);
    });
    
    svgElement.addEventListener('backgroundClick', function(event) {
        // Hide selection indicator
        document.getElementById('selection-indicator').style.display = 'none';
    });
    
    // Handle viewport changes
    svgElement.addEventListener('viewportChanged', function(event) {
        const { scale, translateX, translateY } = event.detail;
        
        // Update scale-dependent elements
        updateScaleDependentElements(scale);
        
        // Trigger entity visibility updates if needed
        updateEntityVisibility(event.detail.viewBox);
    });
    
    // Store references globally for debugging
    window.svgCoordinateTransform = coordinateTransform;
    window.svgInteractionHandler = interactionHandler;
    window.svgViewportController = viewportController;
    window.entityPositionManager = positionManager;
});

// Utility functions
function openEntityDetailsModal(entityId) {
    // Standard modal opening pattern
    fetch(`/entity/${entityId}/details/`)
        .then(response => response.json())
        .then(data => {
            if (data.modal) {
                showModal(data.modal);
            }
        })
        .catch(error => {
            console.error('Error loading entity details:', error);
        });
}

function updateScaleDependentElements(scale) {
    // Adjust element sizes based on zoom level
    const scaleDependentElements = document.querySelectorAll('.scale-dependent');
    scaleDependentElements.forEach(element => {
        const baseSize = parseFloat(element.getAttribute('data-base-size')) || 1;
        const newSize = Math.max(0.5, baseSize / scale);
        element.setAttribute('stroke-width', newSize);
    });
}

function updateEntityVisibility(viewBox) {
    // Hide entities outside visible area for performance
    const entities = document.querySelectorAll('[data-entity-id]');
    entities.forEach(entity => {
        const bbox = entity.getBBox();
        const isVisible = !(
            bbox.x + bbox.width < viewBox.x ||
            bbox.x > viewBox.x + viewBox.width ||
            bbox.y + bbox.height < viewBox.y ||
            bbox.y > viewBox.y + viewBox.height
        );
        
        entity.style.display = isVisible ? 'block' : 'none';
    });
}
```

### Standard Testing Patterns for Coordinate Operations

#### Coordinate Conversion Testing
```javascript
// Standard test patterns for coordinate transformations
function testCoordinateConversions() {
    const svg = document.getElementById('location-svg');
    const transform = new SvgCoordinateTransform(svg);
    
    // Test screen to SVG conversion
    const screenPoint = { x: 100, y: 50 };
    const svgPoint = transform.screenToSvg(screenPoint);
    console.assert(typeof svgPoint.x === 'number', 'SVG X coordinate should be number');
    console.assert(typeof svgPoint.y === 'number', 'SVG Y coordinate should be number');
    
    // Test round-trip conversion
    const backToScreen = transform.svgToScreen(svgPoint);
    const tolerance = 1; // 1 pixel tolerance
    console.assert(
        Math.abs(backToScreen.x - screenPoint.x) < tolerance,
        'Round-trip X conversion failed'
    );
    console.assert(
        Math.abs(backToScreen.y - screenPoint.y) < tolerance,
        'Round-trip Y conversion failed'
    );
    
    console.log('Coordinate conversion tests passed');
}

function testViewportOperations() {
    const svg = document.getElementById('location-svg');
    const viewport = new SvgViewportController(svg);
    
    const originalViewBox = svg.getAttribute('viewBox');
    
    // Test zoom operations
    viewport.zoomIn();
    const zoomedViewBox = svg.getAttribute('viewBox');
    console.assert(zoomedViewBox !== originalViewBox, 'Zoom in should change viewBox');
    
    viewport.resetView();
    const resetViewBox = svg.getAttribute('viewBox');
    console.assert(resetViewBox === originalViewBox, 'Reset should restore original viewBox');
    
    console.log('Viewport operation tests passed');
}

function testEntityPositioning() {
    const svg = document.getElementById('location-svg');
    const positionManager = new EntityPositionManager(svg);
    
    // Create test entity
    const testEntityHtml = `
        <g data-entity-id="test-entity" class="entity-group">
            <use href="#icon-motion-sensor" class="entity-svg"/>
        </g>
    `;
    svg.innerHTML += testEntityHtml;
    
    // Test position update
    const newPosition = { x: 100, y: 150, scale: 1.5, rotation: 45 };
    positionManager.updateEntityPosition('test-entity', newPosition);
    
    // Verify position was applied
    const retrievedPosition = positionManager.getEntityPosition('test-entity');
    console.assert(retrievedPosition.x === 100, 'X position not set correctly');
    console.assert(retrievedPosition.y === 150, 'Y position not set correctly');
    console.assert(retrievedPosition.scale === 1.5, 'Scale not set correctly');
    console.assert(retrievedPosition.rotation === 45, 'Rotation not set correctly');
    
    console.log('Entity positioning tests passed');
}
```

#### Performance Testing Pattern
```javascript
// Standard performance testing for coordinate operations
function performanceTestCoordinateOperations() {
    const svg = document.getElementById('location-svg');
    const transform = new SvgCoordinateTransform(svg);
    
    const testPoints = [];
    for (let i = 0; i < 1000; i++) {
        testPoints.push({
            x: Math.random() * window.innerWidth,
            y: Math.random() * window.innerHeight
        });
    }
    
    // Test coordinate conversion performance
    console.time('1000 screen-to-SVG conversions');
    testPoints.forEach(point => {
        transform.screenToSvg(point);
    });
    console.timeEnd('1000 screen-to-SVG conversions');
    
    // Test entity positioning performance
    const positionManager = new EntityPositionManager(svg);
    const positions = testPoints.map(point => ({
        x: point.x,
        y: point.y,
        scale: 1 + Math.random(),
        rotation: Math.random() * 360
    }));
    
    console.time('1000 entity position updates');
    positions.forEach((position, index) => {
        positionManager.updateEntityPosition(`entity-${index}`, position);
    });
    console.timeEnd('1000 entity position updates');
    
    console.log('Performance tests completed');
}
```

## Performance Optimization Guide

### Overview

SVG coordinate operations can become computationally expensive with complex transformations, frequent updates, or large numbers of entities. This guide provides optimization strategies for maintaining smooth, responsive coordinate operations.

### Coordinate Transformation Optimization

#### Caching Transformation Matrices
```javascript
// Cache expensive matrix calculations
class OptimizedCoordinateTransform extends SvgCoordinateTransform {
    constructor(svgElement) {
        super(svgElement);
        this.matrixCache = new Map();
        this.cacheHitCount = 0;
        this.cacheMissCount = 0;
    }
    
    getScreenCTM() {
        const cacheKey = this.generateMatrixCacheKey();
        
        if (this.matrixCache.has(cacheKey)) {
            this.cacheHitCount++;
            return this.matrixCache.get(cacheKey);
        }
        
        const matrix = this.svgElement.getScreenCTM();
        this.matrixCache.set(cacheKey, matrix);
        this.cacheMissCount++;
        
        // Limit cache size to prevent memory leaks
        if (this.matrixCache.size > 100) {
            const firstKey = this.matrixCache.keys().next().value;
            this.matrixCache.delete(firstKey);
        }
        
        return matrix;
    }
    
    generateMatrixCacheKey() {
        const viewBox = this.svgElement.getAttribute('viewBox');
        const transform = this.svgElement.getAttribute('transform') || '';
        const boundingRect = this.svgElement.getBoundingClientRect();
        
        return `${viewBox}|${transform}|${boundingRect.width}x${boundingRect.height}`;
    }
    
    invalidateCache() {
        this.matrixCache.clear();
    }
    
    getCacheStats() {
        const totalRequests = this.cacheHitCount + this.cacheMissCount;
        const hitRate = totalRequests > 0 ? (this.cacheHitCount / totalRequests) * 100 : 0;
        
        return {
            hits: this.cacheHitCount,
            misses: this.cacheMissCount,
            hitRate: hitRate.toFixed(1) + '%',
            cacheSize: this.matrixCache.size
        };
    }
}
```

#### Optimized Batch Coordinate Conversions
```javascript
// Process multiple coordinates efficiently
class BatchCoordinateProcessor {
    constructor(svgElement) {
        this.svgElement = svgElement;
        this.transform = new OptimizedCoordinateTransform(svgElement);
    }
    
    batchScreenToSvg(screenPoints) {
        const results = [];
        const matrix = this.transform.getScreenCTM()?.inverse();
        
        if (!matrix) {
            return screenPoints.map(p => ({ x: p.x, y: p.y }));
        }
        
        const rect = this.svgElement.getBoundingClientRect();
        
        // Process all points using the same matrix
        for (const point of screenPoints) {
            const svgPoint = this.svgElement.createSVGPoint();
            svgPoint.x = point.x - rect.left;
            svgPoint.y = point.y - rect.top;
            
            const transformed = svgPoint.matrixTransform(matrix);
            results.push({ x: transformed.x, y: transformed.y });
        }
        
        return results;
    }
    
    batchSvgToScreen(svgPoints) {
        const results = [];
        const matrix = this.transform.getScreenCTM();
        
        if (!matrix) {
            return svgPoints;
        }
        
        const rect = this.svgElement.getBoundingClientRect();
        
        // Process all points using the same matrix
        for (const point of svgPoints) {
            const svgPoint = this.svgElement.createSVGPoint();
            svgPoint.x = point.x;
            svgPoint.y = point.y;
            
            const transformed = svgPoint.matrixTransform(matrix);
            results.push({ 
                x: transformed.x + rect.left, 
                y: transformed.y + rect.top 
            });
        }
        
        return results;
    }
    
    // Optimized bulk entity position updates
    updateEntityPositions(entityUpdates) {
        const startTime = performance.now();
        
        // Group updates by transformation type
        const transformGroups = this.groupTransformations(entityUpdates);
        
        // Process each group efficiently
        Object.entries(transformGroups).forEach(([transformType, entities]) => {
            this.processTransformGroup(transformType, entities);
        });
        
        const endTime = performance.now();
        console.log(`Batch position update: ${entityUpdates.length} entities in ${(endTime - startTime).toFixed(2)}ms`);
    }
    
    groupTransformations(entityUpdates) {
        const groups = {};
        
        entityUpdates.forEach(update => {
            const key = `${update.scale || 1}_${update.rotation || 0}`;
            if (!groups[key]) {
                groups[key] = [];
            }
            groups[key].push(update);
        });
        
        return groups;
    }
    
    processTransformGroup(transformType, entities) {
        // Apply same transformation parameters to multiple entities
        entities.forEach(entity => {
            const element = document.querySelector(`[data-entity-id="${entity.id}"]`);
            if (element) {
                const transform = `translate(${entity.x}, ${entity.y})`;
                const targetElement = element.querySelector('use, path') || element;
                targetElement.setAttribute('transform', transform);
            }
        });
    }
}
```

### Viewport Operation Performance

#### Optimized Viewport Controller
```javascript
// High-performance viewport operations
class PerformantViewportController extends SvgViewportController {
    constructor(svgElement, options = {}) {
        super(svgElement, options);
        this.updateThrottle = options.updateThrottle || 16; // ~60fps
        this.lastUpdateTime = 0;
        this.pendingUpdate = null;
        this.performanceMode = this.detectPerformanceMode();
    }
    
    detectPerformanceMode() {
        // Detect if we need to use performance mode
        const entityCount = this.svgElement.querySelectorAll('[data-entity-id]').length;
        const isLowEndDevice = navigator.hardwareConcurrency < 4;
        const hasLimitedMemory = navigator.deviceMemory && navigator.deviceMemory < 4;
        
        return entityCount > 100 || isLowEndDevice || hasLimitedMemory;
    }
    
    updateViewBox() {
        const now = performance.now();
        
        // Throttle updates to prevent excessive redraws
        if (now - this.lastUpdateTime < this.updateThrottle) {
            if (this.pendingUpdate) {
                cancelAnimationFrame(this.pendingUpdate);
            }
            
            this.pendingUpdate = requestAnimationFrame(() => {
                this.performViewBoxUpdate();
            });
            return;
        }
        
        this.performViewBoxUpdate();
    }
    
    performViewBoxUpdate() {
        this.lastUpdateTime = performance.now();
        
        const width = this.originalViewBox.width / this.currentTransform.scale;
        const height = this.originalViewBox.height / this.currentTransform.scale;
        
        const x = this.currentTransform.translateX - width / 2;
        const y = this.currentTransform.translateY - height / 2;
        
        // Use CSS transforms for better performance if supported
        if (this.performanceMode && this.supportsCSSTransforms()) {
            this.applyCSSTransform();
        } else {
            this.svgElement.setAttribute('viewBox', `${x} ${y} ${width} ${height}`);
        }
        
        // Emit transform change event (throttled)
        this.emitThrottledViewportEvent();
    }
    
    supportsCSSTransforms() {
        return CSS.supports('transform', 'scale(1) translate(0px, 0px)');
    }
    
    applyCSSTransform() {
        const scale = this.currentTransform.scale;
        const translateX = -this.currentTransform.translateX * scale;
        const translateY = -this.currentTransform.translateY * scale;
        
        this.svgElement.style.transform = 
            `scale(${scale}) translate(${translateX}px, ${translateY}px)`;
    }
    
    emitThrottledViewportEvent() {
        // Only emit events at most once per frame
        if (!this.eventPending) {
            this.eventPending = true;
            
            requestAnimationFrame(() => {
                this.svgElement.dispatchEvent(new CustomEvent('viewportChanged', {
                    detail: {
                        scale: this.currentTransform.scale,
                        translateX: this.currentTransform.translateX,
                        translateY: this.currentTransform.translateY,
                        viewBox: this.getCurrentViewBox()
                    }
                }));
                this.eventPending = false;
            });
        }
    }
    
    // Optimized zoom operation
    zoomAt(centerX, centerY, scaleDelta) {
        // Pre-calculate to avoid expensive operations during zoom
        const newScale = this.clampScale(this.currentTransform.scale * scaleDelta);
        
        if (newScale === this.currentTransform.scale) {
            return; // No change needed
        }
        
        // Use efficient transform calculation
        this.updateTransformOptimized(centerX, centerY, newScale);
        
        if (this.performanceMode) {
            // In performance mode, defer heavy operations
            this.deferHeavyOperations();
        } else {
            this.updateViewBox();
        }
    }
    
    clampScale(scale) {
        return Math.max(
            this.options.minScale,
            Math.min(this.options.maxScale, scale)
        );
    }
    
    updateTransformOptimized(centerX, centerY, newScale) {
        // Optimized transform calculation
        const scaleChange = newScale / this.currentTransform.scale;
        
        const viewBoxCenterX = this.originalViewBox.x + centerX * this.originalViewBox.width;
        const viewBoxCenterY = this.originalViewBox.y + centerY * this.originalViewBox.height;
        
        // Update transform in one operation
        this.currentTransform.translateX = viewBoxCenterX - 
            (viewBoxCenterX - this.currentTransform.translateX) * scaleChange;
        this.currentTransform.translateY = viewBoxCenterY - 
            (viewBoxCenterY - this.currentTransform.translateY) * scaleChange;
        this.currentTransform.scale = newScale;
    }
    
    deferHeavyOperations() {
        // Defer expensive operations until zoom is complete
        clearTimeout(this.deferredOperationsTimeout);
        this.deferredOperationsTimeout = setTimeout(() => {
            this.updateViewBox();
            this.updateEntityVisibility();
        }, 100);
    }
}
```

### Entity Positioning Performance

#### High-Performance Entity Position Manager
```javascript
// Optimized entity positioning with spatial indexing
class PerformantEntityPositionManager extends EntityPositionManager {
    constructor(svgElement) {
        super(svgElement);
        this.spatialIndex = new SpatialIndex();
        this.positionCache = new Map();
        this.updateQueue = [];
        this.isProcessingQueue = false;
    }
    
    // Spatial indexing for efficient entity queries
    buildSpatialIndex() {
        this.spatialIndex.clear();
        
        const entities = this.svgElement.querySelectorAll('[data-entity-id]');
        entities.forEach(entity => {
            const entityId = entity.getAttribute('data-entity-id');
            const position = this.getEntityPosition(entityId);
            
            if (position) {
                this.spatialIndex.insert({
                    id: entityId,
                    x: position.x,
                    y: position.y,
                    width: 32, // Assume standard entity size
                    height: 32
                });
            }
        });
    }
    
    // Queue position updates for batch processing
    queuePositionUpdate(entityId, position, options = {}) {
        this.updateQueue.push({ entityId, position, options });
        
        if (!this.isProcessingQueue) {
            this.processUpdateQueue();
        }
    }
    
    async processUpdateQueue() {
        this.isProcessingQueue = true;
        
        while (this.updateQueue.length > 0) {
            const batch = this.updateQueue.splice(0, 20); // Process 20 at a time
            
            // Process batch synchronously for better performance
            batch.forEach(update => {
                this.updateEntityPositionImmediate(
                    update.entityId, 
                    update.position, 
                    update.options
                );
            });
            
            // Yield control periodically
            if (this.updateQueue.length > 0) {
                await new Promise(resolve => setTimeout(resolve, 0));
            }
        }
        
        this.isProcessingQueue = false;
    }
    
    updateEntityPositionImmediate(entityId, position, options = {}) {
        const element = this.svgElement.querySelector(`[data-entity-id="${entityId}"]`);
        
        if (!element) {
            return;
        }
        
        // Use cached transform calculation when possible
        const transformString = this.getCachedTransform(position) || 
                               this.buildTransform(position, options);
        
        const targetElement = element.querySelector('use, path') || element;
        
        if (options.animate && !this.performanceMode) {
            this.animateTransform(targetElement, transformString, options.duration || 300);
        } else {
            // Direct attribute update is faster than animation
            targetElement.setAttribute('transform', transformString);
        }
        
        // Update position cache
        this.positionCache.set(entityId, position);
        
        // Update spatial index
        this.spatialIndex.update(entityId, position);
    }
    
    getCachedTransform(position) {
        const cacheKey = `${position.x}_${position.y}_${position.scale || 1}_${position.rotation || 0}`;
        return this.transformCache?.get(cacheKey);
    }
    
    // Efficient entity queries using spatial indexing
    getEntitiesInRegion(x, y, width, height) {
        return this.spatialIndex.query(x, y, width, height);
    }
    
    getNearestEntities(x, y, maxDistance = 50, limit = 10) {
        return this.spatialIndex.queryNearest(x, y, maxDistance, limit);
    }
    
    // Bulk position updates with optimizations
    updateMultipleEntityPositions(positionUpdates) {
        const startTime = performance.now();
        
        // Sort updates to minimize DOM access patterns
        positionUpdates.sort((a, b) => a.entityId.localeCompare(b.entityId));
        
        // Disable transitions during bulk update
        this.disableTransitions();
        
        positionUpdates.forEach(update => {
            this.updateEntityPositionImmediate(update.entityId, update.position);
        });
        
        // Re-enable transitions
        this.enableTransitions();
        
        // Update spatial index in batch
        this.spatialIndex.batchUpdate(positionUpdates);
        
        const endTime = performance.now();
        console.log(`Bulk position update: ${positionUpdates.length} entities in ${(endTime - startTime).toFixed(2)}ms`);
    }
    
    disableTransitions() {
        const style = document.createElement('style');
        style.id = 'disable-entity-transitions';
        style.textContent = '.entity-svg, .entity-path { transition: none !important; }';
        document.head.appendChild(style);
    }
    
    enableTransitions() {
        const style = document.getElementById('disable-entity-transitions');
        if (style) {
            style.remove();
        }
    }
}
```

### Spatial Indexing for Performance

#### Efficient Spatial Data Structure
```javascript
// Simple spatial index for entity queries
class SpatialIndex {
    constructor(cellSize = 100) {
        this.cellSize = cellSize;
        this.cells = new Map();
        this.entityLocations = new Map();
    }
    
    insert(entity) {
        const cellKey = this.getCellKey(entity.x, entity.y);
        
        if (!this.cells.has(cellKey)) {
            this.cells.set(cellKey, new Set());
        }
        
        this.cells.get(cellKey).add(entity.id);
        this.entityLocations.set(entity.id, { cellKey, ...entity });
    }
    
    update(entityId, newPosition) {
        const oldLocation = this.entityLocations.get(entityId);
        
        if (oldLocation) {
            // Remove from old cell
            const oldCell = this.cells.get(oldLocation.cellKey);
            if (oldCell) {
                oldCell.delete(entityId);
                if (oldCell.size === 0) {
                    this.cells.delete(oldLocation.cellKey);
                }
            }
        }
        
        // Add to new cell
        const newCellKey = this.getCellKey(newPosition.x, newPosition.y);
        if (!this.cells.has(newCellKey)) {
            this.cells.set(newCellKey, new Set());
        }
        
        this.cells.get(newCellKey).add(entityId);
        this.entityLocations.set(entityId, { cellKey: newCellKey, ...newPosition });
    }
    
    query(x, y, width, height) {
        const entities = new Set();
        
        const minCellX = Math.floor(x / this.cellSize);
        const maxCellX = Math.floor((x + width) / this.cellSize);
        const minCellY = Math.floor(y / this.cellSize);
        const maxCellY = Math.floor((y + height) / this.cellSize);
        
        for (let cellX = minCellX; cellX <= maxCellX; cellX++) {
            for (let cellY = minCellY; cellY <= maxCellY; cellY++) {
                const cellKey = `${cellX},${cellY}`;
                const cell = this.cells.get(cellKey);
                
                if (cell) {
                    cell.forEach(entityId => entities.add(entityId));
                }
            }
        }
        
        return Array.from(entities);
    }
    
    queryNearest(x, y, maxDistance, limit = 10) {
        const candidates = [];
        const searchRadius = Math.ceil(maxDistance / this.cellSize);
        
        const centerCellX = Math.floor(x / this.cellSize);
        const centerCellY = Math.floor(y / this.cellSize);
        
        // Search in expanding squares
        for (let radius = 0; radius <= searchRadius; radius++) {
            for (let dx = -radius; dx <= radius; dx++) {
                for (let dy = -radius; dy <= radius; dy++) {
                    if (Math.abs(dx) === radius || Math.abs(dy) === radius) {
                        const cellKey = `${centerCellX + dx},${centerCellY + dy}`;
                        const cell = this.cells.get(cellKey);
                        
                        if (cell) {
                            cell.forEach(entityId => {
                                const entity = this.entityLocations.get(entityId);
                                if (entity) {
                                    const distance = Math.sqrt(
                                        Math.pow(entity.x - x, 2) + Math.pow(entity.y - y, 2)
                                    );
                                    
                                    if (distance <= maxDistance) {
                                        candidates.push({ entityId, distance });
                                    }
                                }
                            });
                        }
                    }
                }
            }
            
            // Early exit if we have enough candidates
            if (candidates.length >= limit * 2) {
                break;
            }
        }
        
        // Sort by distance and return top results
        return candidates
            .sort((a, b) => a.distance - b.distance)
            .slice(0, limit)
            .map(c => c.entityId);
    }
    
    getCellKey(x, y) {
        const cellX = Math.floor(x / this.cellSize);
        const cellY = Math.floor(y / this.cellSize);
        return `${cellX},${cellY}`;
    }
    
    clear() {
        this.cells.clear();
        this.entityLocations.clear();
    }
    
    batchUpdate(updates) {
        // Disable individual updates during batch
        const oldUpdate = this.update;
        this.update = () => {}; // No-op during batch
        
        updates.forEach(update => {
            oldUpdate.call(this, update.entityId, update.position);
        });
        
        // Restore update function
        this.update = oldUpdate;
    }
}
```

### Interaction Performance Optimization

#### Optimized Event Handling
```javascript
// High-performance SVG interaction handling
class PerformantInteractionHandler extends SvgInteractionHandler {
    constructor(svgElement, options = {}) {
        super(svgElement, options);
        this.eventThrottle = options.eventThrottle || 10; // 100fps max
        this.lastEventTime = 0;
        this.eventCache = new Map();
        this.spatialIndex = new SpatialIndex();
    }
    
    handleClick(event) {
        // Throttle click events to prevent spam
        const now = performance.now();
        if (now - this.lastEventTime < this.eventThrottle) {
            return;
        }
        this.lastEventTime = now;
        
        const svgPoint = this.coordinateTransform.screenToSvg({
            x: event.clientX,
            y: event.clientY
        });
        
        // Use spatial index for faster entity lookup
        const nearbyEntities = this.spatialIndex.queryNearest(
            svgPoint.x, svgPoint.y, 50, 5
        );
        
        let clickedElement = null;
        for (const entityId of nearbyEntities) {
            const element = document.querySelector(`[data-entity-id="${entityId}"]`);
            if (element && this.isPointInsideEntity(svgPoint, element)) {
                clickedElement = element;
                break;
            }
        }
        
        if (clickedElement) {
            this.onEntityClick(clickedElement, svgPoint, event);
        } else {
            this.onBackgroundClick(svgPoint, event);
        }
    }
    
    isPointInsideEntity(point, element) {
        // Use cached bounding boxes when possible
        const cacheKey = element.getAttribute('data-entity-id');
        let bbox = this.eventCache.get(`bbox_${cacheKey}`);
        
        if (!bbox) {
            bbox = element.getBBox();
            this.eventCache.set(`bbox_${cacheKey}`, bbox);
            
            // Cache cleanup
            if (this.eventCache.size > 200) {
                const firstKey = this.eventCache.keys().next().value;
                this.eventCache.delete(firstKey);
            }
        }
        
        return point.x >= bbox.x && 
               point.x <= bbox.x + bbox.width &&
               point.y >= bbox.y && 
               point.y <= bbox.y + bbox.height;
    }
    
    // Optimized mouse move handling
    handleMouseMove(event) {
        if (!this.isInteracting) return;
        
        // Use requestAnimationFrame to throttle mouse move events
        if (this.mouseMoveFrame) {
            cancelAnimationFrame(this.mouseMoveFrame);
        }
        
        this.mouseMoveFrame = requestAnimationFrame(() => {
            this.processMouseMove(event);
        });
    }
    
    processMouseMove(event) {
        const svgPoint = this.coordinateTransform.screenToSvg({
            x: event.clientX,
            y: event.clientY
        });
        
        // Only process if movement is significant
        if (this.lastInteractionPoint) {
            const dx = svgPoint.x - this.lastInteractionPoint.x;
            const dy = svgPoint.y - this.lastInteractionPoint.y;
            const distance = Math.sqrt(dx * dx + dy * dy);
            
            if (distance < 1) { // Less than 1 SVG unit
                return; // Skip insignificant movements
            }
        }
        
        this.lastInteractionPoint = svgPoint;
        this.emitMouseMoveEvent(svgPoint, event);
    }
    
    emitMouseMoveEvent(svgPoint, originalEvent) {
        this.svgElement.dispatchEvent(new CustomEvent('svgMouseMove', {
            detail: {
                svgCoordinates: svgPoint,
                screenCoordinates: { 
                    x: originalEvent.clientX, 
                    y: originalEvent.clientY 
                }
            }
        }));
    }
}
```

### Memory and Resource Management

#### Resource Pool for Coordinate Operations
```javascript
// Efficient resource management for coordinate operations
class CoordinateResourcePool {
    constructor() {
        this.svgPointPool = [];
        this.matrixPool = [];
        this.transformPool = [];
        this.maxPoolSize = 100;
    }
    
    // Object pooling for SVG points
    acquireSVGPoint() {
        if (this.svgPointPool.length > 0) {
            return this.svgPointPool.pop();
        }
        
        // Create new if pool is empty
        const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        return svg.createSVGPoint();
    }
    
    releaseSVGPoint(point) {
        if (this.svgPointPool.length < this.maxPoolSize) {
            // Reset point
            point.x = 0;
            point.y = 0;
            this.svgPointPool.push(point);
        }
    }
    
    // Batch coordinate conversion using pooled objects
    batchConvertCoordinates(coordinates, converter) {
        const results = [];
        const points = coordinates.map(() => this.acquireSVGPoint());
        
        try {
            // Use pooled points for conversion
            coordinates.forEach((coord, index) => {
                const point = points[index];
                point.x = coord.x;
                point.y = coord.y;
                
                const result = converter(point);
                results.push({ x: result.x, y: result.y });
            });
        } finally {
            // Always return points to pool
            points.forEach(point => this.releaseSVGPoint(point));
        }
        
        return results;
    }
    
    // Memory cleanup
    cleanup() {
        this.svgPointPool.length = 0;
        this.matrixPool.length = 0;
        this.transformPool.length = 0;
    }
}
```

### Performance Monitoring and Analytics

#### Coordinate Performance Profiler
```javascript
// Performance monitoring for coordinate operations
class CoordinatePerformanceProfiler {
    constructor() {
        this.metrics = {
            transformations: [],
            entityUpdates: [],
            viewportChanges: [],
            interactions: []
        };
        this.isEnabled = false;
    }
    
    enable() {
        this.isEnabled = true;
        this.startTime = performance.now();
    }
    
    disable() {
        this.isEnabled = false;
    }
    
    profileTransformation(operation, duration) {
        if (!this.isEnabled) return;
        
        this.metrics.transformations.push({
            operation,
            duration,
            timestamp: performance.now() - this.startTime
        });
        
        // Keep metrics size manageable
        if (this.metrics.transformations.length > 1000) {
            this.metrics.transformations.splice(0, 100);
        }
    }
    
    profileEntityUpdate(entityCount, duration) {
        if (!this.isEnabled) return;
        
        this.metrics.entityUpdates.push({
            entityCount,
            duration,
            timestamp: performance.now() - this.startTime
        });
    }
    
    profileInteraction(type, duration) {
        if (!this.isEnabled) return;
        
        this.metrics.interactions.push({
            type,
            duration,
            timestamp: performance.now() - this.startTime
        });
    }
    
    generateReport() {
        const report = {
            transformations: this.analyzeTransformations(),
            entityUpdates: this.analyzeEntityUpdates(),
            interactions: this.analyzeInteractions(),
            recommendations: this.generateRecommendations()
        };
        
        console.table(report.transformations);
        console.table(report.entityUpdates);
        console.log('Performance Recommendations:', report.recommendations);
        
        return report;
    }
    
    analyzeTransformations() {
        if (this.metrics.transformations.length === 0) return {};
        
        const durations = this.metrics.transformations.map(t => t.duration);
        const operations = {};
        
        this.metrics.transformations.forEach(t => {
            if (!operations[t.operation]) {
                operations[t.operation] = [];
            }
            operations[t.operation].push(t.duration);
        });
        
        return Object.entries(operations).map(([op, durations]) => ({
            operation: op,
            count: durations.length,
            average: (durations.reduce((a, b) => a + b, 0) / durations.length).toFixed(2),
            max: Math.max(...durations).toFixed(2),
            min: Math.min(...durations).toFixed(2)
        }));
    }
    
    analyzeEntityUpdates() {
        if (this.metrics.entityUpdates.length === 0) return {};
        
        const updates = this.metrics.entityUpdates;
        const avgEntitiesPerUpdate = updates.reduce((sum, u) => sum + u.entityCount, 0) / updates.length;
        const avgDuration = updates.reduce((sum, u) => sum + u.duration, 0) / updates.length;
        
        return {
            totalUpdates: updates.length,
            avgEntitiesPerUpdate: avgEntitiesPerUpdate.toFixed(1),
            avgDuration: avgDuration.toFixed(2),
            entitiesPerSecond: (avgEntitiesPerUpdate / (avgDuration / 1000)).toFixed(0)
        };
    }
    
    analyzeInteractions() {
        const interactions = {};
        
        this.metrics.interactions.forEach(i => {
            if (!interactions[i.type]) {
                interactions[i.type] = [];
            }
            interactions[i.type].push(i.duration);
        });
        
        return Object.entries(interactions).map(([type, durations]) => ({
            type,
            count: durations.length,
            average: (durations.reduce((a, b) => a + b, 0) / durations.length).toFixed(2)
        }));
    }
    
    generateRecommendations() {
        const recommendations = [];
        
        // Analyze transformation performance
        const transformData = this.analyzeTransformations();
        if (Array.isArray(transformData)) {
            const slowTransforms = transformData.filter(t => parseFloat(t.average) > 5);
            if (slowTransforms.length > 0) {
                recommendations.push('Consider caching or optimizing slow transformation operations');
            }
        }
        
        // Analyze entity update performance
        const entityData = this.analyzeEntityUpdates();
        if (entityData.entitiesPerSecond && parseInt(entityData.entitiesPerSecond) < 1000) {
            recommendations.push('Entity update performance is below optimal (< 1000 entities/sec)');
        }
        
        return recommendations;
    }
}
```

## Overview

This document covers the frontend-specific SVG coordinate operations used in location-based entity displays. These operations handle the conversion between different coordinate systems and the visual positioning of entities within SVG-based floor plans.

## Coordinate System Types

### SVG Document Coordinates
- **Origin**: Top-left corner of the SVG viewBox
- **Units**: SVG units (typically corresponding to real-world measurements)
- **Usage**: Entity positioning data stored in EntityPosition and EntityPath models

### Screen/Canvas Coordinates  
- **Origin**: Top-left corner of the rendered SVG element
- **Units**: CSS pixels
- **Usage**: Mouse interactions, click detection, dynamic positioning

### Viewport Coordinates
- **Origin**: Top-left corner of the visible viewport area
- **Units**: CSS pixels  
- **Usage**: Scroll position, panning operations

## Frontend SVG Operations

### Screen Position Calculation

Convert SVG coordinates to screen position for interactions:

```python
class SvgCoordinateTransform:
    def calculate_entity_position(self, svg_coords, viewbox, canvas_size):
        """Convert SVG coordinates to screen position"""
        # Extract viewbox parameters
        vb_x, vb_y, vb_width, vb_height = self.parse_viewbox(viewbox)
        canvas_width, canvas_height = canvas_size
        
        # Calculate scale factors
        scale_x = canvas_width / vb_width
        scale_y = canvas_height / vb_height
        
        # Transform SVG coordinates to screen coordinates
        screen_x = (svg_coords.x - vb_x) * scale_x
        screen_y = (svg_coords.y - vb_y) * scale_y
        
        return ScreenPosition(screen_x, screen_y)
    
    def parse_viewbox(self, viewbox_string):
        """Parse SVG viewBox string into components"""
        parts = viewbox_string.split()
        return float(parts[0]), float(parts[1]), float(parts[2]), float(parts[3])
```

### Interactive Coordinate Conversion

Handle mouse events and convert to SVG coordinates:

```javascript
class SvgInteractionHandler {
    constructor(svgElement) {
        this.svgElement = svgElement;
    }
    
    screenToSvgCoordinates(screenX, screenY) {
        // Get SVG bounding rectangle
        const rect = this.svgElement.getBoundingClientRect();
        
        // Convert screen coordinates to SVG viewport coordinates
        const svgPoint = this.svgElement.createSVGPoint();
        svgPoint.x = screenX - rect.left;
        svgPoint.y = screenY - rect.top;
        
        // Transform through CTM (Current Transformation Matrix)
        const ctm = this.svgElement.getScreenCTM().inverse();
        const svgCoords = svgPoint.matrixTransform(ctm);
        
        return {
            x: svgCoords.x,
            y: svgCoords.y
        };
    }
    
    handleEntityClick(event, entityId) {
        const svgCoords = this.screenToSvgCoordinates(event.clientX, event.clientY);
        
        // Process entity interaction at SVG coordinates
        this.processEntityInteraction(entityId, svgCoords);
    }
}
```

### Zoom and Pan Operations

Handle viewport transformations for navigation:

```javascript
class SvgViewportController {
    constructor(svgElement) {
        this.svgElement = svgElement;
        this.currentZoom = 1.0;
        this.currentPan = { x: 0, y: 0 };
    }
    
    zoomToFit(entities) {
        // Calculate bounding box of all entities
        const bbox = this.calculateEntityBoundingBox(entities);
        
        // Add padding
        const padding = 20;
        const paddedBounds = {
            x: bbox.x - padding,
            y: bbox.y - padding,
            width: bbox.width + (padding * 2),
            height: bbox.height + (padding * 2)
        };
        
        // Update viewBox to fit entities
        const viewBox = `${paddedBounds.x} ${paddedBounds.y} ${paddedBounds.width} ${paddedBounds.height}`;
        this.svgElement.setAttribute('viewBox', viewBox);
    }
    
    zoomIn(factor = 1.2) {
        this.currentZoom *= factor;
        this.applyTransform();
    }
    
    zoomOut(factor = 0.8) {
        this.currentZoom *= factor;
        this.applyTransform();
    }
    
    pan(deltaX, deltaY) {
        this.currentPan.x += deltaX / this.currentZoom;
        this.currentPan.y += deltaY / this.currentZoom;
        this.applyTransform();
    }
    
    applyTransform() {
        const transform = `translate(${this.currentPan.x}, ${this.currentPan.y}) scale(${this.currentZoom})`;
        const mainGroup = this.svgElement.querySelector('#main-group');
        if (mainGroup) {
            mainGroup.setAttribute('transform', transform);
        }
    }
}
```

### Entity Positioning and Scaling

Handle dynamic entity positioning based on viewport:

```javascript
class EntityPositionManager {
    updateEntityPosition(entityElement, position, viewportScale) {
        // Calculate scaled position
        const scaledX = position.x * viewportScale;
        const scaledY = position.y * viewportScale;
        const scaledSize = position.scale * viewportScale;
        
        // Apply transform to entity element
        const transform = `translate(${scaledX}, ${scaledY}) scale(${scaledSize}) rotate(${position.rotation})`;
        entityElement.setAttribute('transform', transform);
    }
    
    updateEntityPath(pathElement, pathData, viewportTransform) {
        // Apply viewport transformation to path data
        const transformedPath = this.transformSvgPath(pathData, viewportTransform);
        pathElement.setAttribute('d', transformedPath);
    }
    
    transformSvgPath(pathData, transform) {
        // Parse and transform SVG path data
        // This is a simplified example - real implementation would use SVG path parsing library
        return pathData; // Placeholder for actual path transformation
    }
}
```

## Template Integration

### SVG Viewport Setup

```django
<!-- Location view SVG setup -->
<svg id="location-svg" 
     class="location-display"
     viewBox="{{ location_view.get_viewbox }}"
     preserveAspectRatio="xMidYMid meet">
     
  <!-- Main transform group for zoom/pan -->
  <g id="main-group">
    
    <!-- Background layer -->
    <g class="background-layer">
      {% if location.floor_plan_svg %}
        {% include location.floor_plan_svg %}
      {% endif %}
    </g>
    
    <!-- Entity layer -->
    <g class="entity-layer">
      {% for entity in entities %}
        {% if entity.has_position %}
          <g class="entity-group" 
             data-entity-id="{{ entity.id }}"
             transform="translate({{ entity.position.x }}, {{ entity.position.y }}) 
                        scale({{ entity.position.scale }}) 
                        rotate({{ entity.position.rotation }})">
            {% include entity.get_visual_template %}
          </g>
        {% elif entity.has_path %}
          <path class="entity-path" 
                data-entity-id="{{ entity.id }}"
                d="{{ entity.path.svg_path }}"
                style="{{ entity.get_path_styling }}"/>
        {% endif %}
      {% endfor %}
    </g>
    
  </g>
</svg>
```

### JavaScript Integration

```javascript
// Initialize SVG coordinate handling
document.addEventListener('DOMContentLoaded', function() {
    const locationSvg = document.getElementById('location-svg');
    
    if (locationSvg) {
        // Initialize interaction handler
        const interactionHandler = new SvgInteractionHandler(locationSvg);
        
        // Initialize viewport controller
        const viewportController = new SvgViewportController(locationSvg);
        
        // Initialize entity position manager
        const positionManager = new EntityPositionManager();
        
        // Set up event listeners
        locationSvg.addEventListener('click', function(event) {
            const entityElement = event.target.closest('[data-entity-id]');
            if (entityElement) {
                const entityId = entityElement.getAttribute('data-entity-id');
                interactionHandler.handleEntityClick(event, entityId);
            }
        });
        
        // Set up zoom controls
        document.getElementById('zoom-in').addEventListener('click', () => {
            viewportController.zoomIn();
        });
        
        document.getElementById('zoom-out').addEventListener('click', () => {
            viewportController.zoomOut();
        });
        
        // Set up pan controls (mouse drag)
        let isPanning = false;
        let lastPanPoint = null;
        
        locationSvg.addEventListener('mousedown', function(event) {
            if (event.button === 1 || (event.button === 0 && event.ctrlKey)) { // Middle mouse or Ctrl+click
                isPanning = true;
                lastPanPoint = { x: event.clientX, y: event.clientY };
                event.preventDefault();
            }
        });
        
        document.addEventListener('mousemove', function(event) {
            if (isPanning && lastPanPoint) {
                const deltaX = event.clientX - lastPanPoint.x;
                const deltaY = event.clientY - lastPanPoint.y;
                viewportController.pan(deltaX, deltaY);
                lastPanPoint = { x: event.clientX, y: event.clientY };
            }
        });
        
        document.addEventListener('mouseup', function() {
            isPanning = false;
            lastPanPoint = null;
        });
    }
});
```

## Performance Considerations

### Efficient Coordinate Calculations

```javascript
// Cache frequently used calculations
class CoordinateCache {
    constructor() {
        this.transformCache = new Map();
        this.boundingBoxCache = new Map();
    }
    
    getCachedTransform(viewBox, canvasSize) {
        const key = `${viewBox}_${canvasSize.width}x${canvasSize.height}`;
        
        if (!this.transformCache.has(key)) {
            const transform = this.calculateTransform(viewBox, canvasSize);
            this.transformCache.set(key, transform);
        }
        
        return this.transformCache.get(key);
    }
    
    clearCache() {
        this.transformCache.clear();
        this.boundingBoxCache.clear();
    }
}
```

### Optimize Frequent Updates

```javascript
// Use requestAnimationFrame for smooth updates
class SmoothPositionUpdater {
    constructor() {
        this.pendingUpdates = new Map();
        this.isUpdateScheduled = false;
    }
    
    scheduleUpdate(entityId, newPosition) {
        this.pendingUpdates.set(entityId, newPosition);
        
        if (!this.isUpdateScheduled) {
            this.isUpdateScheduled = true;
            requestAnimationFrame(() => this.processPendingUpdates());
        }
    }
    
    processPendingUpdates() {
        this.pendingUpdates.forEach((position, entityId) => {
            const element = document.querySelector(`[data-entity-id="${entityId}"]`);
            if (element) {
                this.applyPositionUpdate(element, position);
            }
        });
        
        this.pendingUpdates.clear();
        this.isUpdateScheduled = false;
    }
}
```

## Troubleshooting

### Click Detection Not Working

**Symptoms**: Mouse clicks on entities don't trigger expected actions
**Diagnostic Steps**:

1. **Verify Event Listener Setup**
   ```javascript
   // Check if click handler is attached
   const svg = document.getElementById('location-svg');
   console.log('Click listeners:', getEventListeners(svg));
   
   // Test manual click
   svg.addEventListener('click', (e) => {
       console.log('Click at:', e.clientX, e.clientY);
   });
   ```

2. **Check Coordinate Conversion**
   ```javascript
   // Test coordinate transformation
   const handler = new SvgInteractionHandler(svg);
   const svgCoords = handler.screenToSvgCoordinates(event.clientX, event.clientY);
   console.log('SVG coordinates:', svgCoords);
   ```

3. **Verify Element Structure**
   ```html
   <!-- Entity must have data-entity-id and be in correct layer -->
   <g class="entity-layer">
     <g data-entity-id="123" class="entity-group">
       <!-- Clickable content -->
     </g>
   </g>
   ```

**Common Fixes**:
- **Missing data-entity-id**: Add attribute to entity elements
- **Event bubbling issues**: Use `event.target.closest('[data-entity-id]')`
- **Coordinate transformation error**: Check SVG viewBox and CTM calculation
- **Z-index/layering**: Ensure entities are in front of background elements

### Entity Positions Incorrect

**Symptoms**: Entities appear in wrong locations after coordinate transformations
**Root Causes & Solutions**:

1. **ViewBox Parsing Issues**
   ```javascript
   // Debug viewBox parsing
   const viewBox = svg.getAttribute('viewBox');
   console.log('ViewBox:', viewBox);
   
   const [x, y, width, height] = viewBox.split(' ').map(Number);
   console.log('Parsed:', { x, y, width, height });
   ```

2. **Scale Factor Calculation**
   ```javascript
   // Verify scale factors
   const rect = svg.getBoundingClientRect();
   const viewBoxWidth = parseFloat(svg.viewBox.baseVal.width);
   const scaleX = rect.width / viewBoxWidth;
   console.log('Scale factor:', scaleX);
   ```

3. **Transform Matrix Issues**
   ```javascript
   // Check current transformation matrix
   const ctm = svg.getScreenCTM();
   console.log('CTM:', ctm);
   console.log('Transform values:', {
       a: ctm.a, b: ctm.b, c: ctm.c, 
       d: ctm.d, e: ctm.e, f: ctm.f
   });
   ```

**Solutions**:
- **Invalid viewBox**: Ensure viewBox attribute has 4 numeric values
- **Missing CTM**: Check if SVG element has proper screen CTM
- **Nested transforms**: Account for parent group transformations
- **Dynamic sizing**: Recalculate on window resize

### Zoom and Pan Not Working

**Symptoms**: Viewport controls don't respond or behave erratically
**Troubleshooting Approach**:

1. **Check Controller Initialization**
   ```javascript
   // Verify controller is properly initialized
   console.log('Viewport controller:', window.viewportController);
   
   // Test basic operations
   if (viewportController) {
       viewportController.zoomIn();
       console.log('Current zoom:', viewportController.currentZoom);
   }
   ```

2. **Verify Transform Application**
   ```javascript
   // Check if transforms are being applied
   const mainGroup = svg.querySelector('#main-group');
   console.log('Main group transform:', mainGroup.getAttribute('transform'));
   ```

3. **Event Handler Issues**
   ```javascript
   // Test zoom button events
   document.getElementById('zoom-in').addEventListener('click', () => {
       console.log('Zoom in clicked');
       viewportController.zoomIn();
   });
   ```

**Common Fixes**:
- **Missing main group**: Ensure SVG has `#main-group` element
- **Event conflicts**: Check for competing mouse event handlers
- **Transform syntax**: Verify proper transform string formatting
- **Boundary limits**: Implement zoom/pan limits to prevent excessive values

### Performance Issues with Many Entities

**Symptoms**: Slow coordinate calculations, laggy interactions with large datasets
**Optimization Strategies**:

1. **Coordinate Caching**
   ```javascript
   // Implement coordinate result caching
   class CoordinateCache {
       constructor(maxSize = 1000) {
           this.cache = new Map();
           this.maxSize = maxSize;
       }
       
       get(key) {
           const result = this.cache.get(key);
           if (result) {
               // Move to end (LRU)
               this.cache.delete(key);
               this.cache.set(key, result);
           }
           return result;
       }
   }
   ```

2. **Batch Operations**
   ```javascript
   // Process coordinate updates in batches
   requestAnimationFrame(() => {
       const updates = this.pendingCoordinateUpdates;
       updates.forEach(update => {
           this.applyCoordinateUpdate(update);
       });
       this.pendingCoordinateUpdates.clear();
   });
   ```

3. **Viewport Culling**
   ```javascript
   // Only process entities in visible viewport
   function isEntityVisible(entityCoords, viewportBounds) {
       return entityCoords.x >= viewportBounds.left &&
              entityCoords.x <= viewportBounds.right &&
              entityCoords.y >= viewportBounds.top &&
              entityCoords.y <= viewportBounds.bottom;
   }
   ```

### SVG Viewbox and Scaling Issues

**Symptoms**: Inconsistent scaling, elements clipped or positioned wrong
**Diagnostic Steps**:

1. **Check ViewBox vs Canvas Size**
   ```javascript
   // Compare logical vs physical dimensions
   const viewBox = svg.viewBox.baseVal;
   const rect = svg.getBoundingClientRect();
   
   console.log('ViewBox:', viewBox.width, 'x', viewBox.height);
   console.log('Canvas:', rect.width, 'x', rect.height);
   console.log('Aspect ratios:', 
       viewBox.width/viewBox.height, 
       rect.width/rect.height);
   ```

2. **Verify preserveAspectRatio**
   ```html
   <!-- Check preserveAspectRatio setting -->
   <svg viewBox="0 0 1000 800" 
        preserveAspectRatio="xMidYMid meet"  <!-- or "none" for stretching -->
        ...>
   ```

3. **Test Scale Consistency**
   ```javascript
   // Verify consistent scaling in both dimensions
   function testScaling() {
       const point1 = { x: 0, y: 0 };
       const point2 = { x: 100, y: 100 };
       
       const screen1 = svgToScreen(point1);
       const screen2 = svgToScreen(point2);
       
       const scaleX = (screen2.x - screen1.x) / (point2.x - point1.x);
       const scaleY = (screen2.y - screen1.y) / (point2.y - point1.y);
       
       console.log('Scale factors:', { scaleX, scaleY });
   }
   ```

### Browser Compatibility Problems

**Symptoms**: Coordinate operations work in some browsers but not others
**Common Issues & Solutions**:

1. **SVG DOM API Support**
   ```javascript
   // Check for required APIs
   if (!SVGElement.prototype.getScreenCTM) {
       console.error('Browser lacks SVG getScreenCTM support');
       // Implement fallback or show warning
   }
   
   if (!SVGSVGElement.prototype.createSVGPoint) {
       console.error('Browser lacks createSVGPoint support');
       // Use alternative coordinate conversion
   }
   ```

2. **Transform Matrix Differences**
   ```javascript
   // Handle browser differences in matrix calculations
   function getScreenCTMSafe(element) {
       try {
           return element.getScreenCTM();
       } catch (e) {
           console.warn('getScreenCTM failed, using fallback');
           return element.getCTM();
       }
   }
   ```

3. **Event Coordinate Differences**
   ```javascript
   // Normalize event coordinates across browsers
   function getNormalizedCoordinates(event) {
       return {
           clientX: event.clientX || event.pageX,
           clientY: event.clientY || event.pageY
       };
   }
   ```

### Touch and Mobile Issues

**Symptoms**: Coordinate operations fail on touch devices
**Mobile-Specific Solutions**:

1. **Touch Event Handling**
   ```javascript
   // Handle touch events for mobile devices
   svg.addEventListener('touchstart', (e) => {
       e.preventDefault(); // Prevent default touch behaviors
       const touch = e.touches[0];
       handleInteraction(touch.clientX, touch.clientY);
   });
   ```

2. **Viewport Meta Tag**
   ```html
   <!-- Ensure proper mobile viewport handling -->
   <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
   ```

3. **High DPI Display Issues**
   ```javascript
   // Account for device pixel ratio
   const dpr = window.devicePixelRatio || 1;
   const adjustedCoords = {
       x: screenX * dpr,
       y: screenY * dpr
   };
   ```

## Related Documentation
- Entity visual configuration: [Entity Visual Configuration](entity-visual-configuration.md)
- Entity status display: [Entity Status Display](entity-status-display.md) 
- Style guidelines: [Style Guidelines](style-guidelines.md)
- Domain geometric operations: [Domain Guidelines](../domain/domain-guidelines.md#complex-calculations)
- Frontend guidelines: [Frontend Guidelines](frontend-guidelines.md)