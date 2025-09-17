# Entity Visual Configuration

## Overview

This document covers the frontend configuration required to set up visual representations for entity types. It includes icon configuration, path styling, viewbox management, and visual asset creation.

### Key Configuration Files
- **Icons**: `hi/apps/entity/templates/entity/svg/type.{TYPE}.svg`
- **Registration**: `hi.hi_styles.EntityStyle.EntityTypesWithIcons`
- **Path Types**: `hi.hi_styles.EntityStyle.EntityTypeClosedPaths/EntityTypeOpenPaths`
- **Styling**: `hi.hi_styles.EntityStyle.PathEntityTypeToSvgStatusStyle`

## Entity Display Methods

Entities can be visually represented through two primary methods:

### Icon-Based Representation
- **EntityPosition**: Icon-based representation with position, scale, rotation
- **Use Case**: Point entities like sensors, devices, controls
- **Visual**: SVG icons with positioning and scaling

### Path-Based Representation  
- **EntityPath**: SVG path representation for areas or complex shapes
- **Use Case**: Areas, zones, complex geometric shapes
- **Visual**: SVG paths with fill, stroke, and styling

## Adding Visual Support for New Entity Types

When adding visual support for a new entity type, follow these configuration steps:

### 1. Choose Visual Display Method

Determine whether the entity should be displayed as an icon or a path based on its nature:
- **Icons**: Point-like entities (sensors, switches, cameras)
- **Paths**: Area-like entities (rooms, zones, boundaries)

### 2. Icon-Based Entity Configuration

#### Create SVG Icon Asset

Create an SVG icon for the new entity type in:
```
hi/apps/entity/templates/entity/svg/type.${TYPE}.svg
```
The `${TYPE}` must match the enum name in lowercase.

**SVG Icon Requirements:**
```svg
<!-- Example: type.motion_sensor.svg -->
<rect class="hi-entity-bg" x="0" y="0" width="64" height="64" fill="none"/>
<circle cx="32" cy="32" r="20" fill="currentColor"/>
<path d="M20,32 L32,20 L44,32 L32,44 Z" fill="white" opacity="0.8"/>
```

**Key Requirements:**
1. **Clickable Background**: Always include a rectangle covering the entire viewbox:
   ```svg
   <rect class="hi-entity-bg" x="0" y="0" width="64" height="64" fill="none"/>
   ```
   This ensures the entire icon area is clickable for user interactions.

2. **No Wrapping SVG Element**: File should contain only drawing commands, no `<svg>` wrapper

3. **Standard Viewbox**: Default viewbox is `0 0 64 64` unless custom viewbox is registered

#### Register Icon Configuration

Add the new entity type to the icon registry:
```python
# hi.hi_styles.EntityStyle.EntityTypesWithIcons
EntityTypesWithIcons = {
    EntityType.MOTION_SENSOR,
    EntityType.DOOR_SENSOR,
    EntityType.YOUR_NEW_TYPE,  # Add here
    # ... existing types
}
```

#### Custom Viewbox Configuration (Optional)

If your icon requires a different viewbox than the default `0 0 64 64`, register it:
```python
# hi.hi_styles.EntityStyle.EntityTypeToIconViewbox
EntityTypeToIconViewbox = {
    EntityType.YOUR_NEW_TYPE: "0 0 100 50",  # Custom viewbox
    # ... existing custom viewboxes
}
```

### 3. Path-Based Entity Configuration

#### Choose Path Type

Determine whether the entity represents a closed or open path:

**Closed Paths** (filled areas):
```python
# hi.hi_styles.EntityStyle.EntityTypeClosedPaths
EntityTypeClosedPaths = {
    EntityType.ROOM,
    EntityType.ZONE,
    EntityType.YOUR_NEW_AREA_TYPE,  # Add here
}
```

**Open Paths** (lines/curves):
```python
# hi.hi_styles.EntityStyle.EntityTypeOpenPaths  
EntityTypeOpenPaths = {
    EntityType.CORRIDOR,
    EntityType.BOUNDARY_LINE,
    EntityType.YOUR_NEW_LINE_TYPE,  # Add here
}
```

