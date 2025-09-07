# Domain Guidelines

## Entity-Centric Design Philosophy

The system models all controllable/observable items as entities with states. This provides a unified approach to managing diverse physical and logical objects.

## Core Domain Models

### Entity Hierarchy
- **Entity**: Central model for all objects (devices, features, software)
- **EntityState**: Hidden state variables that are sensed/controlled
- **EntityType**: Categorization and behavior definition
- **EntityPosition/EntityPath**: Spatial representation in locations

### Location Modeling
- **Location**: Physical spaces with SVG-based floor plans
- **LocationView**: Configurable views of locations with bounds and rotation
- **LocationItem**: Abstract interface for positionable items

### Sensor/Controller Pattern
- **Sensor**: Observation of entity state variables
- **Controller**: Actions to affect entity state variables
- **SensorResponse**: Historical sensor readings

## Business Logic Patterns

### Status Display System

All entity state variables are indirectly observed through sensors, and all sensor values come from integrations. Integrations normalize sensor values and encapsulate them in SensorResponse instances. The SensorResponseManager receives these responses and provides latest status values and histories to views, also detecting changes and feeding them into the alerting subsystem.

### Status Display Logic

Entity status display is driven by business logic that determines how sensor readings translate into visual states. The `StatusDisplayManager` coordinates this process by calculating appropriate display states based on current and historical sensor data.

```python
class StatusDisplayManager(Singleton):
    def get_status_display_data(self, entity):
        """Compute display state data for entity"""
        current_state = entity.get_current_state()
        return StatusDisplayData(
            status_level=self.calculate_status_level(current_state),
            priority_state=self.resolve_priority_state(entity),
            decaying_status=self.calculate_decaying_status(entity, timezone.now())
        )
```

The visual implementation of this status data (CSS classes, colors, SVG styling) is handled by the frontend system. See [Entity Status Display](../frontend/entity-status-display.md) for visual implementation details.

### Value Decaying Logic

For some entity state types and sensors, we display not only current sensor values but also visually represent recent past values. For example, when motion is detected in an area, we highlight that, but after motion ends, we visually show it was "active" in the recent past (Active red → Recent orange → Past yellow → Idle green).

#### Implementation Approach

The decaying logic creates synthetic visual states ("recent" and "past") that are not actual EntityState values, but are derived from history and timing of sensor readings. The system examines both current and previous sensor values with timestamps to determine appropriate visual representation.

**Key Concept**: The system uses configurable time thresholds to transition between visual states. An entity that was recently active but is now idle will show as "recent" (orange) for a period, then transition to "past" (yellow), and finally to "idle" (green).

**Supported State Types**: Currently implemented for movement sensors, presence sensors, and open/close sensors - entity types where showing recent activity history provides valuable context.

**Color Progression**: Typical color flow is: Active (red) → Recent (orange) → Past (yellow) → Idle (green/gray). This creates an intuitive visual "cooling off" effect.

**Architecture**: The logic is centralized in the status display system (`StatusDisplayData` and `StatusDisplayManager` classes) and integrates with the existing client-server polling mechanism for real-time updates.

```python
class EntityStatusCalculator:
    def calculate_decaying_status(self, entity, current_time):
        """Calculate status with time-based decay"""
        latest_activity = entity.get_latest_activity()
        if not latest_activity:
            return EntityStatus.IDLE
            
        time_since = current_time - latest_activity.timestamp
        
        if time_since < timedelta(minutes=5):
            return EntityStatus.ACTIVE
        elif time_since < timedelta(minutes=30): 
            return EntityStatus.RECENT
        elif time_since < timedelta(hours=2):
            return EntityStatus.PAST
        else:
            return EntityStatus.IDLE
```

### Multiple Sensors Priority

The visual representation is always for an Entity, but an entity can have multiple states and multiple sensors. Trying to support visual distinctions across the cross-product of values for multiple sensors would be too complicated. Thus, the design decision is that at most one entity state will determine the visual view of the SVG.

