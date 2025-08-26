# Entity Visual Configuration

## Quick Reference

### Common Tasks
- **Add new entity icon** → [Create SVG asset](#create-svg-icon-asset) → Register in `EntityTypesWithIcons`
- **Add new entity path** → [Configure path type](#choose-path-type) → Add to `EntityTypeClosedPaths` or `EntityTypeOpenPaths`
- **Fix icon not showing** → [Check registration](#register-icon-configuration) → Verify enum and icon file match
- **Change entity colors** → [Update style classes](#define-visual-style) → Modify `SvgStatusStyle` properties
- **Test new entity type** → [Visual testing](#testing-visual-configuration) → Create test entity and verify display

### Key Configuration Files
- **Icons**: `hi/apps/entity/templates/entity/svg/type.{TYPE}.svg`
- **Registration**: `hi.hi_styles.EntityStyle.EntityTypesWithIcons`
- **Path Types**: `hi.hi_styles.EntityStyle.EntityTypeClosedPaths/EntityTypeOpenPaths`
- **Styling**: `hi.hi_styles.EntityStyle.PathEntityTypeToSvgStatusStyle`

### Quick Fixes
| Problem | Solution | Location |
|---------|----------|----------|
| Icon not displaying | Check file name matches enum | [Create SVG Asset](#create-svg-icon-asset) |
| Wrong icon size | Verify viewbox registration | [Custom Viewbox](#register-icon-configuration) |
| Path not styling | Check style class assignment | [Define Visual Style](#define-visual-style) |
| Entity not clickable | Add `hi-entity-bg` rectangle | [SVG Icon Requirements](#create-svg-icon-asset) |

### Entity Type Decision Tree
```
New Entity Type
├── Point-like (sensor, device) → Use Icon
│   ├── Create SVG file: type.{enum_name}.svg
│   └── Register in EntityTypesWithIcons
└── Area-like (room, zone) → Use Path
    ├── Closed shape → Add to EntityTypeClosedPaths
    └── Open line → Add to EntityTypeOpenPaths
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

---

### Workflow 3: Troubleshooting Icon Registration Issues

**Scenario**: New entity type icon was created and registered, but still shows as placeholder or missing.

**Systematic Debugging:**

1. **Verify File Path and Naming** ([Troubleshooting - Icon Not Displaying](#entity-icon-not-displaying))
   ```bash
   # Check exact file path and naming
   ls hi/apps/entity/templates/entity/svg/type.smart_door_lock.svg
   
   # Verify enum name matches file name
   # EntityType.SMART_DOOR_LOCK → type.smart_door_lock.svg
   ```

2. **Check Registration** ([Icon Registration](#register-icon-configuration))
   ```python
   # Verify in hi.hi_styles.EntityStyle.EntityTypesWithIcons
   print(EntityType.SMART_DOOR_LOCK in EntityStyle.EntityTypesWithIcons)
   # Should print: True
   ```

3. **Validate SVG Content** ([SVG Icon Requirements](#create-svg-icon-asset))
   ```xml
   <!-- Check file content structure -->
   <!-- GOOD: No <svg> wrapper, has clickable background -->
   <rect class="hi-entity-bg" x="0" y="0" width="64" height="64" fill="none"/>
   <circle cx="32" cy="32" r="20" fill="currentColor"/>
   
   <!-- BAD: Has <svg> wrapper -->
   <svg viewBox="0 0 64 64">
     <circle cx="32" cy="32" r="20" fill="currentColor"/>
   </svg>
   ```

4. **Check Template Symbol Generation** ([Template Integration](#template-integration))
   ```django
   <!-- Verify symbol is generated in template -->
   <defs>
     {% for entity_type in entity_types_with_icons %}
       <symbol id="icon-{{ entity_type.name.lower }}" viewBox="{{ entity_type.get_viewbox }}">
         {% include entity_type.get_icon_template %}
       </symbol>
     {% endfor %}
   </defs>
   
   <!-- Check in browser dev tools if symbol exists -->
   <!-- Should find: <symbol id="icon-smart_door_lock"> -->
   ```

5. **Test Direct Icon Usage** ([Testing](#testing-visual-configuration))
   ```html
   <!-- Test icon directly in browser console -->
   <script>
   // Check if symbol exists
   const symbol = document.querySelector('#icon-smart_door_lock');
   console.log('Symbol found:', symbol);
   
   // Test manual icon usage
   const testIcon = document.createElementNS('http://www.w3.org/2000/svg', 'use');
   testIcon.setAttribute('href', '#icon-smart_door_lock');
   testIcon.setAttribute('class', 'entity-svg');
   document.querySelector('svg').appendChild(testIcon);
   </script>
   ```

6. **Check ViewBox Issues** ([Custom ViewBox](#register-icon-configuration))
   ```python
   # If icon appears but wrong size, check viewbox
   # Add custom viewbox if needed
   EntityTypeToIconViewbox = {
       EntityType.SMART_DOOR_LOCK: "0 0 80 80",  # If icon designed differently
   }
   ```

**Common Resolutions**:
- File name doesn't match enum (case sensitivity)
- SVG has `<svg>` wrapper (remove it)
- Missing clickable background rectangle
- Not registered in `EntityTypesWithIcons`

---

### Workflow 4: Creating Entity Type Family with Consistent Styling

**Scenario**: Create multiple related security device types (door lock, window sensor, security camera) with consistent visual styling.

**Coordinated Implementation:**

1. **Design Visual Family** ([Visual Asset Guidelines](#visual-asset-guidelines))
   ```css
   /* Define consistent family styling */
   .security-device {
     stroke-width: 2;
     stroke: #333333;
   }
   
   .security-device.state-secure {
     fill: #28a745;  /* Green family */
   }
   
   .security-device.state-alert {
     fill: #dc3545;  /* Red family */  
   }
   
   .security-device.state-warning {
     fill: #ffc107; /* Yellow family */
   }
   ```

2. **Create Icon Family** ([SVG Icon Standards](#visual-asset-guidelines))
   ```xml
   <!-- Common 64x64 viewbox, similar design elements -->
   
   <!-- type.door_lock.svg -->
   <rect class="hi-entity-bg" x="0" y="0" width="64" height="64" fill="none"/>
   <rect x="20" y="15" width="24" height="34" fill="none" stroke="currentColor" stroke-width="2"/>
   <circle cx="32" cy="32" r="4" fill="currentColor"/>
   
   <!-- type.window_sensor.svg -->  
   <rect class="hi-entity-bg" x="0" y="0" width="64" height="64" fill="none"/>
   <rect x="15" y="20" width="34" height="24" fill="none" stroke="currentColor" stroke-width="2"/>
   <rect x="18" y="23" width="28" height="18" fill="currentColor" opacity="0.3"/>
   
   <!-- type.security_camera.svg -->
   <rect class="hi-entity-bg" x="0" y="0" width="64" height="64" fill="none"/>
   <rect x="20" y="25" width="24" height="16" rx="4" fill="currentColor"/>
   <circle cx="44" cy="33" r="8" fill="none" stroke="currentColor" stroke-width="2"/>
   ```

3. **Register All Types** ([Batch Registration](#register-icon-configuration))
   ```python
   # Add all security devices to icons
   EntityTypesWithIcons = {
       # ... existing types
       EntityType.DOOR_LOCK,
       EntityType.WINDOW_SENSOR,
       EntityType.SECURITY_CAMERA,
       # ... other types
   }
   ```

4. **Apply Family CSS Classes** ([CSS Class Application](../entity-status-display.md#css-class-mapping))
   ```python
   # In status calculation logic
   def get_security_device_classes(entity):
       base_classes = ['security-device']
       
       if entity.entity_type in [EntityType.DOOR_LOCK, EntityType.WINDOW_SENSOR]:
           state = entity.get_current_state('security_state')
           if state and state.value == 'secure':
               base_classes.append('state-secure')
           elif state and state.value == 'breached':
               base_classes.append('state-alert')
           else:
               base_classes.append('state-warning')
       
       return base_classes
   ```

5. **Test Family Consistency** ([Visual Testing](#testing-visual-configuration))
   ```python
   # Create test entities for all family members
   security_devices = [
       ('Front Door Lock', EntityType.DOOR_LOCK),
       ('Living Room Window', EntityType.WINDOW_SENSOR), 
       ('Driveway Camera', EntityType.SECURITY_CAMERA),
   ]
   
   for name, entity_type in security_devices:
       test_entity = Entity.objects.create(
           name=name,
           entity_type=entity_type,
           location=test_location
       )
       # Test all status states for visual consistency
   ```

**Expected Result**: All security devices have cohesive visual design with consistent status colors and styling patterns.

## Common Patterns Library

### Standard Entity Icon Templates

#### Basic Icon SVG Structure
```xml
<!-- Standard template for entity type icons -->
<!-- File: hi/apps/entity/templates/entity/svg/type.{TYPE_NAME}.svg -->
<rect class="hi-entity-bg" x="0" y="0" width="64" height="64" fill="none"/>
<!-- Entity-specific icon content here -->
<circle cx="32" cy="32" r="20" fill="currentColor"/>
<!-- Optional status indicator -->
<circle cx="50" cy="14" r="6" fill="currentColor" opacity="0.8"/>
```

#### Icon Family Consistency Pattern
```xml
<!-- Motion sensor icon -->
<rect class="hi-entity-bg" x="0" y="0" width="64" height="64" fill="none"/>
<circle cx="32" cy="32" r="18" fill="currentColor"/>
<path d="M20,32 L32,20 L44,32 L32,44 Z" fill="white" opacity="0.8"/>

<!-- Door sensor icon -->
<rect class="hi-entity-bg" x="0" y="0" width="64" height="64" fill="none"/>
<rect x="22" y="16" width="20" height="32" fill="none" stroke="currentColor" stroke-width="2"/>
<circle cx="36" cy="32" r="3" fill="currentColor"/>

<!-- Window sensor icon -->
<rect class="hi-entity-bg" x="0" y="0" width="64" height="64" fill="none"/>
<rect x="16" y="22" width="32" height="20" fill="none" stroke="currentColor" stroke-width="2"/>
<rect x="19" y="25" width="26" height="14" fill="currentColor" opacity="0.3"/>
```

#### Status-Aware Icon Variants
```xml
<!-- Base thermostat icon -->
<rect class="hi-entity-bg" x="0" y="0" width="64" height="64" fill="none"/>
<circle cx="32" cy="32" r="20" fill="none" stroke="currentColor" stroke-width="3"/>
<circle cx="32" cy="32" r="12" fill="currentColor"/>
<!-- Temperature display area -->
<text x="32" y="36" text-anchor="middle" fill="white" font-size="8">72°</text>

<!-- Heating indicator (conditional element) -->
<g class="heating-indicator">
  <path d="M32,15 L35,20 L29,20 Z" fill="#ff4444"/>
</g>

<!-- Cooling indicator (conditional element) -->
<g class="cooling-indicator">
  <path d="M32,49 L35,44 L29,44 Z" fill="#4444ff"/>
</g>
```

### Standard Entity Configuration Patterns

#### Icon Registration Pattern
```python
# Standard pattern for registering icon entity types
# In hi.hi_styles.EntityStyle

EntityTypesWithIcons = {
    # Security devices family
    EntityType.MOTION_SENSOR,
    EntityType.DOOR_SENSOR,
    EntityType.WINDOW_SENSOR,
    EntityType.SECURITY_CAMERA,
    
    # Climate control family
    EntityType.TEMPERATURE_SENSOR,
    EntityType.THERMOSTAT,
    EntityType.HUMIDITY_SENSOR,
    
    # Lighting family
    EntityType.LIGHT_SWITCH,
    EntityType.DIMMER_SWITCH,
    EntityType.SMART_BULB,
    
    # Add new entity types here following family grouping
}

# Custom viewboxes for non-standard icons
EntityTypeToIconViewbox = {
    EntityType.WIDE_SENSOR: "0 0 100 50",      # Wide rectangular sensor
    EntityType.TALL_SENSOR: "0 0 40 80",       # Tall vertical sensor
    EntityType.DETAILED_CAMERA: "0 0 80 60",   # More detailed camera icon
}
```

#### Path Registration Pattern
```python
# Standard pattern for registering path entity types
# In hi.hi_styles.EntityStyle

# Closed paths (filled areas)
EntityTypeClosedPaths = {
    # Room and zone types
    EntityType.ROOM,
    EntityType.ZONE,
    EntityType.COVERAGE_AREA,
    
    # Detection/sensor coverage areas
    EntityType.MOTION_DETECTION_ZONE,
    EntityType.SECURITY_PERIMETER,
    
    # Add new area-based entity types here
}

# Open paths (lines and curves)
EntityTypeOpenPaths = {
    # Boundary and connection types
    EntityType.BOUNDARY_LINE,
    EntityType.CORRIDOR,
    EntityType.FENCE_LINE,
    
    # Connection paths
    EntityType.CABLE_RUN,
    EntityType.PIPE_LINE,
    
    # Add new line-based entity types here
}
```

#### Visual Style Mapping Pattern
```python
# Standard pattern for mapping entity types to visual styles
# In hi.hi_styles.EntityStyle

PathEntityTypeToSvgStatusStyle = {
    # Security areas
    EntityType.SECURITY_PERIMETER: SecurityPerimeterStyle,
    EntityType.MOTION_DETECTION_ZONE: MotionZoneStyle,
    
    # Climate zones
    EntityType.HVAC_ZONE: HvacZoneStyle,
    EntityType.TEMPERATURE_ZONE: TemperatureZoneStyle,
    
    # Room types
    EntityType.ROOM: RoomStyle,
    EntityType.BATHROOM: BathroomStyle,
    EntityType.BEDROOM: BedroomStyle,
}

# Standard size overrides
EntityTypePathInitialRadius = {
    EntityType.SMALL_SENSOR_COVERAGE: 15.0,
    EntityType.ROOM: 30.0,
    EntityType.LARGE_DETECTION_ZONE: 50.0,
}
```

### Standard Visual Style Classes

#### Basic SVG Status Style Template
```python
# Standard template for SVG status style classes
class StandardSvgStatusStyle:
    """Base template for entity visual styling"""
    
    # Default styling (idle/unknown state)
    default_fill = "#E0E0E0"
    default_stroke = "#808080"
    default_stroke_width = "2"
    default_opacity = "0.6"
    
    # Active state styling
    active_fill = "#DC3545"
    active_stroke = "#B02A37"
    active_stroke_width = "3"
    active_opacity = "0.9"
    
    # Recent activity styling
    recent_fill = "#FD7E14"
    recent_stroke = "#CC6200"
    recent_stroke_width = "2"
    recent_opacity = "0.7"
    
    # Past activity styling
    past_fill = "#FFC107"
    past_stroke = "#CC9A00"
    past_stroke_width = "2"
    past_opacity = "0.5"
    
    # Idle/safe state styling
    idle_fill = "#28A745"
    idle_stroke = "#1E7E34"
    idle_stroke_width = "2"
    idle_opacity = "0.4"

# Security-specific styling
class SecurityDeviceStyle(StandardSvgStatusStyle):
    """Visual styling for security devices"""
    
    # Override for security-specific colors
    active_fill = "#FF0000"     # Bright red for security alerts
    active_opacity = "1.0"      # Full opacity for alerts
    
    idle_fill = "#00AA00"       # Green for secure state
    idle_opacity = "0.6"

# Climate-specific styling  
class ClimateDeviceStyle(StandardSvgStatusStyle):
    """Visual styling for climate control devices"""
    
    # Climate-specific state colors
    heating_fill = "#FF4444"
    heating_stroke = "#CC0000"
    
    cooling_fill = "#4444FF"
    cooling_stroke = "#0000CC"
    
    idle_fill = "#44AA44"       # Green for idle HVAC
```

### Standard Template Integration Patterns

#### Icon Entity Template Pattern
```django
<!-- Standard template for icon-based entities in location views -->
<defs>
  {% for entity_type in entity_types_with_icons %}
    <symbol id="icon-{{ entity_type.name.lower }}" 
            viewBox="{{ entity_type.get_viewbox }}">
      {% include entity_type.get_icon_template %}
    </symbol>
  {% endfor %}
</defs>

<!-- Entity rendering loop -->
{% for entity in positioned_entities %}
  <g class="entity-group" data-entity-id="{{ entity.id }}" 
     data-entity-type="{{ entity.entity_type.name.lower }}">
    <use href="#icon-{{ entity.entity_type.name.lower }}" 
         class="entity-svg {{ entity.get_status_css_classes|join:' ' }}"
         transform="translate({{ entity.position.x }}, {{ entity.position.y }}) 
                    scale({{ entity.position.scale|default:1.0 }}) 
                    rotate({{ entity.position.rotation|default:0 }})"/>
    <!-- Optional entity label -->
    {% if entity.show_label %}
      <text x="{{ entity.position.x }}" 
            y="{{ entity.position.y|add:25 }}" 
            class="entity-label">{{ entity.name }}</text>
    {% endif %}
  </g>
{% endfor %}
```

#### Path Entity Template Pattern
```django
<!-- Standard template for path-based entities -->
{% for entity in path_entities %}
  <g class="entity-group" data-entity-id="{{ entity.id }}" 
     data-entity-type="{{ entity.entity_type.name.lower }}">
    <path class="entity-path {{ entity.get_status_css_classes|join:' ' }}"
          d="{{ entity.path.svg_path }}"
          style="fill: {{ entity.get_status_fill }};
                 stroke: {{ entity.get_status_stroke }};
                 stroke-width: {{ entity.get_status_stroke_width }};
                 opacity: {{ entity.get_status_opacity }}"/>
    <!-- Optional path label at centroid -->
    {% if entity.show_label %}
      <text x="{{ entity.path.centroid_x }}" 
            y="{{ entity.path.centroid_y }}" 
            class="entity-label path-label">{{ entity.name }}</text>
    {% endif %}
  </g>
{% endfor %}
```

#### Entity Collection Template Pattern
```django
<!-- Standard template for entity collections/groups -->
<div class="entity-collection" data-collection-id="{{ collection.id }}">
  <h4 class="collection-title">{{ collection.name }}</h4>
  <div class="entity-grid">
    {% for entity in collection.entities %}
      <div class="entity-card" data-entity-id="{{ entity.id }}">
        <div class="entity-icon-container">
          {% if entity.has_position %}
            <svg viewBox="0 0 64 64" class="entity-card-icon">
              <use href="#icon-{{ entity.entity_type.name.lower }}" 
                   class="entity-svg {{ entity.get_status_css_classes|join:' ' }}"/>
            </svg>
          {% else %}
            <div class="entity-placeholder {{ entity.get_status_css_classes|join:' ' }}">
              {{ entity.entity_type.display_name|first }}
            </div>
          {% endif %}
        </div>
        <div class="entity-info">
          <span class="entity-name">{{ entity.name }}</span>
          <span class="entity-status">{{ entity.get_display_state }}</span>
        </div>
      </div>
    {% endfor %}
  </div>
</div>
```

### Standard Testing Patterns for Visual Configuration

#### Icon Registration Testing Pattern
```python
# Standard test pattern for icon registration
class IconRegistrationTestCase(TestCase):
    def test_entity_type_icon_registration(self):
        """Test that entity type is properly registered for icon display"""
        entity_type = EntityType.MOTION_SENSOR
        
        # Verify type is in icon registry
        self.assertIn(entity_type, EntityStyle.EntityTypesWithIcons)
        
        # Verify icon template file exists
        icon_template_path = entity_type.get_icon_template_path()
        self.assertTrue(os.path.exists(icon_template_path))
        
        # Verify viewbox is defined
        viewbox = entity_type.get_viewbox()
        self.assertIsNotNone(viewbox)
        self.assertRegex(viewbox, r'\d+ \d+ \d+ \d+')  # "x y width height" format
    
    def test_icon_svg_content_requirements(self):
        """Test that icon SVG meets requirements"""
        entity_type = EntityType.MOTION_SENSOR
        svg_content = entity_type.get_icon_svg_content()
        
        # Must have clickable background
        self.assertIn('class="hi-entity-bg"', svg_content)
        
        # Should not have wrapping <svg> element
        self.assertNotIn('<svg', svg_content)
        
        # Should use currentColor for primary elements
        self.assertIn('currentColor', svg_content)
```

#### Path Configuration Testing Pattern
```python
# Standard test pattern for path configuration
class PathConfigurationTestCase(TestCase):
    def test_path_entity_type_registration(self):
        """Test that path entity type is properly configured"""
        entity_type = EntityType.ROOM
        
        # Verify type is in appropriate path registry
        is_closed = entity_type in EntityStyle.EntityTypeClosedPaths
        is_open = entity_type in EntityStyle.EntityTypeOpenPaths
        self.assertTrue(is_closed or is_open, f"{entity_type} not in any path registry")
        
        # Verify style is assigned
        self.assertIn(entity_type, EntityStyle.PathEntityTypeToSvgStatusStyle)
        
        # Verify style class exists and has required properties
        style_class = EntityStyle.PathEntityTypeToSvgStatusStyle[entity_type]
        self.assertTrue(hasattr(style_class, 'default_fill'))
        self.assertTrue(hasattr(style_class, 'active_fill'))
        
    def test_path_entity_creation_and_display(self):
        """Test creating and displaying path entities"""
        room = Entity.objects.create(
            name='Test Room',
            entity_type=EntityType.ROOM,
            location=self.test_location
        )
        
        # Create path data
        path_data = "M10,10 L50,10 L50,50 L10,50 Z"  # Simple rectangle
        EntityPath.objects.create(
            entity=room,
            svg_path=path_data
        )
        
        # Verify entity can provide display data
        css_classes = room.get_status_css_classes()
        self.assertIsInstance(css_classes, list)
        
        fill_color = room.get_status_fill()
        self.assertIsInstance(fill_color, str)
        self.assertRegex(fill_color, r'^#[0-9A-Fa-f]{6}$')  # Valid hex color
```

#### Visual Style Testing Pattern
```python
# Standard test pattern for visual style classes
class VisualStyleTestCase(TestCase):
    def test_style_class_completeness(self):
        """Test that style class defines all required properties"""
        style_class = SecurityDeviceStyle
        
        required_properties = [
            'default_fill', 'default_stroke', 'default_opacity',
            'active_fill', 'active_stroke', 'active_opacity',
            'idle_fill', 'idle_stroke', 'idle_opacity'
        ]
        
        for prop in required_properties:
            self.assertTrue(hasattr(style_class, prop),
                          f"Style class missing property: {prop}")
    
    def test_color_format_validation(self):
        """Test that style colors are valid hex format"""
        style_class = SecurityDeviceStyle
        
        color_properties = ['default_fill', 'active_fill', 'idle_fill']
        for prop in color_properties:
            color_value = getattr(style_class, prop)
            self.assertRegex(color_value, r'^#[0-9A-Fa-f]{6}$',
                           f"Invalid color format in {prop}: {color_value}")
```

#### JavaScript Testing Pattern for Entity Configuration
```javascript
// Standard pattern for testing entity visual configuration
function testEntityVisualConfiguration() {
    // Test icon symbol generation
    const iconSymbol = document.querySelector('#icon-motion-sensor');
    console.assert(iconSymbol !== null, 'Icon symbol not generated');
    console.assert(iconSymbol.getAttribute('viewBox') === '0 0 64 64', 
                  'Incorrect viewBox');
    
    // Test entity element creation
    const testEntityHtml = `
        <g data-entity-id="test-123" data-entity-type="motion-sensor">
            <use href="#icon-motion-sensor" class="entity-svg state-idle"/>
        </g>
    `;
    document.querySelector('svg').innerHTML += testEntityHtml;
    
    // Test CSS class application
    const entityElement = document.querySelector('[data-entity-id="test-123"] use');
    console.assert(entityElement.classList.contains('entity-svg'), 
                  'Base entity class missing');
    console.assert(entityElement.classList.contains('state-idle'), 
                  'Status class missing');
    
    // Test visual style application
    const computedStyle = window.getComputedStyle(entityElement);
    const fillColor = computedStyle.fill;
    console.assert(fillColor !== '', 'Fill color not applied');
    
    console.log('Entity visual configuration test passed');
}
```

### Standard Maintenance Patterns

#### Icon File Organization Pattern
```
hi/apps/entity/templates/entity/svg/
├── families/
│   ├── security/
│   │   ├── type.motion_sensor.svg
│   │   ├── type.door_sensor.svg
│   │   └── type.security_camera.svg
│   ├── climate/
│   │   ├── type.thermostat.svg
│   │   └── type.temperature_sensor.svg
│   └── lighting/
│       ├── type.light_switch.svg
│       └── type.dimmer_switch.svg
└── deprecated/
    └── old_icon_files_kept_for_reference.svg
```

#### Configuration Review Checklist
```python
# Standard checklist for reviewing entity visual configuration
"""
Entity Visual Configuration Review Checklist:

□ Icon File Requirements:
  - SVG file exists in correct location
  - No <svg> wrapper element
  - Contains hi-entity-bg rectangle for clickability
  - Uses currentColor for status-responsive elements
  - Follows 64x64 viewBox standard (or custom viewBox registered)

□ Registration Requirements:
  - EntityType added to appropriate registry (Icons vs Paths)
  - Style class assigned in PathEntityTypeToSvgStatusStyle (for paths)
  - Custom viewBox registered if needed

□ Style Requirements:
  - Style class defines all required state properties
  - Colors use valid hex format
  - Opacity values are between 0.0 and 1.0
  - Stroke widths are reasonable (1-4 typical)

□ Template Integration:
  - Entity appears in location views
  - Status changes trigger visual updates
  - CSS classes apply correctly
  - Cross-browser compatibility verified

□ Testing Requirements:
  - Unit tests cover registration
  - Visual tests verify appearance
  - Status change tests verify dynamic updates
  - Error cases handled gracefully
"""
```

## Performance Optimization Guide

### Overview

Entity visual configuration can significantly impact rendering performance, especially with many entity types, complex SVG icons, or large-scale deployments. This guide provides optimization strategies for efficient entity visual management.

### SVG Icon Performance Optimization

#### Icon Complexity Management
```xml
<!-- EFFICIENT: Simple geometric shapes -->
<rect class="hi-entity-bg" x="0" y="0" width="64" height="64" fill="none"/>
<circle cx="32" cy="32" r="20" fill="currentColor"/>
<rect x="28" y="28" width="8" height="8" fill="white"/>

<!-- INEFFICIENT: Complex path with many points -->
<rect class="hi-entity-bg" x="0" y="0" width="64" height="64" fill="none"/>
<path d="M32,10 L35,15 L40,15 L37,20 L38,25 L32,23 L26,25 L27,20 L24,15 L29,15 Z" fill="currentColor"/>
<path d="M20,30 Q25,25 30,30 Q35,35 40,30 Q45,25 50,30" fill="none" stroke="currentColor"/>
```

#### SVG Optimization Pipeline
```javascript
// Automated SVG optimization during build
class SvgIconOptimizer {
    constructor(options = {}) {
        this.options = {
            removeUnusedDefs: true,
            simplifyPaths: true,
            mergeShapes: true,
            removeComments: true,
            minifyCoordinates: true,
            ...options
        };
    }
    
    optimizeSvgContent(svgString) {
        let optimized = svgString;
        
        if (this.options.removeComments) {
            optimized = this.removeComments(optimized);
        }
        
        if (this.options.simplifyPaths) {
            optimized = this.simplifyPaths(optimized);
        }
        
        if (this.options.minifyCoordinates) {
            optimized = this.minifyCoordinates(optimized);
        }
        
        return optimized;
    }
    
    removeComments(svg) {
        return svg.replace(/<!--[\s\S]*?-->/g, '');
    }
    
    simplifyPaths(svg) {
        // Convert complex paths to simpler equivalents
        return svg.replace(/(<path[^>]*d=")([^"]+)(")/g, (match, start, pathData, end) => {
            const simplified = this.simplifyPathData(pathData);
            return start + simplified + end;
        });
    }
    
    simplifyPathData(pathData) {
        // Remove unnecessary precision
        return pathData.replace(/(\d+\.\d{3,})/g, (match, num) => {
            return parseFloat(num).toFixed(2);
        });
    }
    
    minifyCoordinates(svg) {
        // Round coordinates to reduce file size
        return svg.replace(/(\d+\.\d{2,})/g, (match, coord) => {
            return Math.round(parseFloat(coord) * 100) / 100;
        });
    }
}
```

#### Icon Caching Strategy
```javascript
// Efficient icon loading and caching
class IconCacheManager {
    constructor() {
        this.iconCache = new Map();
        this.preloadQueue = [];
        this.isPreloading = false;
    }
    
    async preloadIcons(iconTypes) {
        this.preloadQueue.push(...iconTypes);
        
        if (!this.isPreloading) {
            this.processPreloadQueue();
        }
    }
    
    async processPreloadQueue() {
        this.isPreloading = true;
        
        while (this.preloadQueue.length > 0) {
            const iconType = this.preloadQueue.shift();
            
            if (!this.iconCache.has(iconType)) {
                try {
                    const iconContent = await this.loadIconContent(iconType);
                    this.iconCache.set(iconType, iconContent);
                } catch (error) {
                    console.warn(`Failed to preload icon ${iconType}:`, error);
                }
            }
            
            // Yield control to prevent blocking
            await new Promise(resolve => setTimeout(resolve, 0));
        }
        
        this.isPreloading = false;
    }
    
    async loadIconContent(iconType) {
        const iconPath = `/static/entity/svg/type.${iconType.toLowerCase()}.svg`;
        const response = await fetch(iconPath);
        
        if (!response.ok) {
            throw new Error(`Failed to load icon: ${response.status}`);
        }
        
        return await response.text();
    }
    
    getIcon(iconType) {
        return this.iconCache.get(iconType);
    }
    
    // Lazy load icons on demand with memory limits
    async ensureIconLoaded(iconType, priority = 'normal') {
        if (this.iconCache.has(iconType)) {
            return this.iconCache.get(iconType);
        }
        
        // Manage cache size
        if (this.iconCache.size >= 100) {
            this.evictLeastRecentlyUsed();
        }
        
        const iconContent = await this.loadIconContent(iconType);
        this.iconCache.set(iconType, {
            content: iconContent,
            lastUsed: Date.now(),
            priority
        });
        
        return iconContent;
    }
    
    evictLeastRecentlyUsed() {
        let oldestTime = Date.now();
        let oldestKey = null;
        
        for (const [key, value] of this.iconCache) {
            if (value.priority !== 'high' && value.lastUsed < oldestTime) {
                oldestTime = value.lastUsed;
                oldestKey = key;
            }
        }
        
        if (oldestKey) {
            this.iconCache.delete(oldestKey);
        }
    }
}
```

### Registration and Configuration Performance

#### Lazy Registration Pattern
```python
# Optimize entity type registration for large numbers of types
class LazyEntityTypeRegistry:
    """Lazy-load entity type configurations to improve startup performance"""
    
    def __init__(self):
        self._icon_registry = None
        self._path_registry = None
        self._style_registry = None
        self._viewbox_registry = None
    
    @property
    def entity_types_with_icons(self):
        if self._icon_registry is None:
            self._icon_registry = self._build_icon_registry()
        return self._icon_registry
    
    @property
    def entity_type_closed_paths(self):
        if self._path_registry is None:
            self._path_registry = self._build_path_registry()
        return self._path_registry
    
    def _build_icon_registry(self):
        """Build icon registry on first access"""
        icon_types = set()
        
        # Load from configuration files or database
        # This allows for dynamic entity type registration
        icon_config = self.load_icon_configuration()
        
        for entity_type_name in icon_config:
            try:
                entity_type = EntityType[entity_type_name]
                icon_types.add(entity_type)
            except KeyError:
                logger.warning(f"Unknown entity type in icon config: {entity_type_name}")
        
        return icon_types
    
    def load_icon_configuration(self):
        """Load icon configuration from external source"""
        # Can be loaded from JSON, database, or environment
        return getattr(settings, 'ENTITY_ICON_TYPES', DEFAULT_ICON_TYPES)
```

#### Batch Configuration Updates
```python
# Efficient bulk configuration changes
class EntityConfigurationBatcher:
    """Batch entity configuration changes for better performance"""
    
    def __init__(self):
        self.pending_icon_registrations = set()
        self.pending_path_registrations = set()
        self.pending_style_updates = {}
        self.batch_size = 50
    
    def add_icon_registration(self, entity_type):
        self.pending_icon_registrations.add(entity_type)
        
        if len(self.pending_icon_registrations) >= self.batch_size:
            self.flush_icon_registrations()
    
    def add_path_registration(self, entity_type, path_type):
        self.pending_path_registrations.add((entity_type, path_type))
        
        if len(self.pending_path_registrations) >= self.batch_size:
            self.flush_path_registrations()
    
    def flush_icon_registrations(self):
        """Apply all pending icon registrations at once"""
        if not self.pending_icon_registrations:
            return
        
        # Update registry in single operation
        EntityStyle.EntityTypesWithIcons.update(self.pending_icon_registrations)
        
        # Clear template caches that depend on icon registry
        self.clear_related_caches(['entity_icon_symbols', 'location_view_templates'])
        
        self.pending_icon_registrations.clear()
    
    def flush_all(self):
        """Flush all pending configuration changes"""
        self.flush_icon_registrations()
        self.flush_path_registrations()
        self.flush_style_updates()
    
    def clear_related_caches(self, cache_keys):
        """Clear Django template and view caches"""
        from django.core.cache import cache
        for key in cache_keys:
            cache.delete_many(cache.get_many([f"{key}:*"]))
```

### Template Rendering Optimization

#### Template Fragment Caching
```django
<!-- Cache expensive template fragments -->
{% load cache %}

<!-- Cache entity symbol definitions -->
{% cache 3600 entity_symbols entity_types_hash %}
<defs>
  {% for entity_type in entity_types_with_icons %}
    <symbol id="icon-{{ entity_type.name.lower }}" 
            viewBox="{{ entity_type.get_viewbox }}">
      {% include entity_type.get_icon_template %}
    </symbol>
  {% endfor %}
</defs>
{% endcache %}

<!-- Cache per-entity-type rendering -->
{% for entity in positioned_entities %}
  {% cache 300 entity_rendering entity.id entity.last_modified entity_type_version %}
    <g class="entity-group" data-entity-id="{{ entity.id }}">
      <use href="#icon-{{ entity.entity_type.name.lower }}" 
           class="entity-svg {{ entity.get_status_css_classes|join:' ' }}"
           transform="{{ entity.get_transform_string }}"/>
    </g>
  {% endcache %}
{% endfor %}
```

#### Conditional Template Loading
```python
# Load templates conditionally based on entity types present
class OptimizedLocationViewMixin:
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Only load entity types that are actually used in this location
        present_entity_types = self.get_present_entity_types()
        context['entity_types_with_icons'] = [
            et for et in EntityStyle.EntityTypesWithIcons 
            if et in present_entity_types
        ]
        
        # Pre-calculate expensive template data
        context['entity_transforms'] = self.precalculate_transforms()
        context['entity_type_hash'] = self.get_entity_types_cache_key()
        
        return context
    
    def get_present_entity_types(self):
        """Get only entity types that exist in current location"""
        return set(
            Entity.objects
            .filter(location=self.object)
            .values_list('entity_type', flat=True)
            .distinct()
        )
    
    def precalculate_transforms(self):
        """Pre-calculate transform strings to avoid template computation"""
        transforms = {}
        for entity in self.get_positioned_entities():
            transforms[entity.id] = entity.get_transform_string()
        return transforms
```

### CSS Performance for Visual Configuration

#### CSS Custom Properties Optimization
```css
/* Efficient CSS custom property usage */
:root {
  /* Define base colors once */
  --entity-base-active: #dc3545;
  --entity-base-idle: #28a745;
  --entity-base-unknown: #6c757d;
  
  /* Derive variations using calc() */
  --entity-active-light: color-mix(in srgb, var(--entity-base-active) 80%, white);
  --entity-active-dark: color-mix(in srgb, var(--entity-base-active) 80%, black);
}

/* Use efficient selectors for entity styling */
[data-entity-type="motion_sensor"] {
  --entity-color: var(--entity-base-active);
  --entity-stroke: var(--entity-active-dark);
}

[data-entity-type="door_sensor"] {
  --entity-color: var(--entity-base-idle);
  --entity-stroke: var(--entity-active-dark);
}

/* Apply colors using custom properties */
.entity-svg {
  fill: var(--entity-color);
  stroke: var(--entity-stroke);
}
```

#### Critical CSS for Entity Display
```css
/* Critical CSS - load first for entity display */
.entity-svg, .entity-path {
  /* Essential properties only */
  fill: currentColor;
  stroke: currentColor;
  cursor: pointer;
}

.entity-group {
  /* Minimal base styling */
  pointer-events: all;
}

/* Non-critical styling - can be loaded later */
@media (min-width: 768px) {
  .entity-svg:hover {
    filter: brightness(1.1);
    transform: scale(1.05);
    transition: all 0.2s ease;
  }
}
```

### Browser Performance Optimization

#### Feature Detection and Polyfills
```javascript
// Conditional feature loading based on browser capabilities
class BrowserOptimizedEntityRenderer {
    constructor() {
        this.capabilities = this.detectCapabilities();
        this.loadOptimalStrategies();
    }
    
    detectCapabilities() {
        return {
            hasIntersectionObserver: 'IntersectionObserver' in window,
            hasResizeObserver: 'ResizeObserver' in window,
            supportsCustomElements: 'customElements' in window,
            supportsCSSSCustomProperties: CSS.supports('--test', 'test'),
            hasRequestIdleCallback: 'requestIdleCallback' in window,
            memoryInfo: navigator.memory || { usedJSHeapSize: 50 * 1024 * 1024 },
            hardwareConcurrency: navigator.hardwareConcurrency || 4
        };
    }
    
    loadOptimalStrategies() {
        if (this.capabilities.hasIntersectionObserver) {
            this.useIntersectionBasedRendering();
        } else {
            this.useScrollBasedRendering();
        }
        
        if (this.capabilities.hasRequestIdleCallback) {
            this.useIdleTimeProcessing();
        } else {
            this.useTimeSlicedProcessing();
        }
        
        // Adjust strategies based on device memory
        if (this.capabilities.memoryInfo.usedJSHeapSize > 100 * 1024 * 1024) {
            this.enableMemoryConservationMode();
        }
    }
    
    useIntersectionBasedRendering() {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                const entityId = entry.target.getAttribute('data-entity-id');
                if (entry.isIntersecting) {
                    this.enableEntityRendering(entityId);
                } else {
                    this.disableEntityRendering(entityId);
                }
            });
        }, { 
            rootMargin: '50px',
            threshold: 0.1
        });
        
        document.querySelectorAll('[data-entity-id]').forEach(el => {
            observer.observe(el);
        });
    }
    
    useIdleTimeProcessing() {
        const processQueue = (deadline) => {
            while (deadline.timeRemaining() > 0 && this.processingQueue.length > 0) {
                const task = this.processingQueue.shift();
                task();
            }
            
            if (this.processingQueue.length > 0) {
                requestIdleCallback(processQueue);
            }
        };
        
        requestIdleCallback(processQueue);
    }
    
    enableMemoryConservationMode() {
        // Reduce icon cache size
        this.maxIconCacheSize = 25;
        
        // Use simplified rendering for non-critical entities
        this.useSimplifiedRendering = true;
        
        // Disable expensive visual effects
        this.disableVisualEffects = true;
    }
}
```

### Testing Performance Optimizations

#### Performance Testing Framework
```javascript
// Automated performance testing for entity configurations
class EntityPerformanceTester {
    constructor(testConfig = {}) {
        this.config = {
            maxEntityCount: 1000,
            testDuration: 30000, // 30 seconds
            acceptableFrameTime: 16, // 60 FPS
            ...testConfig
        };
        this.results = {};
    }
    
    async runEntityLoadTest(entityCount) {
        console.log(`Starting entity load test with ${entityCount} entities`);
        
        const startTime = performance.now();
        const frameTimes = [];
        
        // Create test entities
        const testEntities = this.createTestEntities(entityCount);
        
        // Measure rendering performance
        const measureFrame = () => {
            const frameStart = performance.now();
            
            // Simulate entity updates
            testEntities.forEach(entity => {
                this.updateEntityVisuals(entity);
            });
            
            const frameEnd = performance.now();
            frameTimes.push(frameEnd - frameStart);
            
            if (frameEnd - startTime < this.config.testDuration) {
                requestAnimationFrame(measureFrame);
            } else {
                this.analyzeResults(frameTimes, entityCount);
            }
        };
        
        requestAnimationFrame(measureFrame);
    }
    
    createTestEntities(count) {
        const entities = [];
        const entityTypes = ['motion_sensor', 'door_sensor', 'temperature_sensor'];
        
        for (let i = 0; i < count; i++) {
            const entityType = entityTypes[i % entityTypes.length];
            const entity = {
                id: `test-entity-${i}`,
                type: entityType,
                x: Math.random() * 1000,
                y: Math.random() * 1000,
                status: Math.random() > 0.5 ? 'active' : 'idle'
            };
            entities.push(entity);
        }
        
        return entities;
    }
    
    updateEntityVisuals(entity) {
        const element = document.querySelector(`[data-entity-id="${entity.id}"]`);
        if (element) {
            element.classList.toggle('state-active', entity.status === 'active');
            element.classList.toggle('state-idle', entity.status === 'idle');
        }
    }
    
    analyzeResults(frameTimes, entityCount) {
        const avgFrameTime = frameTimes.reduce((a, b) => a + b, 0) / frameTimes.length;
        const maxFrameTime = Math.max(...frameTimes);
        const slowFrames = frameTimes.filter(t => t > this.config.acceptableFrameTime).length;
        const slowFramePercentage = (slowFrames / frameTimes.length) * 100;
        
        const result = {
            entityCount,
            averageFrameTime: avgFrameTime.toFixed(2),
            maxFrameTime: maxFrameTime.toFixed(2),
            slowFramePercentage: slowFramePercentage.toFixed(1),
            acceptable: slowFramePercentage < 10 // Less than 10% slow frames
        };
        
        this.results[entityCount] = result;
        console.log('Performance test results:', result);
        
        return result;
    }
    
    async runComprehensiveTest() {
        const testSizes = [50, 100, 250, 500, 750, 1000];
        
        for (const size of testSizes) {
            await this.runEntityLoadTest(size);
            
            // Wait between tests
            await new Promise(resolve => setTimeout(resolve, 2000));
        }
        
        this.generatePerformanceReport();
    }
    
    generatePerformanceReport() {
        console.log('\n=== Entity Performance Report ===');
        Object.values(this.results).forEach(result => {
            const status = result.acceptable ? '✅ PASS' : '❌ FAIL';
            console.log(`${status} ${result.entityCount} entities: ${result.averageFrameTime}ms avg, ${result.slowFramePercentage}% slow frames`);
        });
        
        // Find performance breakpoint
        const breakpoint = this.findPerformanceBreakpoint();
        if (breakpoint) {
            console.log(`\n⚠️  Performance degradation detected at ${breakpoint} entities`);
        }
    }
    
    findPerformanceBreakpoint() {
        const results = Object.values(this.results);
        for (let i = 0; i < results.length - 1; i++) {
            if (results[i].acceptable && !results[i + 1].acceptable) {
                return results[i + 1].entityCount;
            }
        }
        return null;
    }
}
```

### Memory Management for Entity Configurations

#### Resource Cleanup Patterns
```javascript
// Proper cleanup to prevent memory leaks
class EntityConfigurationManager {
    constructor() {
        this.iconElements = new Map();
        this.styleSheets = new Map();
        this.eventListeners = new WeakMap();
        this.cleanupTasks = [];
    }
    
    registerEntity(entityId, entityType) {
        // Create icon elements
        const iconElement = this.createIconElement(entityType);
        this.iconElements.set(entityId, iconElement);
        
        // Add cleanup task
        this.cleanupTasks.push(() => {
            this.iconElements.delete(entityId);
            this.removeEntityEventListeners(entityId);
        });
    }
    
    unregisterEntity(entityId) {
        // Clean up icon element
        const iconElement = this.iconElements.get(entityId);
        if (iconElement && iconElement.parentNode) {
            iconElement.parentNode.removeChild(iconElement);
        }
        
        this.iconElements.delete(entityId);
        this.removeEntityEventListeners(entityId);
    }
    
    cleanup() {
        // Run all cleanup tasks
        this.cleanupTasks.forEach(task => {
            try {
                task();
            } catch (error) {
                console.warn('Cleanup task failed:', error);
            }
        });
        
        this.cleanupTasks = [];
        this.iconElements.clear();
        this.styleSheets.clear();
    }
    
    // Automatic cleanup on page unload
    setupAutoCleanup() {
        window.addEventListener('beforeunload', () => {
            this.cleanup();
        });
        
        // Clean up periodically
        setInterval(() => {
            this.performPeriodicCleanup();
        }, 60000); // Every minute
    }
    
    performPeriodicCleanup() {
        // Remove references to non-existent entities
        const existingEntityIds = new Set();
        document.querySelectorAll('[data-entity-id]').forEach(el => {
            existingEntityIds.add(el.getAttribute('data-entity-id'));
        });
        
        for (const [entityId] of this.iconElements) {
            if (!existingEntityIds.has(entityId)) {
                this.unregisterEntity(entityId);
            }
        }
    }
}
```

## Overview

This document covers the frontend configuration required to set up visual representations for entity types. It includes icon configuration, path styling, viewbox management, and visual asset creation.

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

## Troubleshooting

### Entity Icon Not Displaying

**Symptoms**: Entity shows as placeholder or missing icon
**Diagnostic Steps**:

1. **Check File Path and Naming**
   ```bash
   # Verify file exists with correct name
   ls hi/apps/entity/templates/entity/svg/type.{enum_name}.svg
   
   # Example: for EntityType.MOTION_SENSOR
   ls hi/apps/entity/templates/entity/svg/type.motion_sensor.svg
   ```
   - **Rule**: File name must match enum name in lowercase with underscores

2. **Verify Icon Registration**
   ```python
   # Check in hi.hi_styles.EntityStyle.EntityTypesWithIcons
   EntityTypesWithIcons = {
       EntityType.MOTION_SENSOR,  # Must be present
       # ... your new entity type
   }
   ```

3. **Check SVG File Content**
   ```xml
   <!-- File should NOT have <svg> wrapper -->
   <!-- GOOD -->
   <rect class="hi-entity-bg" x="0" y="0" width="64" height="64" fill="none"/>
   <circle cx="32" cy="32" r="20" fill="currentColor"/>
   
   <!-- BAD -->
   <svg viewBox="0 0 64 64">
     <circle cx="32" cy="32" r="20" fill="currentColor"/>
   </svg>
   ```

**Common Fixes**:
- **Incorrect enum case**: Ensure file name uses lowercase and underscores
- **Missing registration**: Add entity type to `EntityTypesWithIcons` set
- **Invalid SVG**: Remove `<svg>` wrapper, keep only drawing commands
- **Missing clickable background**: Add `hi-entity-bg` rectangle

### Entity Icon Wrong Size or Position

**Symptoms**: Icon appears too large, small, or positioned incorrectly
**Root Causes & Solutions**:

1. **ViewBox Issues**
   ```python
   # Check custom viewbox registration
   EntityTypeToIconViewbox = {
       EntityType.YOUR_TYPE: "0 0 100 50",  # Custom viewbox
   }
   ```
   - **Default**: `0 0 64 64` - if icon designed differently, register custom viewbox

2. **SVG Coordinate Problems**
   ```xml
   <!-- Icons should be designed for 64x64 viewbox -->
   <rect class="hi-entity-bg" x="0" y="0" width="64" height="64" fill="none"/>
   <!-- Center elements around 32,32 -->
   <circle cx="32" cy="32" r="20" fill="currentColor"/>
   ```

3. **Template Transform Issues**
   ```django
   <!-- Check entity positioning in template -->
   <g transform="translate({{ entity.position.x }}, {{ entity.position.y }}) 
                 scale({{ entity.position.scale }}) 
                 rotate({{ entity.position.rotation }})">
     <use href="#icon-{{ entity.entity_type.name.lower }}"/>
   </g>
   ```

### Entity Path Not Rendering

**Symptoms**: Path-based entities don't appear or have no styling
**Diagnostic Approach**:

1. **Verify Path Type Registration**
   ```python
   # Check appropriate path type set
   EntityTypeClosedPaths = {
       EntityType.ROOM,
       EntityType.YOUR_AREA_TYPE,  # For filled areas
   }
   
   EntityTypeOpenPaths = {
       EntityType.BOUNDARY_LINE,
       EntityType.YOUR_LINE_TYPE,  # For lines/curves
   }
   ```

2. **Check Style Assignment**
   ```python
   # Verify style is assigned
   PathEntityTypeToSvgStatusStyle = {
       EntityType.YOUR_TYPE: YourCustomSvgStatusStyle,
   }
   ```

3. **Validate SVG Path Data**
   ```django
   <!-- Entity must have valid SVG path -->
   <path class="entity-path" 
         d="{{ entity.path.svg_path }}"  <!-- Must be valid SVG path data -->
         style="{{ entity.get_path_styling }}"/>
   ```

**Solutions**:
- **Missing path registration**: Add to correct path type set (closed vs open)
- **No style defined**: Create and assign `SvgStatusStyle` class
- **Invalid path data**: Ensure `entity.path.svg_path` contains valid SVG path commands

### Entity Colors/Styling Not Applied

**Symptoms**: Entity shows default colors, status changes don't affect appearance
**Troubleshooting Steps**:

1. **Check Style Class Definition**
   ```python
   class YourCustomSvgStatusStyle:
       # Must define all required properties
       default_fill = "#E0E0E0"
       default_stroke = "#808080"
       
       active_fill = "#FF4444"
       active_stroke = "#CC0000"
       
       # ... other states
   ```

2. **Verify CSS Class Application**
   ```html
   <!-- Entity element should have status classes -->
   <path class="entity-path state-active" .../>
   
   <!-- CSS rules should exist -->
   .entity-path.state-active {
       fill: #FF4444;
       stroke: #CC0000;
   }
   ```

3. **Test Status Changes**
   ```javascript
   // Manually test CSS class changes
   const element = document.querySelector('[data-entity-id="123"]');
   element.classList.add('state-active');
   // Should see visual change
   ```

### Template Integration Problems

**Symptoms**: New entity types don't appear in location views
**Checklist**:

1. **Entity Creation**
   ```python
   # Entity must be properly created with type
   entity = Entity.objects.create(
       name="Test Entity",
       entity_type=EntityType.YOUR_NEW_TYPE,
       location=location
   )
   ```

2. **Template Symbol Definitions**
   ```django
   <!-- Icons must be defined in template -->
   <defs>
     {% for entity_type in entity_types_with_icons %}
       <symbol id="icon-{{ entity_type.name.lower }}" 
               viewBox="{{ entity_type.get_viewbox }}">
         {% include entity_type.get_icon_template %}
       </symbol>
     {% endfor %}
   </defs>
   ```

3. **Entity Rendering Logic**
   ```django
   {% for entity in entities %}
     {% if entity.has_position %}
       <!-- Icon entity rendering -->
     {% elif entity.has_path %}
       <!-- Path entity rendering -->
     {% endif %}
   {% endfor %}
   ```

### Performance and Visual Quality Issues

**Symptoms**: Icons appear pixelated, slow rendering, or memory issues
**Optimizations**:

1. **SVG Optimization**
   ```xml
   <!-- Use simple shapes, avoid complex paths -->
   <!-- GOOD - simple circle -->
   <circle cx="32" cy="32" r="20"/>
   
   <!-- AVOID - complex path when simple shape works -->
   <path d="M12,32 A20,20 0 1,1 52,32 A20,20 0 1,1 12,32"/>
   ```

2. **Reduce Icon Complexity**
   ```xml
   <!-- Limit number of elements per icon -->
   <!-- Combine shapes where possible -->
   <!-- Use fill over stroke for better performance -->
   ```

3. **Browser Rendering Optimization**
   ```css
   /* Force hardware acceleration for smooth animations */
   .entity-svg {
     transform: translateZ(0);
     will-change: transform;
   }
   ```

### Browser Compatibility Issues

**Symptoms**: Icons work in some browsers but not others
**Common Problems & Solutions**:

1. **SVG Symbol Support (IE)**
   ```html
   <!-- Use polyfill for older browsers -->
   <script src="svg4everybody.js"></script>
   <script>svg4everybody();</script>
   ```

2. **CSS Custom Properties (IE/Edge)**
   ```css
   /* Provide fallbacks */
   .entity-path {
     fill: #E0E0E0; /* fallback */
     fill: var(--entity-default-fill, #E0E0E0);
   }
   ```

3. **ViewBox Issues (Safari)**
   ```xml
   <!-- Always specify explicit dimensions -->
   <symbol id="icon-sensor" viewBox="0 0 64 64" width="64" height="64">
   ```

## Related Documentation
- Entity domain patterns: [Entity Patterns](../domain/entity-patterns.md)
- Status display implementation: [Entity Status Display](entity-status-display.md)
- Style guidelines: [Style Guidelines](style-guidelines.md)
- Icon system: [Icon System](icon-system.md)
- Frontend guidelines: [Frontend Guidelines](frontend-guidelines.md)