#### Define Visual Style

Create or reference a visual style for the path entity:
```python
# hi.hi_styles.EntityStyle.PathEntityTypeToSvgStatusStyle
PathEntityTypeToSvgStatusStyle = {
    EntityType.YOUR_NEW_TYPE: YourCustomSvgStatusStyle,
    # Reference existing style or create new one
}
```

#### Create Custom SVG Status Style (If Needed)

If no existing style fits your entity type, create a new style class:
```python
# In hi.hi_styles.EntityStyle
class YourCustomSvgStatusStyle:
    """SVG styling for your custom entity type"""
    
    # Default styling
    default_fill = "#E0E0E0"
    default_stroke = "#808080"
    default_stroke_width = "2"
    
    # State-based styling
    active_fill = "#FF4444"
    active_stroke = "#CC0000"
    
    recent_fill = "#FF8844"
    recent_stroke = "#CC4400"
    
    past_fill = "#FFCC44"
    past_stroke = "#CC8800"
    
    idle_fill = "#44FF44"
    idle_stroke = "#00CC00"
```

#### Default Path Sizing (Optional)

Configure default sizing for path entities:
```python
# hi.hi_styles.EntityStyle.EntityTypePathInitialRadius
EntityTypePathInitialRadius = {
    EntityType.YOUR_NEW_TYPE: 25.0,  # Default radius in pixels
    # ... existing size overrides
}
```

## Visual Asset Guidelines

### SVG Icon Design Standards

**Size and Scaling:**
- Design for 64x64 viewbox by default
- Use simple, recognizable shapes
- Ensure visibility at small scales (16px minimum)

**Color Usage:**
- Use `currentColor` for primary elements that should inherit entity state colors
- Use fixed colors sparingly for distinctive details
- Maintain sufficient contrast with background

**Style Consistency:**
- Follow existing icon visual language
- Use similar stroke weights and fill patterns
- Maintain consistent visual metaphors

### Path Styling Standards

**Stroke and Fill:**
- Provide meaningful defaults for idle state
- Ensure status colors are clearly distinguishable
- Consider opacity for layered visual effects

**Visual Hierarchy:**
- Active states should be most prominent
- Use color temperature progression (hot to cool)
- Maintain readability across different backgrounds

## Template Integration

### Icon Entity Template Usage

```django
<!-- Icon entity in location view -->
<g class="entity-group" data-entity-id="{{ entity.id }}">
  <use href="#icon-{{ entity.entity_type.name.lower }}" 
       class="entity-icon {{ entity.get_status_css_classes }}"
       transform="translate({{ entity.position.x }}, {{ entity.position.y }}) 
                  scale({{ entity.position.scale }}) 
                  rotate({{ entity.position.rotation }})" />
</g>
```

### Path Entity Template Usage

```django
<!-- Path entity in location view -->
<g class="entity-group" data-entity-id="{{ entity.id }}">
  <path class="entity-path {{ entity.get_status_css_classes }}"
        d="{{ entity.path.svg_path }}"
        style="{{ entity.get_path_styling }}" />
</g>
```

### Icon Symbol Definitions

Icons must be included in the SVG symbol definitions:
```django
<!-- In base template or location template -->
<defs>
  {% for entity_type in entity_types_with_icons %}
    <symbol id="icon-{{ entity_type.name.lower }}" viewBox="{{ entity_type.get_viewbox }}">
      {% include entity_type.get_icon_template %}
    </symbol>
  {% endfor %}
</defs>
```

## Testing Visual Configuration

### Visual Testing Checklist

When adding new entity visual support:

1. **Icon Visibility**: Verify icon displays correctly at various scales
2. **State Changes**: Test all status states (active, recent, past, idle, unknown)
3. **Color Contrast**: Ensure sufficient contrast in all color schemes
4. **Click Targets**: Verify clickable area covers entire visual element
5. **Template Rendering**: Test in location views, collection views, and status modals
6. **Responsive Scaling**: Test on different screen sizes and zoom levels

### Manual Testing Process