We define a default priority of entity states and use the highest priority state. However, a single static priority order is too limiting for many use cases. We need to support different priorities for different purposes. For example, we may want a climate control view and a security view of a defined area. In the former, we want the temperature sensor value to dictate visual display, while in the latter, the motion sensor should impact the area's visual display.

To allow user control over visuals from sensor values, each LocationView instance can have its `location_view_type` set to one of the enum values which determines which EntityStateType value takes precedence for status displays. See `hi.apps.location.enums.LocationViewType`.

```python
class EntityStatePriorityResolver:
    def resolve_display_state(self, entity, location_view_type):
        """Resolve which state takes precedence for display"""
        state_priorities = self.get_priorities_for_view_type(location_view_type)
        
        active_states = entity.get_active_states()
        highest_priority_state = max(
            active_states,
            key=lambda state: state_priorities.get(state.entity_state_type, 0)
        )
        
        return highest_priority_state
```


## Event-Driven Architecture

### Event System
- **EventDefinition**: Multi-clause triggers with time windows
- **EventClause**: Individual conditions for triggering
- **EventAction**: Automated responses to events

### Alert System
- **Alert**: System-wide notifications and alarms
- **AlertManager**: Singleton queue-based processing
- **AlarmLevel**: Priority classification for alerts

### Weather Integration

The weather system follows a pluggable business design to support multiple data sources and provide unified weather information throughout the system.

#### Business Logic Principles

- **Multi-Source Strategy**: System does not depend on any single weather data source
- **Data Merging**: Combines data from multiple sources using priority-based resolution
- **Source Attribution**: Every data point is associated with its source and fetch time
- **Priority Resolution**: Higher priority sources provide primary data; lower priority sources fill gaps or replace stale data

#### Core Components

- **WeatherManager**: Singleton manager coordinating weather data from multiple sources
- **WeatherData**: Unified weather information model used throughout the system
- **WeatherAlert**: Integration with the alert system for weather-based notifications

#### Weather Alert Integration

Weather alerts from external sources integrate with the system alert architecture by converting external weather alerts to system Alarms based on:

- **Alert Type Filtering**: Determines which external weather alerts should create system alarms
- **Severity Mapping**: Maps external weather alert severity levels to system `AlarmLevel` values
- **Lifetime Management**: Weather alerts have different duration characteristics than sensor-based events  
- **Security Level Application**: Weather alarms typically apply to all security levels (unlike sensor-based alarms)

For technical implementation details of weather data sources and API integration, see [Weather Integration](../integrations/weather-integration.md).

## Complex Calculations

### Geometric Calculations

Location-based geometric operations for spatial relationships and positioning:

```python
class LocationGeometry:
    def calculate_bounds_with_rotation(self, bounds, rotation_degrees):
        """Calculate bounding box accounting for rotation"""
        rotation_radians = math.radians(rotation_degrees)
        cos_r, sin_r = math.cos(rotation_radians), math.sin(rotation_radians)
        
        # Transform all corners and find bounding box
        corners = self.get_bounds_corners(bounds)
        transformed_corners = [
            self.rotate_point(corner, cos_r, sin_r) 
            for corner in corners
        ]
        
        return self.calculate_bounding_box(transformed_corners)
    
    def calculate_spatial_relationships(self, entity_positions):
        """Determine spatial relationships between entities"""
        relationships = []
        for i, pos1 in enumerate(entity_positions):
            for j, pos2 in enumerate(entity_positions[i+1:], i+1):
                distance = self.calculate_distance(pos1, pos2)
                if distance < self.proximity_threshold:
                    relationships.append(SpatialRelationship(
                        entities=(pos1.entity, pos2.entity),
                        relationship_type=RelationshipType.ADJACENT,
                        distance=distance
                    ))
        return relationships
```