1. Create test entity of new type
2. Position entity in a location
3. Trigger state changes through integration or simulation
4. Verify visual feedback matches expected behavior
5. Test entity in different view contexts

## Simulator Integration (Optional)

If the new entity type should be supported by the simulator:
```python
# hi.simulator.enums.SimEntityType
SimEntityType = Enum('SimEntityType', [
    'MOTION_SENSOR',
    'DOOR_SENSOR', 
    'YOUR_NEW_TYPE',  # Add corresponding simulator type
    # ... existing types
])
```


## Real-World Workflow Examples

### Workflow 1: Adding a New Entity Type with Custom Icon

**Scenario**: Add support for a "Smart Door Lock" entity type with a custom icon and status colors.

**Complete Implementation Process:**

1. **Domain Setup** (Cross-reference: [Entity Patterns](../domain/entity-patterns.md))
   ```python
   # Add to hi.apps.entity.enums.EntityType
   class EntityType(Enum):
       # ... existing types
       SMART_DOOR_LOCK = ("smart_door_lock", "Smart Door Lock")
   
   # Add to appropriate group  
   class EntityGroupType(Enum):
       SECURITY_DEVICES = "security_devices"
       # Add SMART_DOOR_LOCK to this group
   ```

2. **Create Custom SVG Icon** ([Create SVG Icon Asset](#create-svg-icon-asset))

Note: Do **not** use the `<g>` tag inside these SVGs!

   ```xml
   <!-- File: hi/apps/entity/templates/entity/svg/type.smart_door_lock.svg -->
   <rect class="hi-entity-bg" x="0" y="0" width="64" height="64" fill="none"/>
   <!-- Door outline -->
   <rect x="20" y="10" width="24" height="44" fill="none" stroke="currentColor" stroke-width="2"/>
   <!-- Lock mechanism -->
   <circle cx="32" cy="32" r="6" fill="currentColor"/>
   <!-- Key hole -->
   <circle cx="32" cy="32" r="2" fill="white"/>
   <!-- Status indicator (will change color based on state) -->
   <circle cx="45" cy="15" r="4" fill="currentColor" opacity="0.8"/>
   ```

3. **Register Icon Type** ([Register Icon Configuration](#register-icon-configuration))
   ```python
   # In hi.hi_styles.EntityStyle.EntityTypesWithIcons
   EntityTypesWithIcons = {
       EntityType.MOTION_SENSOR,
       EntityType.DOOR_SENSOR,
       EntityType.SMART_DOOR_LOCK,  # Add this line
       # ... existing types
   }
   ```

4. **Define Status-Specific Styling** ([Status Colors](../entity-status-display.md#status-color-system))
   ```css
   /* Add to your CSS file */
   .entity-svg.door-lock-locked {
     fill: var(--status-idle);    /* Green - secure */
     stroke: #006600;
   }
   
   .entity-svg.door-lock-unlocked {
     fill: var(--status-recent);  /* Orange - caution */
     stroke: #cc6600;
   }
   
   .entity-svg.door-lock-jammed {
     fill: var(--status-active);  /* Red - problem */
     stroke: #cc0000;
   }
   
   .entity-svg.door-lock-offline {
     fill: var(--status-unknown); /* Gray - unknown */
     stroke: #666666;
   }
   ```

5. **Test Visual Configuration** ([Testing Visual Configuration](#testing-visual-configuration))
   ```python
   # Create test entity
   test_door_lock = Entity.objects.create(
       name="Front Door Lock",
       entity_type=EntityType.SMART_DOOR_LOCK,
       location=test_location
   )
   
   # Create EntityPosition for icon display
   EntityPosition.objects.create(
       entity=test_door_lock,
       x=100, y=150,
       scale=1.0, rotation=0
   )
   ```

6. **Verify in Location View**
   - Navigate to location view containing the door lock
   - Verify icon displays correctly
   - Test status changes trigger color updates
   - Check click interactions work (clickable background)

**Expected Result**: Smart door lock appears as custom icon with status-based color changes.

---

### Workflow 2: Converting Icon Entity to Path Entity

**Scenario**: Motion sensor needs to represent a coverage area rather than just a point location.

**Migration Process:**

1. **Plan Path Representation** ([Entity Display Methods](#entity-display-methods))
   ```python
   # Motion sensor coverage area as circular path
   # Center: sensor position
   # Radius: detection range
   coverage_radius = 50  # units in SVG coordinates
   center_x, center_y = 200, 300
   ```

2. **Remove from Icon Registry** ([Icon Configuration](#register-icon-configuration))
   ```python
   # Remove from hi.hi_styles.EntityStyle.EntityTypesWithIcons
   EntityTypesWithIcons = {
       # EntityType.MOTION_SENSOR,  # Comment out or remove
       EntityType.DOOR_SENSOR,
       # ... other types
   }
   ```

3. **Add to Path Registry** ([Path-Based Configuration](#path-based-entity-configuration))
   ```python
   # Add to hi.hi_styles.EntityStyle.EntityTypeClosedPaths
   EntityTypeClosedPaths = {
       EntityType.ROOM,
       EntityType.MOTION_SENSOR,  # Add this line
       # ... existing types
   }
   ```

4. **Create SVG Path Data** ([SVG Path Requirements](#path-based-entity-configuration))
   ```python
   import math
   
   def create_circular_path(center_x, center_y, radius):
       """Create SVG path for circular coverage area"""
       # Create circle using path commands (more flexible than <circle>)
       path_data = (
           f"M {center_x - radius} {center_y} "
           f"A {radius} {radius} 0 0 1 {center_x + radius} {center_y} "
           f"A {radius} {radius} 0 0 1 {center_x - radius} {center_y} "
           f"Z"
       )
       return path_data
   
   # Update existing motion sensor entities
   for motion_sensor in Entity.objects.filter(entity_type=EntityType.MOTION_SENSOR):
       # Get current position
       position = motion_sensor.entityposition_set.first()
       if position:
           # Create EntityPath with coverage area
           EntityPath.objects.create(
               entity=motion_sensor,
               svg_path=create_circular_path(position.x, position.y, 50)
           )
           # Remove EntityPosition
           position.delete()
   ```

5. **Define Path Styling** ([Define Visual Style](#define-visual-style))
   ```python
   # Create new style class in hi.hi_styles.EntityStyle
   class MotionSensorPathStyle:
       default_fill = "#E0E0E0"
       default_stroke = "#808080"
       default_opacity = 0.3
       
       active_fill = "#FF4444"
       active_stroke = "#CC0000"
       active_opacity = 0.6
       
       recent_fill = "#FF8844"
       recent_stroke = "#CC4400"
       recent_opacity = 0.5
       
       idle_fill = "#44FF44"
       idle_stroke = "#00CC00"
       idle_opacity = 0.3
   
   # Register the style
   PathEntityTypeToSvgStatusStyle = {
       EntityType.MOTION_SENSOR: MotionSensorPathStyle,
       # ... existing mappings
   }
   ```

6. **Update Templates** (Cross-reference: [Template Integration](#template-integration))
   ```django
   <!-- Motion sensors now render as paths instead of icons -->
   {% for entity in entities %}
     {% if entity.entity_type.name == 'MOTION_SENSOR' %}
       <path class="entity-path {{ entity.get_status_css_classes }}"
             data-entity-id="{{ entity.id }}"
             d="{{ entity.path.svg_path }}"
             style="{{ entity.get_path_styling }}"/>
     {% elif entity.has_position %}
       <!-- Other icon entities -->
       <use href="#icon-{{ entity.entity_type.name.lower }}"/>
     {% endif %}
   {% endfor %}
   ```

**Expected Result**: Motion sensors display as coverage areas that show detection zones rather than point icons.

## Related Documentation
- Entity domain patterns: [Entity Patterns](../domain/entity-patterns.md)
- Status display implementation: [Entity Status Display](entity-status-display.md)
- Style guidelines: [Style Guidelines](style-guidelines.md)
- Icon system: [Icon System](icon-system.md)
- Frontend guidelines: [Frontend Guidelines](frontend-guidelines.md)