For frontend-specific coordinate transformations, SVG viewbox operations, and screen positioning, see [SVG Coordinate Operations](../frontend/svg-coordinate-operations.md).

### Collection Management

```python
class Collection(models.Model):
    """Logical grouping of entities"""
    name = models.CharField(max_length=100)
    entities = models.ManyToManyField(Entity, related_name='collections')
    
    def get_aggregate_status(self):
        """Calculate collection status from member entities"""
        entity_statuses = [
            entity.get_current_status() 
            for entity in self.entities.all()
        ]
        
        if any(status.is_critical() for status in entity_statuses):
            return CollectionStatus.CRITICAL
        elif any(status.is_active() for status in entity_statuses):
            return CollectionStatus.ACTIVE
        else:
            return CollectionStatus.IDLE
```

## File and Resource Management

### Entity Images and Assets

```python
class EntityAsset(models.Model):
    entity = models.ForeignKey(Entity, on_delete=models.CASCADE)
    asset_type = models.CharField(max_length=50)
    file_path = models.FileField(upload_to='entity_assets/')
    
    def delete(self, *args, **kwargs):
        """Clean up files on deletion"""
        if self.file_path and os.path.isfile(self.file_path.path):
            os.remove(self.file_path.path)
        super().delete(*args, **kwargs)
    
    def generate_unique_filename(self):
        """Generate collision-resistant filenames"""
        ext = self.file_path.name.split('.')[-1]
        return f"{uuid.uuid4()}.{ext}"
```

## Enum Business Rules

### Security State Logic

```python
class SecurityState(Enum):
    ARMED = ("armed", True, True, "#dc3545")
    DISARMED = ("disarmed", True, False, "#28a745")  
    TRIGGERED = ("triggered", False, True, "#dc3545")
    MAINTENANCE = ("maintenance", False, False, "#ffc107")
    
    def __init__(self, name, auto_change_allowed, sends_notification, color):
        self.value = name
        self.auto_change_allowed = auto_change_allowed
        self.sends_notification = sends_notification
        self.color = color
    
    @classmethod
    def from_name_safe(cls, name, default=None):
        """Safe enum lookup with business logic"""
        for state in cls:
            if state.value == name:
                return state
        
        # Business rule: invalid states default to maintenance
        return default or cls.MAINTENANCE
    
    def can_transition_to(self, target_state):
        """Business rules for state transitions"""
        if self == self.TRIGGERED and target_state != self.DISARMED:
            return False  # Must disarm from triggered state
        
        if self == self.MAINTENANCE and not target_state.auto_change_allowed:
            return False  # Can't auto-change from maintenance
            
        return True
```

## Entity Delegation Pattern

```python
class EntityStateDelegation(models.Model):
    """Delegate entity state reflects principal entity state"""
    delegate_entity = models.ForeignKey(
        Entity, 
        on_delete=models.CASCADE,
        related_name='delegated_from'
    )
    principal_entity = models.ForeignKey(
        Entity,
        on_delete=models.CASCADE, 
        related_name='delegated_to'
    )
    entity_state_type = models.ForeignKey(EntityStateType, on_delete=models.CASCADE)
    
    class Meta:
        unique_together = ['delegate_entity', 'entity_state_type']
    
    def sync_state(self):
        """Synchronize delegate state with principal"""
        principal_state = self.principal_entity.get_state(self.entity_state_type)
        delegate_state, created = EntityState.objects.get_or_create(
            entity=self.delegate_entity,
            entity_state_type=self.entity_state_type,
            defaults={'current_value': principal_state.current_value}
        )
        
        if not created and delegate_state.current_value != principal_state.current_value:
            delegate_state.current_value = principal_state.current_value
            delegate_state.save()
```

## Related Documentation
- Entity patterns: [Entity Patterns](entity-patterns.md)
- Event and alert systems: [Event Alert Systems](event-alert-systems.md)
- Business logic: [Business Logic](business-logic.md)
- Data model concepts: [Data Model](../shared/data-model.md)